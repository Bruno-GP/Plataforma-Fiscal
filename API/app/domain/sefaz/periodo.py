from __future__ import annotations

from datetime import date


def intervalo_do_ano(ano: int) -> tuple[date, date]:
    return date(ano, 1, 1), date(ano, 12, 31)
