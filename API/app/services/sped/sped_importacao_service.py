from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

import psycopg

from app.domain.sped.reader import resumir_registros_sped_bytes
from app.services.sped.postgres_config import carregar_config_postgres_sped

@dataclass
class SpedImportacaoResultado:
  arquivo: str
  cnpj_emitente: str | None
  status: str
  mensagem: str

class SpedImportacaoService:
  def __init__(self):
    self.config = carregar_config_postgres_sped()

  def importar_arquivos(
    self,
    arquivos: Iterable[tuple[str, bytes]],
    cnpj_empresa_origem: str,
  ) -> list[SpedImportacaoResultado]:
    resultados: list[SpedImportacaoResultado] = []
    cnpj_normalizado = self._normalizar_cnpj(cnpj_empresa_origem)

    if not cnpj_normalizado:
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
        hash_arquivo = sha256(conteudo).hexdigest()

        with conn.cursor() as cur:
          cur.execute(
            """
            SELECT id
            FROM sped_importados
            WHERE cnpj_emitente = %s
              AND hash_arquivo = %s
            LIMIT 1
            """,
            (cnpj_normalizado, hash_arquivo),
          )
          existente = cur.fetchone()

          if existente:
            resultados.append(
              SpedImportacaoResultado(
                arquivo=nome_arquivo,
                cnpj_emitente=cnpj_normalizado,
                status="duplicado",
                mensagem="Esse arquivo SPED já foi importado para este CNPJ.",
              )
            )
            continue

          cur.execute(
            """
            INSERT INTO sped_importados (
              cnpj_emitente,
              nome_arquivo,
              hash_arquivo,
              tamanho_bytes,
              conteudo_txt
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (cnpj_normalizado, nome_arquivo, hash_arquivo, len(conteudo), conteudo),
          )

        resultados.append(
          SpedImportacaoResultado(
            arquivo=nome_arquivo,
            cnpj_emitente=cnpj_normalizado,
            status="importado",
            mensagem="Arquivo SPED importado com sucesso.",
          )
        )

      conn.commit()

    return resultados

  def contar_pendentes(self, cnpj_emitente: str) -> int:
    cnpj_normalizado = self._normalizar_cnpj(cnpj_emitente)
    if not cnpj_normalizado:
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
          FROM sped_importados
          WHERE cnpj_emitente = %s
            AND processado_em IS NULL
          """,
          (cnpj_normalizado,),
        )
        row = cur.fetchone()

    return int(row[0] or 0) if row else 0

  def processar_importados(self, cnpj_emitente: str) -> tuple[Counter, int, list[int]]:
    cnpj_normalizado = self._normalizar_cnpj(cnpj_emitente)
    if not cnpj_normalizado:
      raise ValueError("CNPJ emitente inválido.")

    contador_registros: Counter = Counter()
    total_linhas = 0
    ids_processados: list[int] = []

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
          SELECT id, conteudo_txt
          FROM sped_importados
          WHERE cnpj_emitente = %s
            AND processado_em IS NULL
          ORDER BY id ASC
          """,
          (cnpj_normalizado,),
        )
        rows = cur.fetchall()

      for row in rows:
        sped_id = int(row[0])
        conteudo = bytes(row[1]) if row[1] else b""
        registros, linhas = resumir_registros_sped_bytes(conteudo)
        contador_registros.update(registros)
        total_linhas += linhas
        ids_processados.append(sped_id)

    return contador_registros, total_linhas, ids_processados

  def marcar_como_processados(self, ids_sped: list[int]) -> None:
    if not ids_sped:
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
          UPDATE sped_importados
          SET processado_em = NOW()
          WHERE id = ANY(%s)
          """,
          (ids_sped,),
        )
      conn.commit()

  def _garantir_tabela(self, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
      cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sped_importados (
          id BIGSERIAL PRIMARY KEY,
          cnpj_emitente VARCHAR(20) NOT NULL,
          nome_arquivo TEXT NOT NULL,
          hash_arquivo VARCHAR(64) NOT NULL,
          tamanho_bytes BIGINT,
          conteudo_txt BYTEA,
          processado_em TIMESTAMPTZ,
          criado_em TIMESTAMPTZ DEFAULT NOW(),
          UNIQUE (cnpj_emitente, hash_arquivo)
        )
        """
      )

      cur.execute("ALTER TABLE sped_importados ADD COLUMN IF NOT EXISTS conteudo_txt BYTEA")
      cur.execute("ALTER TABLE sped_importados ADD COLUMN IF NOT EXISTS processado_em TIMESTAMPTZ")

  def _normalizar_cnpj(self, cnpj: str | None) -> str | None:
    if not cnpj:
      return None

    digits = "".join(ch for ch in cnpj if ch.isdigit())
    if len(digits) == 14:
      return digits

    return None