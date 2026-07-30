from __future__ import annotations

import logging
from time import perf_counter
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import psycopg


logger = logging.getLogger("repositories.fiscal")


@dataclass(frozen=True)
class FiscalDimensionConfigLike:
  from_clause: str
  company_filter_expr: str
  date_expr: str
  document_id_expr: str
  amount_expr: str
  dimension_code_count_expr: str
  dimension_code_display_expr: str
  dimension_description_expr: str
  category_description_expr: str
  sale_condition_expr: str
  reference_join_clause: str = ""
  category_fallback_description_expr: Optional[str] = None
  unknown_code: str = "0000"
  unknown_description: str = "Codigo sem descricao"


class FiscalRepository:
  def _adicionar_limite(
    self,
    sql: str,
    params: list[object],
    limite: Optional[int],
  ) -> tuple[str, list[object]]:
    if limite is None:
      return sql, params

    return f"{sql}\nLIMIT %s", [*params, limite]

  def _construir_case_categoria_fiscal(self, config: FiscalDimensionConfigLike) -> str:
    texto_base = f"COALESCE({config.category_description_expr}, '')"
    if config.category_fallback_description_expr:
      texto_base = (
        f"COALESCE({config.category_description_expr}, "
        f"{config.category_fallback_description_expr}, '')"
      )

    return f"""
      CASE
        WHEN {config.sale_condition_expr} THEN 'Venda'
        WHEN {texto_base} ILIKE '%%devol%%' THEN 'Devolu\u00e7\u00e3o'
        WHEN {texto_base} ILIKE '%%bonific%%'
          OR {texto_base} ILIKE '%%brinde%%'
          OR {texto_base} ILIKE '%%doa\u00e7%%'
          OR {texto_base} ILIKE '%%doac%%' THEN 'Bonifica\u00e7\u00e3o'
        WHEN {texto_base} ILIKE '%%remessa%%'
          OR {texto_base} ILIKE '%%demonstra%%'
          OR {texto_base} ILIKE '%%conserto%%'
          OR {texto_base} ILIKE '%%comodato%%'
          OR {texto_base} ILIKE '%%industrializa%%' THEN 'Remessa'
        WHEN {texto_base} ILIKE '%%transfer%%' THEN 'Transfer\u00eancia'
        WHEN {texto_base} ILIKE '%%substitui%%'
          OR {texto_base} ILIKE '%%subst. trib%%'
          OR {texto_base} ILIKE '%%st%%' THEN 'Substitui\u00e7\u00e3o Tribut\u00e1ria'
        ELSE 'Outras opera\u00e7\u00f5es'
      END
    """

  def obter_total_impostos_complementares_documentos(
    self,
    conn_params: dict[str, object],
    origem_documento: str,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    tipo_operacao: Optional[str] = None,
    codigos_tributos: Optional[list[str]] = None,
  ) -> Decimal:
    coluna_documento = "nota_id" if origem_documento == "nfe" else "sped_documento_id"
    filtros = [
      f"dt.{coluna_documento} IS NOT NULL",
      "regexp_replace(UPPER(dt.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s",
    ]
    parametros: list[object] = [emitente_cnpj]

    if periodo_ano is not None:
      filtros.append(
        "(dt.periodo_ano = %s OR (dt.periodo_ano IS NULL AND EXTRACT(YEAR FROM dt.data_emissao) = %s))"
      )
      parametros.extend([periodo_ano, periodo_ano])

    if periodo_mes is not None:
      filtros.append(
        "(dt.periodo_mes = %s OR (dt.periodo_mes IS NULL AND EXTRACT(MONTH FROM dt.data_emissao) = %s))"
      )
      parametros.extend([periodo_mes, periodo_mes])

    if tipo_operacao is not None:
      filtros.append("dt.tipo_operacao = %s")
      parametros.append(tipo_operacao)

    join_tributos = ""
    if codigos_tributos:
      join_tributos = "JOIN public.tributos t ON t.id = dt.tributo_id"
      filtros.append("t.codigo = ANY(%s)")
      parametros.append(codigos_tributos)

    try:
      with psycopg.connect(**conn_params) as conn:
        with conn.cursor() as cur:
          inicio = perf_counter()
          cur.execute(
            f"""
            SELECT COALESCE(
              SUM(
                COALESCE(
                  NULLIF(dt.valor_tributo, 0),
                  dt.valor_debito - dt.valor_credito,
                  0
                )
              ),
              0
            ) AS total_impostos
            FROM public.documentos_fiscais_tributos dt
            {join_tributos}
            WHERE {' AND '.join(filtros)}
            """,
            parametros,
          )
          row = cur.fetchone()
          logger.info(
            "SQL total_impostos_complementares_documentos origem=%s linhas=%s tempo=%.3fs parametros=%s",
            origem_documento,
            1 if row else 0,
            perf_counter() - inicio,
            parametros,
          )
    except psycopg.errors.UndefinedTable:
      return Decimal("0.00")

    return row[0] if row else Decimal("0.00")

  def obter_total_tributos_reforma_documentos(
    self,
    conn_params: dict[str, object],
    origem_documento: str,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    tipo_operacao: Optional[str] = None,
  ) -> Decimal:
    return self.obter_total_impostos_complementares_documentos(
      conn_params=conn_params,
      origem_documento=origem_documento,
      emitente_cnpj=emitente_cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      tipo_operacao=tipo_operacao,
      codigos_tributos=["CBS", "IBS", "IBS_UF", "IBS_MUN", "IS"],
    )

  def obter_totais_tributos_documentos_por_periodo(
    self,
    conn_params: dict[str, object],
    origem_documento: str,
    emitente_cnpj: str,
    periodos: list[tuple[int, Optional[int]]],
    tipo_operacao: Optional[str] = None,
  ) -> dict[tuple[int, Optional[int]], dict[str, Decimal]]:
    if not periodos:
      return {}

    coluna_documento = "nota_id" if origem_documento == "nfe" else "sped_documento_id"
    anos = sorted({ano for ano, _mes in periodos})
    filtros = [
      f"dt.{coluna_documento} IS NOT NULL",
      "regexp_replace(UPPER(dt.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s",
      "COALESCE(dt.periodo_ano, EXTRACT(YEAR FROM dt.data_emissao)::int) = ANY(%s)",
    ]
    parametros: list[object] = [emitente_cnpj, anos]

    if tipo_operacao is not None:
      filtros.append("dt.tipo_operacao = %s")
      parametros.append(tipo_operacao)

    totais = {
      periodo: {
        "total_impostos_complementares": Decimal("0.00"),
        "total_tributos_reforma": Decimal("0.00"),
      }
      for periodo in periodos
    }
    periodos_set = set(periodos)
    codigos_tributos_reforma = ["CBS", "IBS", "IBS_UF", "IBS_MUN", "IS"]

    try:
      with psycopg.connect(**conn_params) as conn:
        with conn.cursor() as cur:
          inicio = perf_counter()
          cur.execute(
            f"""
            SELECT
              COALESCE(dt.periodo_ano, EXTRACT(YEAR FROM dt.data_emissao)::int) AS periodo_ano,
              COALESCE(dt.periodo_mes, EXTRACT(MONTH FROM dt.data_emissao)::int) AS periodo_mes,
              COALESCE(
                SUM(
                  COALESCE(
                    NULLIF(dt.valor_tributo, 0),
                    dt.valor_debito - dt.valor_credito,
                    0
                  )
                ),
                0
              ) AS total_impostos_complementares,
              COALESCE(
                SUM(
                  CASE
                    WHEN t.codigo = ANY(%s) THEN COALESCE(
                      NULLIF(dt.valor_tributo, 0),
                      dt.valor_debito - dt.valor_credito,
                      0
                    )
                    ELSE 0
                  END
                ),
                0
              ) AS total_tributos_reforma
            FROM public.documentos_fiscais_tributos dt
            LEFT JOIN public.tributos t ON t.id = dt.tributo_id
            WHERE {' AND '.join(filtros)}
            GROUP BY 1, 2
            """,
            [codigos_tributos_reforma, *parametros],
          )
          rows = cur.fetchall()
          logger.info(
            "SQL totais_tributos_documentos_por_periodo origem=%s linhas=%s tempo=%.3fs parametros=%s",
            origem_documento,
            len(rows),
            perf_counter() - inicio,
            [codigos_tributos_reforma, *parametros],
          )
    except psycopg.errors.UndefinedTable:
      return totais

    for ano, mes, total_impostos, total_reforma in rows:
      if ano is None:
        continue

      chave_mensal = (int(ano), int(mes)) if mes is not None else None
      if chave_mensal in periodos_set:
        totais[chave_mensal]["total_impostos_complementares"] += total_impostos or Decimal("0.00")
        totais[chave_mensal]["total_tributos_reforma"] += total_reforma or Decimal("0.00")

      chave_anual = (int(ano), None)
      if chave_anual in periodos_set:
        totais[chave_anual]["total_impostos_complementares"] += total_impostos or Decimal("0.00")
        totais[chave_anual]["total_tributos_reforma"] += total_reforma or Decimal("0.00")

    return totais

  def analisar_fiscal_por_dimensao(
    self,
    conn_params: dict[str, object],
    config: FiscalDimensionConfigLike,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: Optional[int] = None,
  ) -> dict:
    filtros = [f"{config.company_filter_expr} = %s"]
    parametros: list[object] = [emitente_cnpj]

    if periodo_ano is not None:
      filtros.append(f"EXTRACT(YEAR FROM {config.date_expr}) = %s")
      parametros.append(periodo_ano)

    if periodo_mes is not None:
      filtros.append(f"EXTRACT(MONTH FROM {config.date_expr}) = %s")
      parametros.append(periodo_mes)

    where_clause = " AND ".join(filtros)
    categoria_case = self._construir_case_categoria_fiscal(config)

    with psycopg.connect(**conn_params) as conn:
      with conn.cursor() as cur:
        inicio = perf_counter()
        cur.execute(
          f"""
          SELECT
            COALESCE(SUM({config.amount_expr}), 0) AS total_movimentado,
            COUNT(DISTINCT {config.document_id_expr}) AS quantidade_documentos,
            COUNT(DISTINCT {config.dimension_code_count_expr}) AS quantidade_dimensoes
          FROM {config.from_clause}
          WHERE {where_clause}
          """,
          parametros,
        )
        resumo_row = cur.fetchone()
        logger.info(
          "SQL analise_fiscal_por_dimensao_resumo linhas=%s tempo=%.3fs parametros=%s",
          1 if resumo_row else 0,
          perf_counter() - inicio,
          parametros,
        )
        total_movimentado = resumo_row[0] if resumo_row else Decimal("0.00")
        quantidade_documentos = resumo_row[1] if resumo_row else 0
        quantidade_dimensoes = resumo_row[2] if resumo_row else 0

        inicio = perf_counter()
        categorias_sql, categorias_params = self._adicionar_limite(
          f"""
          SELECT
            {categoria_case} AS categoria,
            COALESCE(SUM({config.amount_expr}), 0) AS valor_total,
            COUNT(DISTINCT {config.document_id_expr}) AS quantidade_documentos
          FROM {config.from_clause}
          {config.reference_join_clause}
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC, 1 ASC
          """,
          [*parametros],
          limite,
        )
        cur.execute(categorias_sql, categorias_params)
        top_categorias_rows = cur.fetchall()
        logger.info(
          "SQL analise_fiscal_por_dimensao_categorias linhas=%s tempo=%.3fs parametros=%s",
          len(top_categorias_rows),
          perf_counter() - inicio,
          categorias_params,
        )
        top_categorias = [
          {
            "categoria": categoria,
            "valor_total": valor_total or Decimal("0.00"),
            "participacao_percentual": (
              ((valor_total or Decimal("0.00")) / total_movimentado) * Decimal("100")
              if total_movimentado
              else Decimal("0.00")
            ),
            "quantidade_documentos": quantidade_docs or 0,
          }
          for categoria, valor_total, quantidade_docs in top_categorias_rows
        ]

        inicio = perf_counter()
        dimensoes_sql, dimensoes_params = self._adicionar_limite(
          f"""
          SELECT
            COALESCE(NULLIF({config.dimension_code_display_expr}, ''), %s) AS codigo,
            COALESCE(NULLIF(TRIM({config.dimension_description_expr}), ''), %s) AS descricao,
            COALESCE(SUM({config.amount_expr}), 0) AS valor_total
          FROM {config.from_clause}
          {config.reference_join_clause}
          WHERE {where_clause}
          GROUP BY 1, 2
          ORDER BY 3 DESC, 1 ASC
          """,
          [config.unknown_code, config.unknown_description, *parametros],
          limite,
        )
        cur.execute(dimensoes_sql, dimensoes_params)
        top_dimensoes_rows = cur.fetchall()
        logger.info(
          "SQL analise_fiscal_por_dimensao_dimensoes linhas=%s tempo=%.3fs parametros=%s",
          len(top_dimensoes_rows),
          perf_counter() - inicio,
          dimensoes_params,
        )
        top_dimensoes = [
          {
            "codigo": codigo,
            "descricao": descricao,
            "valor_total": valor_total or Decimal("0.00"),
            "participacao_percentual": (
              ((valor_total or Decimal("0.00")) / total_movimentado) * Decimal("100")
              if total_movimentado
              else Decimal("0.00")
            ),
          }
          for codigo, descricao, valor_total in top_dimensoes_rows
        ]

    return {
      "total_movimentado": total_movimentado or Decimal("0.00"),
      "quantidade_documentos": quantidade_documentos or 0,
      "quantidade_dimensoes": quantidade_dimensoes or 0,
      "top_categorias": top_categorias,
      "top_dimensoes": top_dimensoes,
    }
