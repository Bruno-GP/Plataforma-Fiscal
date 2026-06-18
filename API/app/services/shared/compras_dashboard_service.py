from __future__ import annotations

import logging
from time import perf_counter
from typing import Literal

from fastapi import HTTPException, status

from app.api.shared.analytics import obter_periodo_anterior
from app.services.fiscal.fiscal_analysis import (
    obter_total_impostos_complementares_documentos,
    obter_total_tributos_reforma_documentos,
)


OrigemDocumento = Literal["nfe", "sped"]
logger = logging.getLogger("services.shared.compras_dashboard")


def montar_dashboard_compras(
    *,
    consulta_service,
    emitente_cnpj: str,
    origem_documento: OrigemDocumento,
    periodo_ano: int | None,
    periodo_mes: int | None,
    limite: int,
) -> dict:
    inicio_total = perf_counter()
    logger.info(
        "Montando dashboard compras emitente_cnpj=%s origem_documento=%s periodo_ano=%s periodo_mes=%s limite=%s",
        emitente_cnpj,
        origem_documento,
        periodo_ano,
        periodo_mes,
        limite,
    )

    inicio_anos = perf_counter()
    anos_disponiveis = sorted(
        {
            item.periodo_ano
            for item in consulta_service.listar_kpis(emitente_cnpj=emitente_cnpj, limite=120)
            if item.periodo_ano
        },
        reverse=True,
    )
    logger.info(
        "Dashboard compras anos_disponiveis emitente_cnpj=%s tempo=%.3fs quantidade=%s anos=%s",
        emitente_cnpj,
        perf_counter() - inicio_anos,
        len(anos_disponiveis),
        anos_disponiveis,
    )

    ano_referencia = periodo_ano or (anos_disponiveis[0] if anos_disponiveis else None)
    if ano_referencia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum periodo disponivel para o emitente informado.",
        )

    ano_anterior, mes_anterior = obter_periodo_anterior(ano_referencia, periodo_mes)

    inicio_resumo_atual = perf_counter()
    resumo_atual = consulta_service.analisar_compras(
        emitente_cnpj=emitente_cnpj,
        periodo_ano=ano_referencia,
        periodo_mes=periodo_mes,
        limite=limite,
    )
    logger.info(
        "Dashboard compras resumo_atual emitente_cnpj=%s periodo_ano=%s periodo_mes=%s tempo=%.3fs",
        emitente_cnpj,
        ano_referencia,
        periodo_mes,
        perf_counter() - inicio_resumo_atual,
    )

    inicio_resumo_anterior = perf_counter()
    resumo_anterior = consulta_service.analisar_compras(
        emitente_cnpj=emitente_cnpj,
        periodo_ano=ano_anterior,
        periodo_mes=mes_anterior,
        limite=limite,
    )
    logger.info(
        "Dashboard compras resumo_anterior emitente_cnpj=%s periodo_ano=%s periodo_mes=%s tempo=%.3fs",
        emitente_cnpj,
        ano_anterior,
        mes_anterior,
        perf_counter() - inicio_resumo_anterior,
    )

    serie_mensal = []
    inicio_serie = perf_counter()
    for mes in range(1, 13):
        inicio_mes = perf_counter()
        analise_mes = consulta_service.analisar_compras(
            emitente_cnpj=emitente_cnpj,
            periodo_ano=ano_referencia,
            periodo_mes=mes,
            limite=limite,
        )
        inicio_impostos = perf_counter()
        total_impostos_complementares = obter_total_impostos_complementares_documentos(
            consulta_service.conn_params,
            origem_documento,
            emitente_cnpj,
            ano_referencia,
            mes,
            "entrada",
        )
        tempo_impostos = perf_counter() - inicio_impostos

        inicio_reforma = perf_counter()
        total_tributos_reforma = obter_total_tributos_reforma_documentos(
            consulta_service.conn_params,
            origem_documento,
            emitente_cnpj,
            ano_referencia,
            mes,
            "entrada",
        )
        tempo_reforma = perf_counter() - inicio_reforma

        serie_mensal.append(
            {
                "periodo_ano": ano_referencia,
                "periodo_mes": mes,
                "total_comprado": analise_mes["total_comprado"],
                "total_impostos_complementares": total_impostos_complementares,
                "total_tributos_reforma": total_tributos_reforma,
            }
        )
        logger.info(
            "Dashboard compras serie_mensal emitente_cnpj=%s periodo_ano=%s periodo_mes=%s tempo_analise=%.3fs tempo_impostos=%.3fs tempo_reforma=%.3fs total_comprado=%s",
            emitente_cnpj,
            ano_referencia,
            mes,
            perf_counter() - inicio_mes,
            tempo_impostos,
            tempo_reforma,
            analise_mes["total_comprado"],
        )

    logger.info(
        "Dashboard compras serie_mensal_total emitente_cnpj=%s periodo_ano=%s tempo=%.3fs quantidade=%s",
        emitente_cnpj,
        ano_referencia,
        perf_counter() - inicio_serie,
        len(serie_mensal),
    )

    resultado = {
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

    logger.info(
        "Dashboard compras montado emitente_cnpj=%s periodo_ano=%s periodo_mes=%s tempo_total=%.3fs",
        emitente_cnpj,
        ano_referencia,
        periodo_mes,
        perf_counter() - inicio_total,
    )
    return resultado
