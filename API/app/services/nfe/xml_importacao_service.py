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

  def importar_arquivos(
    self,
    arquivos: Iterable[tuple[str, bytes]],
    cnpj_empresa_origem: str,
  ) -> list[XMLImportacaoResultado]:
    resultados: list[XMLImportacaoResultado] = []
    
    cnpj_empresa_origem_normalizado = self._normalizar_cnpj(cnpj_empresa_origem)

    if not cnpj_empresa_origem_normalizado:
      raise ValueError("CNPJ de origem inválido.")

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
              mensagem="XML não foi processado por não ser compativel",
            )
          )
          continue
        
        if cnpj_emitente != cnpj_empresa_origem_normalizado:
          resultados.append(
            XMLImportacaoResultado(
              arquivo=nome_arquivo,
              cnpj_emitente=cnpj_emitente,
              status="erro",
              mensagem="XML rejeitado: o CNPJ emitente difere do CNPJ da empresa autenticada.",
            )
          )
          continue

        hash_arquivo = sha256(conteudo).hexdigest()

        with conn.cursor() as cur:
          cur.execute(
            """
            SELECT id
            FROM notas_xml_importados
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
            INSERT INTO notas_xml_importados (
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
        CREATE TABLE IF NOT EXISTS notas_xml_importados (
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
      
      cur.execute("ALTER TABLE notas_xml_importados ADD COLUMN IF NOT EXISTS conteudo_xml BYTEA")
      cur.execute("ALTER TABLE notas_xml_importados ADD COLUMN IF NOT EXISTS processado_em TIMESTAMPTZ")

  def listar_xmls_importados_nao_processados(self, cnpj_emitente: str) -> list[tuple[int, str, bytes]]:
    cnpj_emitente_normalizado = self._normalizar_cnpj(cnpj_emitente)
    if not cnpj_emitente_normalizado:
      return []
    
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
          FROM notas_xml_importados
          WHERE cnpj_emitente = %s
            AND processado_em IS NULL
          ORDER BY id ASC
          """,
          (cnpj_emitente_normalizado,),
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
          UPDATE notas_xml_importados
          SET processado_em = NOW()
          WHERE id = ANY(%s)
          """,
          (ids_xml,),
        )
      conn.commit()
      
  def contar_xmls_pendentes(self, cnpj_emitente: str) -> int:
    cnpj_emitente_normalizado = self._normalizar_cnpj(cnpj_emitente)
    if not cnpj_emitente_normalizado:
      return 0
    
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
          SELECT COUNT(*)
          FROM notas_xml_importados
          WHERE cnpj_emitente = %s
            AND processado_em IS NULL
          """,
          (cnpj_emitente_normalizado,),
        )
        row = cur.fetchone()

      return int(row[0] or 0) if row else 0

  def _extrair_cnpj_emitente(self, conteudo: bytes) -> str | None:
    try:
      root = ET.fromstring(conteudo)
    except ET.ParseError:
      return None

    emitente = next(
      (
        element
        for element in root.iter()
        if element.tag.split("}")[-1].lower() == "emit"
      ),
      None,
    )
    if emitente is None:
      return None

    cnpj_emitente = next(
      (
        element
        for element in emitente.iter()
        if element.tag.split("}")[-1].lower() == "cnpj"
      ),
      None,
    )
    if cnpj_emitente is None or not cnpj_emitente.text:
      return None

    return self._normalizar_cnpj(cnpj_emitente.text)

  def _normalizar_cnpj(self, cnpj: str | None) -> str | None:
    if not cnpj:
      return None

    digits = "".join(ch for ch in cnpj if ch.isdigit())
    if len(digits) == 14:
      return digits

    return None