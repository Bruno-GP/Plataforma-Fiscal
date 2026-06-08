from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.repositories.fiscal.fiscal_repository import FiscalRepository


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

_fiscal_repository = FiscalRepository()


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
    return _fiscal_repository._construir_case_categoria_fiscal(config)


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
    tipo_operacao: Optional[str] = None,
    codigos_tributos: Optional[list[str]] = None,
) -> Decimal:
    return _fiscal_repository.obter_total_impostos_complementares_documentos(
        conn_params=conn_params,
        origem_documento=origem_documento,
        emitente_cnpj=emitente_cnpj,
        periodo_ano=periodo_ano,
        periodo_mes=periodo_mes,
        tipo_operacao=tipo_operacao,
        codigos_tributos=codigos_tributos,
    )


def obter_total_tributos_reforma_documentos(
    conn_params: dict[str, object],
    origem_documento: str,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    tipo_operacao: Optional[str] = None,
) -> Decimal:
    return _fiscal_repository.obter_total_tributos_reforma_documentos(
        conn_params=conn_params,
        origem_documento=origem_documento,
        emitente_cnpj=emitente_cnpj,
        periodo_ano=periodo_ano,
        periodo_mes=periodo_mes,
        tipo_operacao=tipo_operacao,
    )


def obter_totais_tributos_documentos_por_periodo(
    conn_params: dict[str, object],
    origem_documento: str,
    emitente_cnpj: str,
    periodos: list[tuple[int, Optional[int]]],
    tipo_operacao: Optional[str] = None,
) -> dict[tuple[int, Optional[int]], dict[str, Decimal]]:
    return _fiscal_repository.obter_totais_tributos_documentos_por_periodo(
        conn_params=conn_params,
        origem_documento=origem_documento,
        emitente_cnpj=emitente_cnpj,
        periodos=periodos,
        tipo_operacao=tipo_operacao,
    )


def analisar_fiscal_por_dimensao(
    conn_params: dict[str, object],
    config: FiscalDimensionConfig,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: Optional[int] = None,
) -> dict:
    return _fiscal_repository.analisar_fiscal_por_dimensao(
        conn_params=conn_params,
        config=config,
        emitente_cnpj=emitente_cnpj,
        periodo_ano=periodo_ano,
        periodo_mes=periodo_mes,
        limite=limite,
    )
