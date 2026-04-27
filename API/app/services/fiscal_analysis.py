from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import psycopg


UF_PARA_REGIAO = {
    "AC": "Norte",
    "AL": "Nordeste",
    "AP": "Norte",
    "AM": "Norte",
    "BA": "Nordeste",
    "CE": "Nordeste",
    "DF": "Centro-Oeste",
    "ES": "Sudeste",
    "GO": "Centro-Oeste",
    "MA": "Nordeste",
    "MT": "Centro-Oeste",
    "MS": "Centro-Oeste",
    "MG": "Sudeste",
    "PA": "Norte",
    "PB": "Nordeste",
    "PR": "Sul",
    "PE": "Nordeste",
    "PI": "Nordeste",
    "RJ": "Sudeste",
    "RN": "Nordeste",
    "RS": "Sul",
    "RO": "Norte",
    "RR": "Norte",
    "SC": "Sul",
    "SP": "Sudeste",
    "SE": "Nordeste",
    "TO": "Norte",
}


@dataclass(frozen=True)
class FiscalDimensionConfig:
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


def obter_regiao_por_uf(uf: object) -> str | None:
    uf_normalizada = str(uf or "").strip().upper()
    return UF_PARA_REGIAO.get(uf_normalizada)


def _construir_case_categoria_fiscal(config: FiscalDimensionConfig) -> str:
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


def _adicionar_limite(sql: str, params: list[object], limite: Optional[int]) -> tuple[str, list[object]]:
    if limite is None:
        return sql, params

    return f"{sql}\nLIMIT %s", [*params, limite]


def obter_total_impostos_complementares_documentos(
    conn_params: dict[str, object],
    origem_documento: str,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
) -> Decimal:
    coluna_documento = "nota_id" if origem_documento == "nfe" else "sped_documento_id"
    filtros = [
        f"dt.{coluna_documento} IS NOT NULL",
        "regexp_replace(dt.empresa_cnpj, '\\D', '', 'g') = %s",
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

    with psycopg.connect(**conn_params) as conn:
        with conn.cursor() as cur:
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
                WHERE {' AND '.join(filtros)}
                """,
                parametros,
            )
            row = cur.fetchone()

    return row[0] if row else Decimal("0.00")


def analisar_fiscal_por_dimensao(
    conn_params: dict[str, object],
    config: FiscalDimensionConfig,
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
    categoria_case = _construir_case_categoria_fiscal(config)

    with psycopg.connect(**conn_params) as conn:
        with conn.cursor() as cur:
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
            total_movimentado = resumo_row[0] if resumo_row else Decimal("0.00")
            quantidade_documentos = resumo_row[1] if resumo_row else 0
            quantidade_dimensoes = resumo_row[2] if resumo_row else 0

            categorias_sql, categorias_params = _adicionar_limite(
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
                for categoria, valor_total, quantidade_docs in cur.fetchall()
            ]

            dimensoes_sql, dimensoes_params = _adicionar_limite(
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
                for codigo, descricao, valor_total in cur.fetchall()
            ]

    return {
        "total_movimentado": total_movimentado or Decimal("0.00"),
        "quantidade_documentos": quantidade_documentos or 0,
        "quantidade_dimensoes": quantidade_dimensoes or 0,
        "top_categorias": top_categorias,
        "top_dimensoes": top_dimensoes,
    }
