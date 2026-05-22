from decimal import Decimal

from app.services.fiscal_hierarchy import (
    calcular_imposto_por_percentual,
    calcular_percentual_imposto,
    construir_filtros_hierarquia_nfe,
    construir_filtros_hierarquia_sped,
    construir_item_cidade,
    construir_item_estado,
    construir_item_hierarquia_completa,
    construir_item_ncm,
    construir_item_produto,
    construir_resposta_hierarquia_fiscal,
    deve_montar_hierarquia_legado,
    normalizar_paginacao_hierarquia,
    resolver_nivel_hierarquia,
)


def test_calcular_percentual_imposto_com_faturamento():
    assert calcular_percentual_imposto(Decimal("15"), Decimal("300")) == Decimal("5.00")


def test_calcular_percentual_imposto_sem_faturamento():
    assert calcular_percentual_imposto(Decimal("15"), Decimal("0")) == Decimal("0.00")


def test_calcular_imposto_por_percentual_com_faturamento():
    assert calcular_imposto_por_percentual(Decimal("300"), Decimal("5")) == Decimal("15")


def test_resolver_nivel_hierarquia_respeita_nivel_explicito():
    assert resolver_nivel_hierarquia("cidade", "SP", None, None) == "cidade"


def test_resolver_nivel_hierarquia_deriva_por_filtros():
    assert resolver_nivel_hierarquia(None, None, None, None) == "estado"
    assert resolver_nivel_hierarquia(None, "SP", None, None) == "cidade"
    assert resolver_nivel_hierarquia(None, "SP", "Sao Paulo", None) == "ncm"
    assert resolver_nivel_hierarquia(None, "SP", "Sao Paulo", "12345678") == "produto"


def test_normalizar_paginacao_hierarquia():
    assert normalizar_paginacao_hierarquia(None, -10) == (100000, 0)
    assert normalizar_paginacao_hierarquia(50, 20) == (50, 20)


def test_deve_montar_hierarquia_legado_apenas_na_primeira_pagina_sem_filtros():
    assert deve_montar_hierarquia_legado(None, None, None, None, None, 0) is True
    assert deve_montar_hierarquia_legado(None, "SP", None, None, None, 0) is False
    assert deve_montar_hierarquia_legado(None, None, None, None, None, 10) is False
    assert deve_montar_hierarquia_legado("estado", None, None, None, None, 0) is False


def test_construir_filtros_hierarquia_nfe_com_periodo_e_dimensoes():
    where_clause, params = construir_filtros_hierarquia_nfe(
        "12345678000190",
        periodo_ano=2025,
        periodo_mes=3,
        estado=" sp ",
        cidade=" sao paulo ",
        ncm="12.345.678",
        produto_codigo=" P001 ",
    )

    assert "regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g') = %s" in where_clause
    assert "EXTRACT(YEAR FROM n.data_emissao) = %s" in where_clause
    assert "EXTRACT(MONTH FROM n.data_emissao) = %s" in where_clause
    assert "UPPER(COALESCE(NULLIF(TRIM(n.destinatario_uf), ''), 'Sem UF')) = %s" in where_clause
    assert params == ["12345678000190", 2025, 3, "SP", "SAO PAULO", "12345678", "P001"]


def test_construir_filtros_hierarquia_sped_separa_documentos_kpis_e_base():
    filtros = construir_filtros_hierarquia_sped(
        "12345678000190",
        periodo_ano=2025,
        periodo_mes=3,
        estado=" sp ",
        cidade=" sao paulo ",
        ncm="abc",
        produto_codigo=" P001 ",
    )

    assert filtros["where_documentos"] == (
        "regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s "
        "AND d.tipo_operacao = 'saida' "
        "AND EXTRACT(YEAR FROM d.data_emissao) = %s "
        "AND EXTRACT(MONTH FROM d.data_emissao) = %s"
    )
    assert filtros["where_kpis"] == (
        "regexp_replace(cnpj_emitente, '\\D', '', 'g') = %s "
        "AND periodo_ano = %s "
        "AND periodo_mes = %s"
    )
    assert filtros["where_base"] == (
        "UPPER(estado) = %s AND UPPER(cidade) = %s AND ncm = %s AND produto_codigo = %s"
    )
    assert filtros["params_documentos"] == ["12345678000190", 2025, 3]
    assert filtros["params_kpis"] == ["12345678000190", 2025, 3]
    assert filtros["params_base"] == ["SP", "SAO PAULO", "00000000", "P001"]
    assert filtros["params_cte"] == [
        "12345678000190",
        2025,
        3,
        "12345678000190",
        2025,
        3,
    ]


def test_construir_item_estado_calcula_percentual():
    assert construir_item_estado("SP", Decimal("200"), Decimal("20")) == {
        "estado": "SP",
        "faturamento": Decimal("200"),
        "imposto_valor": Decimal("20"),
        "imposto_percentual": Decimal("10.0"),
    }


def test_construir_item_cidade_pode_normalizar_nome():
    item = construir_item_cidade(
        "3550308",
        "SP",
        Decimal("100"),
        Decimal("5"),
        normalizar_cidade=lambda _: "Sao Paulo",
    )

    assert item["cidade"] == "Sao Paulo"
    assert item["uf"] == "SP"
    assert item["imposto_percentual"] == Decimal("5.00")


def test_construir_item_ncm_preserva_quantidade_zero():
    item = construir_item_ncm("00000000", "NCM sem descricao", None, Decimal("0"), Decimal("10"))

    assert item["quantidade_produtos"] == 0
    assert item["imposto_percentual"] == Decimal("0.00")


def test_construir_item_produto():
    item = construir_item_produto("P001", "Produto teste", Decimal("50"), Decimal("2.5"))

    assert item["produto_codigo"] == "P001"
    assert item["produto"] == "Produto teste"
    assert item["imposto_percentual"] == Decimal("5.00")


def test_construir_item_hierarquia_completa_com_flag_sped():
    item = construir_item_hierarquia_completa(
        "SP",
        "3550308",
        "12345678",
        "Descricao NCM",
        "P001",
        "Produto teste",
        Decimal("100"),
        Decimal("12"),
        normalizar_cidade=lambda _: "Sao Paulo",
        sem_item_detalhado=True,
    )

    assert item["cidade"] == "Sao Paulo"
    assert item["uf"] == "SP"
    assert item["sem_item_detalhado"] is True
    assert item["imposto_percentual"] == Decimal("12.00")


def test_construir_resposta_hierarquia_fiscal_monta_contadores_e_paginacao():
    itens = [{"estado": "SP"}, {"estado": "RJ"}]
    resposta = construir_resposta_hierarquia_fiscal(
        emitente_cnpj="12345678000190",
        periodo_ano=2025,
        periodo_mes=3,
        nivel_atual="estado",
        offset=0,
        limite=2,
        total_registros_nivel=3,
        total_faturamento=Decimal("1000"),
        total_impostos=Decimal("100"),
        total_tributos_reforma=Decimal("25"),
        percentual_impostos_sobre_faturamento=Decimal("10"),
        resumo_row=(Decimal("1000"), Decimal("100"), 8, 2, 5, 9, 20),
        hierarquia=[],
        itens_nivel_atual=itens,
        por_estado=itens,
        por_cidade=[],
        por_ncm=[],
        por_produto=[],
    )

    assert resposta["emitente_cnpj"] == "12345678000190"
    assert resposta["possui_mais_registros"] is True
    assert resposta["quantidade_documentos"] == 8
    assert resposta["total_estados"] == 2
    assert resposta["total_cidades"] == 5
    assert resposta["total_ncms"] == 9
    assert resposta["total_produtos"] == 20
    assert resposta["total_tributos_reforma"] == Decimal("25")
    assert resposta["itens_nivel_atual"] == itens


def test_construir_resposta_hierarquia_fiscal_trata_resumo_vazio():
    resposta = construir_resposta_hierarquia_fiscal(
        emitente_cnpj="12345678000190",
        periodo_ano=None,
        periodo_mes=None,
        nivel_atual="estado",
        offset=10,
        limite=10,
        total_registros_nivel=10,
        total_faturamento=None,
        total_impostos=None,
        total_tributos_reforma=Decimal("0"),
        percentual_impostos_sobre_faturamento=Decimal("0"),
        resumo_row=None,
        hierarquia=[],
        itens_nivel_atual=[],
        por_estado=[],
        por_cidade=[],
        por_ncm=[],
        por_produto=[],
    )

    assert resposta["possui_mais_registros"] is False
    assert resposta["total_faturamento"] == Decimal("0.00")
    assert resposta["total_impostos"] == Decimal("0.00")
    assert resposta["quantidade_documentos"] == 0
