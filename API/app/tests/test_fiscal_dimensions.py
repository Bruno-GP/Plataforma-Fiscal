from decimal import Decimal

from app.services.fiscal.fiscal_dimensions import (
    construir_resposta_fiscal_cfop,
    construir_resposta_fiscal_ncm,
    construir_top_cfops,
    construir_top_ncms,
)


def _resultado_dimensao():
    return {
        "total_movimentado": Decimal("1000"),
        "quantidade_documentos": 8,
        "quantidade_dimensoes": 2,
        "top_categorias": [{"categoria": "Venda"}],
        "top_dimensoes": [
            {
                "codigo": "5102",
                "descricao": "Venda",
                "valor_total": Decimal("700"),
                "participacao_percentual": Decimal("70"),
            }
        ],
    }


def test_construir_top_cfops():
    assert construir_top_cfops(_resultado_dimensao()["top_dimensoes"]) == [
        {
            "cfop": "5102",
            "descricao": "Venda",
            "valor_total": Decimal("700"),
            "participacao_percentual": Decimal("70"),
        }
    ]


def test_construir_top_ncms():
    assert construir_top_ncms(_resultado_dimensao()["top_dimensoes"]) == [
        {
            "ncm": "5102",
            "descricao": "Venda",
            "valor_total": Decimal("700"),
            "participacao_percentual": Decimal("70"),
        }
    ]


def test_construir_resposta_fiscal_cfop():
    resposta = construir_resposta_fiscal_cfop(
        "12345678000190",
        2025,
        7,
        _resultado_dimensao(),
        Decimal("50"),
        Decimal("10"),
    )

    assert resposta["emitente_cnpj"] == "12345678000190"
    assert resposta["quantidade_cfops"] == 2
    assert resposta["top_categorias"] == [{"categoria": "Venda"}]
    assert resposta["top_cfops"][0]["cfop"] == "5102"
    assert resposta["total_impostos_complementares"] == Decimal("50")
    assert resposta["total_tributos_reforma"] == Decimal("10")


def test_construir_resposta_fiscal_ncm():
    resposta = construir_resposta_fiscal_ncm(
        "12345678000190",
        2025,
        7,
        _resultado_dimensao(),
        Decimal("50"),
        Decimal("10"),
    )

    assert resposta["emitente_cnpj"] == "12345678000190"
    assert resposta["quantidade_ncms"] == 2
    assert resposta["top_ncms"][0]["ncm"] == "5102"
    assert "top_categorias" not in resposta
