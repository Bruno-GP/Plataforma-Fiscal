from __future__ import annotations

from typing import Literal

from fastapi import HTTPException, status

from app.services.AI.openai_report_service import OpenAIReportService


TipoRelatorioIA = Literal["compras", "vendas", "clientes"]


def injetar_relatorio_ia(
    resultado: dict,
    tipo: TipoRelatorioIA,
    formato_relatorio: str,
    layout: str | None = None,
) -> None:
    ia_service = OpenAIReportService()
    if not ia_service.disponivel():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Integracao com OpenAI indisponivel. "
                "Configure OPENAI_API_KEY no ambiente da API."
            ),
        )

    if tipo == "compras":
        resultado["relatorio_ia"] = ia_service.gerar_relatorio_compras(
            resultado,
            formato_relatorio,
            layout,
        )
    elif tipo == "vendas":
        resultado["relatorio_ia"] = ia_service.gerar_relatorio_vendas(
            resultado,
            formato_relatorio,
            layout,
        )
    elif tipo == "clientes":
        resultado["relatorio_ia"] = ia_service.gerar_relatorio_clientes(
            resultado,
            formato_relatorio,
        )
