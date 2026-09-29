from decimal import Decimal

from app.services.fiscal.fiscal_sales import (
    construir_filtros_vendas_sped,
    construir_item_cfop_vendas,
    construir_params_com_limite,
    construir_ranking_cidades_vendas,
    construir_ranking_clientes_vendas,
    construir_ranking_produtos_vendas,
    construir_ranking_regioes_vendas,
    construir_resposta_analise_vendas,
)


def test_construir_filtros_vendas_sped_com_periodo():
    where_clause, params = construir_filtros_vendas_sped(
        "12345678000190",
        periodo_ano=2025,
        periodo_mes=5,
    )

    assert where_clause == (
        "regexp_replace(UPPER(d.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s "
        "AND d.tipo_operacao = 'saida' "
        "AND EXTRACT(YEAR FROM d.data_emissao) = %s "
        "AND EXTRACT(MONTH FROM d.data_emissao) = %s"
    )
    assert params == ["12345678000190", 2025, 5]


def test_construir_params_com_limite():
    assert construir_params_com_limite(["cnpj", 2025], 10) == ["cnpj", 2025, 10]


def test_construir_rankings_de_clientes_e_produtos():
    clientes = construir_ranking_clientes_vendas([
        ("Cliente A", Decimal("100"), 2),
    ])
    produtos = construir_ranking_produtos_vendas([
        ("Produto A", Decimal("80"), Decimal("4")),
    ])

    assert clientes[0]["valor_total"] == Decimal("100")
    assert clientes[0]["quantidade_documentos"] == 2
    assert produtos[0]["produto"] == "Produto A"
    assert produtos[0]["quantidade_total"] == Decimal("4")


def test_construir_item_cfop_vendas_calcula_participacao():
    item = construir_item_cfop_vendas("5102", "Venda", Decimal("25"), Decimal("100"))

    assert item["participacao_percentual"] == Decimal("25.00")


def test_construir_ranking_cidades_vendas_com_normalizacao():
    ranking = construir_ranking_cidades_vendas(
        [("3550308", "SP", Decimal("50"), 3)],
        normalizar_cidade=lambda _: "Sao Paulo",
    )

    assert ranking == [
        {
            "cidade": "Sao Paulo",
            "uf": "SP",
            "valor_total": Decimal("50"),
            "quantidade_documentos": 3,
        }
    ]


def test_construir_ranking_regioes_vendas_agrega_por_regiao_e_limita():
    ranking = construir_ranking_regioes_vendas(
        [
            ("SP", Decimal("100"), 2),
            ("RJ", Decimal("50"), 1),
            ("AM", Decimal("25"), 1),
            ("XX", Decimal("999"), 9),
        ],
        obter_regiao_por_uf=lambda uf: {"SP": "Sudeste", "RJ": "Sudeste", "AM": "Norte"}.get(uf),
        limite=1,
    )

    assert ranking == [
        {
            "regiao": "Sudeste",
            "valor_total": Decimal("150.00"),
            "quantidade_documentos": 3,
        }
    ]


def test_construir_resposta_analise_vendas():
    resposta = construir_resposta_analise_vendas(
        "12345678000190",
        2025,
        5,
        Decimal("100"),
        Decimal("10"),
        Decimal("3"),
        [{"cliente": "A"}],
        [{"cliente": "B"}],
        [{"produto": "P1"}],
        [{"produto": "P2"}],
        [{"cfop": "5102"}],
        [{"regiao": "Sudeste"}],
        [{"cidade": "Sao Paulo"}],
    )

    assert resposta["total_vendido"] == Decimal("100")
    assert resposta["total_impostos_complementares"] == Decimal("10")
    assert resposta["top_cfops_valor"] == [{"cfop": "5102"}]
