from decimal import Decimal

from app.services.fiscal_purchases import (
    construir_filtros_compras_nfe,
    construir_filtros_compras_sped,
    construir_params_com_limite_compras,
    construir_ranking_fornecedores_compras,
    construir_ranking_produtos_compras,
    construir_resposta_analise_compras,
)


def test_construir_filtros_compras_nfe_com_periodo():
    where_clause, params = construir_filtros_compras_nfe(
        "12345678000190",
        periodo_ano=2025,
        periodo_mes=6,
    )

    assert "regexp_replace(COALESCE(n.destinatario_documento, ''), '\\D', '', 'g') = %s" in where_clause
    assert "regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g') = %s" in where_clause
    assert "LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('1','2','3')" in where_clause
    assert params == ["12345678000190", "12345678000190", 2025, 6]


def test_construir_filtros_compras_sped_com_periodo():
    where_clause, params = construir_filtros_compras_sped(
        "12345678000190",
        periodo_ano=2025,
        periodo_mes=6,
    )

    assert where_clause == (
        "regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s "
        "AND d.tipo_operacao = 'entrada' "
        "AND EXTRACT(YEAR FROM d.data_emissao) = %s "
        "AND EXTRACT(MONTH FROM d.data_emissao) = %s"
    )
    assert params == ["12345678000190", 2025, 6]


def test_construir_params_com_limite_compras():
    assert construir_params_com_limite_compras(["cnpj", 2025], 5) == ["cnpj", 2025, 5]


def test_construir_rankings_fornecedores_e_produtos_compras():
    fornecedores = construir_ranking_fornecedores_compras([
        ("Fornecedor A", Decimal("100"), 2),
    ])
    produtos = construir_ranking_produtos_compras([
        ("Produto A", Decimal("80"), Decimal("4")),
    ])

    assert fornecedores == [
        {
            "fornecedor": "Fornecedor A",
            "valor_total": Decimal("100"),
            "quantidade_documentos": 2,
        }
    ]
    assert produtos == [
        {
            "produto": "Produto A",
            "valor_total": Decimal("80"),
            "quantidade_total": Decimal("4"),
        }
    ]


def test_construir_resposta_analise_compras():
    resposta = construir_resposta_analise_compras(
        "12345678000190",
        2025,
        6,
        Decimal("200"),
        Decimal("20"),
        Decimal("5"),
        [{"fornecedor": "A"}],
        [{"fornecedor": "B"}],
        [{"produto": "P1"}],
        [{"produto": "P2"}],
    )

    assert resposta == {
        "emitente_cnpj": "12345678000190",
        "periodo_ano": 2025,
        "periodo_mes": 6,
        "total_comprado": Decimal("200"),
        "total_impostos_complementares": Decimal("20"),
        "total_tributos_reforma": Decimal("5"),
        "top_fornecedores_valor": [{"fornecedor": "A"}],
        "top_fornecedores_quantidade": [{"fornecedor": "B"}],
        "top_produtos_valor": [{"produto": "P1"}],
        "top_produtos_quantidade": [{"produto": "P2"}],
    }
