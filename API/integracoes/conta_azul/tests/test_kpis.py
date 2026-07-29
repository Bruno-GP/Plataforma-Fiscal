from __future__ import annotations

from datetime import date
from decimal import Decimal

from contaazul.kpis import agregar_kpis_mensais
from contaazul.models import Venda


def _venda(id_: str, data: date, total: float, cliente_id: str | None = None) -> Venda:
    return Venda(id=id_, data=data, total=total, cliente={"id": cliente_id} if cliente_id else None)


def test_agrega_vendas_do_mesmo_mes():
    vendas = [
        _venda("1", date(2026, 1, 5), 100.0, "c1"),
        _venda("2", date(2026, 1, 20), 50.0, "c1"),
        _venda("3", date(2026, 1, 28), 25.0, "c2"),
    ]

    resultado = agregar_kpis_mensais(vendas)

    kpi = resultado[date(2026, 1, 1)]
    assert kpi.total_pedidos == 3
    assert kpi.clientes_ativos == 2
    assert kpi.receita_total == Decimal("175")
    assert kpi.ticket_medio == Decimal("175") / 3


def test_separa_meses_diferentes():
    vendas = [
        _venda("1", date(2026, 1, 5), 100.0, "c1"),
        _venda("2", date(2026, 2, 5), 200.0, "c1"),
    ]

    resultado = agregar_kpis_mensais(vendas)

    assert set(resultado.keys()) == {date(2026, 1, 1), date(2026, 2, 1)}
    assert resultado[date(2026, 1, 1)].total_pedidos == 1
    assert resultado[date(2026, 2, 1)].total_pedidos == 1


def test_venda_sem_cliente_nao_conta_para_clientes_ativos():
    vendas = [_venda("1", date(2026, 1, 5), 100.0, cliente_id=None)]

    resultado = agregar_kpis_mensais(vendas)

    kpi = resultado[date(2026, 1, 1)]
    assert kpi.total_pedidos == 1
    assert kpi.clientes_ativos == 0


def test_lista_vazia_retorna_dict_vazio():
    assert agregar_kpis_mensais([]) == {}
