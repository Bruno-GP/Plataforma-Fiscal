from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import psycopg


class IBPTSyncRepository:
  TODAS_UFS = (
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
    "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
    "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
  )

  _required_columns_by_table = {
    "ncm_catalogo": {
      "codigo",
      "descricao",
      "codigo_formatado",
      "vigencia",
      "fonte_arquivo",
      "criado_em",
      "atualizado_em",
    },
    "ncm_tributacao": {
      "id",
      "ncm_codigo",
      "uf",
      "nacional_federal",
      "importados_federal",
      "estadual",
      "municipal",
      "vigencia_inicio",
      "vigencia_fim",
      "versao",
      "fonte",
      "criado_em",
      "atualizado_em",
    },
  }

  @staticmethod
  def _normalizar_ncm(valor: str | None) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())[:8]

  @staticmethod
  def _formatar_ncm(codigo: str) -> str:
    codigo_normalizado = codigo.zfill(8)
    if len(codigo_normalizado) != 8:
      return codigo
    return f"{codigo_normalizado[:4]}.{codigo_normalizado[4:6]}.{codigo_normalizado[6:]}"

  @staticmethod
  def _parse_date(value: str | None) -> date | None:
    if not value:
      return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
      try:
        return datetime.strptime(value, fmt).date()
      except ValueError:
        continue

    return None

  @staticmethod
  def _to_decimal(value: object) -> Decimal:
    if value in (None, ""):
      return Decimal("0.00")
    return Decimal(str(value))

  def validate_ibpt_schema(self, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
      cur.execute(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = ANY(%s)
        """,
        (list(self._required_columns_by_table),),
      )
      existing_columns: dict[str, set[str]] = {
        table_name: set()
        for table_name in self._required_columns_by_table
      }
      for table_name, column_name in cur.fetchall():
        existing_columns[str(table_name)].add(str(column_name))

    missing_parts = []
    for table_name, required_columns in self._required_columns_by_table.items():
      missing_columns = sorted(required_columns - existing_columns[table_name])
      if missing_columns:
        missing_parts.append(f"{table_name}: {', '.join(missing_columns)}")

    if missing_parts:
      raise RuntimeError(
        "Schema IBPT/NCM incompleto. Execute as migrations Alembic. "
        f"Colunas ausentes em public: {'; '.join(missing_parts)}."
      )

  def upsert_catalogo(self, conn: psycopg.Connection, registros: list[dict]) -> int:
    dados: list[dict] = []
    for registro in registros:
      codigo = self._normalizar_ncm(registro.get("codigo"))
      if len(codigo) != 8:
        continue

      dados.append(
        {
          "codigo": codigo,
          "descricao": str(registro.get("descricao") or "").strip(),
          "codigo_formatado": self._formatar_ncm(codigo),
          "vigencia": self._parse_date(registro.get("vigenciainicio")),
          "fonte_arquivo": str(registro.get("fonte") or "IBPT").strip()[:255],
        }
      )

    if not dados:
      return 0

    with conn.cursor() as cur:
      cur.executemany(
        """
        INSERT INTO public.ncm_catalogo (
            codigo,
            descricao,
            codigo_formatado,
            vigencia,
            fonte_arquivo,
            atualizado_em
        )
        VALUES (
            %(codigo)s,
            %(descricao)s,
            %(codigo_formatado)s,
            %(vigencia)s,
            %(fonte_arquivo)s,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (codigo) DO UPDATE
        SET
            descricao = EXCLUDED.descricao,
            codigo_formatado = EXCLUDED.codigo_formatado,
            vigencia = COALESCE(EXCLUDED.vigencia, public.ncm_catalogo.vigencia),
            fonte_arquivo = EXCLUDED.fonte_arquivo,
            atualizado_em = CURRENT_TIMESTAMP
        WHERE
            public.ncm_catalogo.descricao IS DISTINCT FROM EXCLUDED.descricao
            OR public.ncm_catalogo.codigo_formatado IS DISTINCT FROM EXCLUDED.codigo_formatado
            OR public.ncm_catalogo.vigencia IS DISTINCT FROM EXCLUDED.vigencia
            OR public.ncm_catalogo.fonte_arquivo IS DISTINCT FROM EXCLUDED.fonte_arquivo;
        """,
        dados,
      )

    return len(dados)

  def upsert_tributacao(self, conn: psycopg.Connection, registros: list[dict], uf: str) -> int:
    dados: list[dict] = []
    for registro in registros:
      codigo = self._normalizar_ncm(registro.get("codigo"))
      if len(codigo) != 8:
        continue

      dados.append(
        {
          "ncm_codigo": codigo,
          "uf": uf,
          "nacional_federal": self._to_decimal(registro.get("nacionalfederal")),
          "importados_federal": self._to_decimal(registro.get("importadosfederal")),
          "estadual": self._to_decimal(registro.get("estadual")),
          "municipal": self._to_decimal(registro.get("municipal")),
          "vigencia_inicio": self._parse_date(registro.get("vigenciainicio")),
          "vigencia_fim": self._parse_date(registro.get("vigenciafim")),
          "versao": str(registro.get("versao") or "").strip()[:20],
          "fonte": str(registro.get("fonte") or "IBPT").strip()[:100],
        }
      )

    if not dados:
      return 0

    with conn.cursor() as cur:
      cur.executemany(
        """
        INSERT INTO public.ncm_tributacao (
            ncm_codigo,
            uf,
            nacional_federal,
            importados_federal,
            estadual,
            municipal,
            vigencia_inicio,
            vigencia_fim,
            versao,
            fonte,
            atualizado_em
        )
        VALUES (
            %(ncm_codigo)s,
            %(uf)s,
            %(nacional_federal)s,
            %(importados_federal)s,
            %(estadual)s,
            %(municipal)s,
            %(vigencia_inicio)s,
            %(vigencia_fim)s,
            %(versao)s,
            %(fonte)s,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (ncm_codigo, uf) DO UPDATE
        SET
            nacional_federal = EXCLUDED.nacional_federal,
            importados_federal = EXCLUDED.importados_federal,
            estadual = EXCLUDED.estadual,
            municipal = EXCLUDED.municipal,
            vigencia_inicio = EXCLUDED.vigencia_inicio,
            vigencia_fim = EXCLUDED.vigencia_fim,
            versao = EXCLUDED.versao,
            fonte = EXCLUDED.fonte,
            atualizado_em = CURRENT_TIMESTAMP
        WHERE
            public.ncm_tributacao.nacional_federal IS DISTINCT FROM EXCLUDED.nacional_federal
            OR public.ncm_tributacao.importados_federal IS DISTINCT FROM EXCLUDED.importados_federal
            OR public.ncm_tributacao.estadual IS DISTINCT FROM EXCLUDED.estadual
            OR public.ncm_tributacao.municipal IS DISTINCT FROM EXCLUDED.municipal
            OR public.ncm_tributacao.vigencia_inicio IS DISTINCT FROM EXCLUDED.vigencia_inicio
            OR public.ncm_tributacao.vigencia_fim IS DISTINCT FROM EXCLUDED.vigencia_fim
            OR public.ncm_tributacao.versao IS DISTINCT FROM EXCLUDED.versao
            OR public.ncm_tributacao.fonte IS DISTINCT FROM EXCLUDED.fonte;
        """,
        dados,
      )

    return len(dados)

  def obter_tributacao(self, conn: psycopg.Connection, codigo_ncm: str, uf: str) -> dict | None:
    codigo_normalizado = self._normalizar_ncm(codigo_ncm)
    uf_normalizada = str(uf or "").strip().upper()

    if len(codigo_normalizado) != 8:
      raise ValueError("Informe um codigo NCM com 8 digitos.")
    if uf_normalizada not in self.TODAS_UFS:
      raise ValueError("Informe uma UF valida.")

    with conn.cursor() as cur:
      cur.execute(
        """
        SELECT
            t.ncm_codigo,
            c.descricao,
            t.uf,
            t.nacional_federal,
            t.importados_federal,
            t.estadual,
            t.municipal,
            t.vigencia_inicio,
            t.vigencia_fim,
            t.versao,
            t.fonte,
            t.atualizado_em
        FROM public.ncm_tributacao AS t
        LEFT JOIN public.ncm_catalogo AS c
          ON c.codigo = t.ncm_codigo
        WHERE t.ncm_codigo = %s
          AND t.uf = %s
        LIMIT 1;
        """,
        (codigo_normalizado, uf_normalizada),
      )
      row = cur.fetchone()

    if not row:
      return None

    return {
      "ncm_codigo": row[0],
      "descricao": row[1],
      "uf": row[2],
      "nacional_federal": row[3],
      "importados_federal": row[4],
      "estadual": row[5],
      "municipal": row[6],
      "vigencia_inicio": row[7],
      "vigencia_fim": row[8],
      "versao": row[9],
      "fonte": row[10],
      "atualizado_em": row[11],
    }
