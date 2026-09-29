from decimal import Decimal

from app.services.fiscal.fiscal_clients import (
    construir_filtros_clientes_nfe,
    construir_filtros_clientes_sped,
    construir_item_cliente_analise,
    construir_params_ranking_clientes,
    construir_ranking_clientes,
    construir_resposta_analise_clientes,
)


def test_construir_filtros_clientes_nfe_com_periodo():
    where_clause, params = construir_filtros_clientes_nfe(
        "12345678000190",
        periodo_ano=2025,
        periodo_mes=4,
    )

    assert "regexp_replace(UPPER(COALESCE(n.emitente_cnpj, '')), '[^0-9A-Z]', '', 'g') = %s" in where_clause
    assert "LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('5','6','7')" in where_clause
    assert "EXTRACT(YEAR FROM n.data_emissao) = %s" in where_clause
    assert "EXTRACT(MONTH FROM n.data_emissao) = %s" in where_clause
    assert params == ["12345678000190", 2025, 4]


def test_construir_filtros_clientes_sped_com_periodo():
    where_clause, params = construir_filtros_clientes_sped(
        "12345678000190",
        periodo_ano=2025,
        periodo_mes=4,
    )

    assert where_clause == (
        "regexp_replace(UPPER(d.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s "
        "AND d.tipo_operacao = 'saida' "
        "AND EXTRACT(YEAR FROM d.data_emissao) = %s "
        "AND EXTRACT(MONTH FROM d.data_emissao) = %s"
    )
    assert params == ["12345678000190", 2025, 4]


def test_construir_params_ranking_clientes_repete_total_e_preserva_limite():
    params = construir_params_ranking_clientes(
        Decimal("150.50"),
        ["12345678000190", 2025],
        10,
    )

    assert params == [Decimal("150.50"), Decimal("150.50"), "12345678000190", 2025, 10]


def test_construir_item_cliente_analise_normaliza_valores_vazios():
    item = construir_item_cliente_analise("Cliente A", None, None, None, None)

    assert item == {
        "cliente": "Cliente A",
        "valor_total": Decimal("0.00"),
        "quantidade_documentos": 0,
        "ticket_medio": Decimal("0.00"),
        "percentual_participacao": Decimal("0.00"),
    }


def test_construir_ranking_clientes():
    ranking = construir_ranking_clientes([
        ("Cliente A", Decimal("100"), 2, Decimal("50"), Decimal("25")),
    ])

    assert ranking == [
        {
            "cliente": "Cliente A",
            "valor_total": Decimal("100"),
            "quantidade_documentos": 2,
            "ticket_medio": Decimal("50"),
            "percentual_participacao": Decimal("25"),
        }
    ]


def test_construir_resposta_analise_clientes():
    top_valor = [{"cliente": "Cliente A"}]
    top_quantidade = [{"cliente": "Cliente B"}]
    resposta = construir_resposta_analise_clientes(
        "12345678000190",
        2025,
        4,
        Decimal("300"),
        2,
        top_valor,
        top_quantidade,
    )

    assert resposta == {
        "emitente_cnpj": "12345678000190",
        "periodo_ano": 2025,
        "periodo_mes": 4,
        "total_vendido": Decimal("300"),
        "total_clientes": 2,
        "top_clientes_valor": top_valor,
        "top_clientes_quantidade": top_quantidade,
    }
