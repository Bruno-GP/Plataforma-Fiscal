from __future__ import annotations

from typing import Literal

from fastapi import HTTPException, status

from app.api.shared.analytics import obter_periodo_anterior
from app.services.fiscal_analysis import (
    obter_total_impostos_complementares_documentos,
    obter_total_tributos_reforma_documentos,
)


OrigemDocumento = Literal["nfe", "sped"]


def montar_dashboard_compras(
    *,
    consulta_service,
    emitente_cnpj: str,
    origem_documento: OrigemDocumento,
    periodo_ano: int | None,
    periodo_mes: int | None,
    limite: int,
) -> dict:
    anos_disponiveis = sorted(
        {
            item.periodo_ano
            for item in consulta_service.listar_kpis(emitente_cnpj=emitente_cnpj, limite=120)
            if item.periodo_ano
        },
        reverse=True,
    )

    ano_referencia = periodo_ano or (anos_disponiveis[0] if anos_disponiveis else None)
    if ano_referencia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum periodo disponivel para o emitente informado.",
        )

    ano_anterior, mes_anterior = obter_periodo_anterior(ano_referencia, periodo_mes)

    resumo_atual = consulta_service.analisar_compras(
        emitente_cnpj=emitente_cnpj,
        periodo_ano=ano_referencia,
        periodo_mes=periodo_mes,
        limite=limite,
    )
    resumo_anterior = consulta_service.analisar_compras(
        emitente_cnpj=emitente_cnpj,
        periodo_ano=ano_anterior,
        periodo_mes=mes_anterior,
        limite=limite,
    )

    serie_mensal = [
        {
            "periodo_ano": ano_referencia,
            "periodo_mes": mes,
            "total_comprado": consulta_service.analisar_compras(
                emitente_cnpj=emitente_cnpj,
                periodo_ano=ano_referencia,
                periodo_mes=mes,
                limite=limite,
            )["total_comprado"],
            "total_impostos_complementares": obter_total_impostos_complementares_documentos(
                consulta_service.conn_params,
                origem_documento,
                emitente_cnpj,
                ano_referencia,
                mes,
                "entrada",
            ),
            "total_tributos_reforma": obter_total_tributos_reforma_documentos(
                consulta_service.conn_params,
                origem_documento,
                emitente_cnpj,
                ano_referencia,
                mes,
                "entrada",
            ),
        }
        for mes in range(1, 13)
    ]

    return {
        "status": "ok",
        "emitente_cnpj": emitente_cnpj,
        "periodo_ano": ano_referencia,
        "periodo_mes": periodo_mes,
        "anos_disponiveis": anos_disponiveis,
        "resumo_atual": {
            "status": "ok",
            **resumo_atual,
            "total_impostos_complementares": obter_total_impostos_complementares_documentos(
                consulta_service.conn_params,
                origem_documento,
                emitente_cnpj,
                ano_referencia,
                periodo_mes,
                "entrada",
            ),
            "total_tributos_reforma": obter_total_tributos_reforma_documentos(
                consulta_service.conn_params,
                origem_documento,
                emitente_cnpj,
                ano_referencia,
                periodo_mes,
                "entrada",
            ),
        },
        "resumo_anterior": {
            "status": "ok",
            **resumo_anterior,
            "total_impostos_complementares": obter_total_impostos_complementares_documentos(
                consulta_service.conn_params,
                origem_documento,
                emitente_cnpj,
                ano_anterior,
                mes_anterior,
                "entrada",
            ),
            "total_tributos_reforma": obter_total_tributos_reforma_documentos(
                consulta_service.conn_params,
                origem_documento,
                emitente_cnpj,
                ano_anterior,
                mes_anterior,
                "entrada",
            ),
        },
        "serie_mensal": serie_mensal,
    }
