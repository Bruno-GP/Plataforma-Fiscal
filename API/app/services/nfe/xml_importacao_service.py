from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable
from xml.etree import ElementTree as ET

import psycopg

from app.services.nfe.postres_config import carregar_config_postgres

@dataclass
class XMLImportacaoResultado:
  arquivo: str
  cnpj_emitente: str | None
  status: str
  mensagem: str


class XMLImportacaoService:
  def __init__(self):
    self.config = carregar_config_postgres()

  def importar_arquivos(self, arquivos: Iterable[tuple[str, bytes]]) -> list[XMLImportacaoResultado]:
    resultados: list[XMLImportacaoResultado] = []

    with psycopg.connect(
      host=self.config["host"],
      port=self.config["port"],
      dbname=self.config["database"],
      user=self.config["user"],
      password=self.config["password"],
    ) as conn:
      self._garantir_tabela(conn)

      for nome_arquivo, conteudo in arquivos:
        cnpj_emitente = self._extrair_cnpj_emitente(conteudo)
        if not cnpj_emitente:
          resultados.append(
            XMLImportacaoResultado(
              arquivo=nome_arquivo,
              cnpj_emitente=None,
              status="erro",
              mensagem="Não foi possível identificar o CNPJ emitente no XML.",
            )
          )
          continue

        hash_arquivo = sha256(conteudo).hexdigest()

        with conn.cursor() as cur:
          cur.execute(
            """
            SELECT id
            FROM xml_importados
            WHERE cnpj_emitente = %s
              AND hash_arquivo = %s
            LIMIT 1
            """,
            (cnpj_emitente, hash_arquivo),
          )
          existente = cur.fetchone()

          if existente:
            resultados.append(
              XMLImportacaoResultado(
                arquivo=nome_arquivo,
                cnpj_emitente=cnpj_emitente,
                status="duplicado",
                mensagem="Esse XML já foi importado para este CNPJ.",
              )
            )
            continue

          cur.execute(
            """
            INSERT INTO xml_importados (
              cnpj_emitente,
              nome_arquivo,
              hash_arquivo,
              tamanho_bytes,
              conteudo_xml
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (cnpj_emitente, nome_arquivo, hash_arquivo, len(conteudo), conteudo),
          )

          resultados.append(
            XMLImportacaoResultado(
              arquivo=nome_arquivo,
              cnpj_emitente=cnpj_emitente,
              status="importado",
              mensagem="XML importado com sucesso.",
            )
          )

      conn.commit()

    return resultados

  def _garantir_tabela(self, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
      cur.execute(
        """
        CREATE TABLE IF NOT EXISTS xml_importados (
          id BIGSERIAL PRIMARY KEY,
          cnpj_emitente VARCHAR(20) NOT NULL,
          nome_arquivo TEXT NOT NULL,
          hash_arquivo VARCHAR(64) NOT NULL,
          tamanho_bytes BIGINT,
          conteudo_xml BYTEA,
          processado_em TIMESTAMPTZ,
          criado_em TIMESTAMPTZ DEFAULT NOW(),
          UNIQUE (cnpj_emitente, hash_arquivo)
        )
        """
      )
      
      cur.execute("ALTER TABLE xml_importados ADD COLUMN IF NOT EXISTS conteudo_xml BYTEA")
      cur.execute("ALTER TABLE xml_importados ADD COLUMN IF NOT EXISTS processado_em TIMESTAMPTZ")

  def listar_xmls_importados_nao_processados(self, cnpj_emitente: str) -> list[tuple[int, str, bytes]]:
    with psycopg.connect(
      host=self.config["host"],
      port=self.config["port"],
      dbname=self.config["database"],
      user=self.config["user"],
      password=self.config["password"],
    ) as conn:
      self._garantir_tabela(conn)

      with conn.cursor() as cur:
        cur.execute(
          """
          SELECT id, nome_arquivo, conteudo_xml
          FROM xml_importados
          WHERE cnpj_emitente = %s
            AND processado_em IS NULL
          ORDER BY id ASC
          """,
          (cnpj_emitente,),
        )
        rows = cur.fetchall()

      return [(row[0], row[1], bytes(row[2]) if row[2] else b"") for row in rows]

  def marcar_como_processados(self, ids_xml: list[int]) -> None:
    if not ids_xml:
      return

    with psycopg.connect(
      host=self.config["host"],
      port=self.config["port"],
      dbname=self.config["database"],
      user=self.config["user"],
      password=self.config["password"],
    ) as conn:
      with conn.cursor() as cur:
        cur.execute(
          """
          UPDATE xml_importados
          SET processado_em = NOW()
          WHERE id = ANY(%s)
          """,
          (ids_xml,),
        )
      conn.commit()

  def _extrair_cnpj_emitente(self, conteudo: bytes) -> str | None:
    try:
      root = ET.fromstring(conteudo)
    except ET.ParseError:
      return None

    for element in root.iter():
      if element.tag.endswith("CNPJ") and element.text:
        digits = "".join(ch for ch in element.text if ch.isdigit())
        if len(digits) == 14:
          return digits

    return None