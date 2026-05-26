from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.services.shared.ia_report_service import TipoRelatorioIA, injetar_relatorio_ia


def executar_analise_com_relatorio_ia(
    *,
    analise_fn: Callable[..., dict],
    analise_kwargs: dict[str, Any],
    gerar_relatorio_ia: bool,
    tipo_relatorio: TipoRelatorioIA,
    formato_relatorio: str,
    layout: str | None = None,
) -> dict:
    resultado = analise_fn(**analise_kwargs)
    if gerar_relatorio_ia:
        injetar_relatorio_ia(resultado, tipo_relatorio, formato_relatorio, layout)
    return resultado
