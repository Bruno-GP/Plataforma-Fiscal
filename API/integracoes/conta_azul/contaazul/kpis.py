"""Agregacao pura de vendas em KPIs mensais. Sem I/O -- fica facil de testar
isoladamente. A gravacao no Postgres fica em exporters/postgres_kpis_exporter.py.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from contaazul.models import Venda


@dataclass(frozen=True)
class KpiMensal:
    mes: date
    total_pedidos: int
    clientes_ativos: int
    receita_total: Decimal
    ticket_medio: Decimal


def agregar_kpis_mensais(vendas: list[Venda]) -> dict[date, KpiMensal]:
    vendas_por_mes: dict[date, list[Venda]] = defaultdict(list)
    for venda in vendas:
        if venda.data is None:
            continue
        vendas_por_mes[venda.data.replace(day=1)].append(venda)

    resultado: dict[date, KpiMensal] = {}
    for mes, vendas_do_mes in vendas_por_mes.items():
        total_pedidos = len(vendas_do_mes)
        clientes_ativos = len({
            venda.cliente["id"]
            for venda in vendas_do_mes
            if venda.cliente and venda.cliente.get("id")
        })
        receita_total = sum((Decimal(str(venda.total)) for venda in vendas_do_mes if venda.total), Decimal("0"))
        ticket_medio = receita_total / total_pedidos if total_pedidos else Decimal("0")

        resultado[mes] = KpiMensal(
            mes=mes,
            total_pedidos=total_pedidos,
            clientes_ativos=clientes_ativos,
            receita_total=receita_total,
            ticket_medio=ticket_medio,
        )

    return resultado
