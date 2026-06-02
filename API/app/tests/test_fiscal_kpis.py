from decimal import Decimal

from app.services.fiscal_kpis import (
    calcular_variacao_percentual,
    construir_comparativo_kpis,
    construir_dashboard_vendas_response,
    construir_nfe_kpi_consulta_de_row,
    construir_nfe_kpi_de_row,
    construir_periodos_dashboard,
    construir_resumo_dashboard,
    construir_serie_mensal_dashboard,
    construir_sped_kpi_consulta,
    normalizar_top_cidades,
    obter_anos_disponiveis_kpis,
    resolver_ano_referencia_dashboard,
    resolver_periodo_anterior_kpi,
    selecionar_resultados_dashboard,
)


def _consulta_kpi(
    ano: int,
    mes: int,
    total_vendas: Decimal = Decimal("100"),
    quantidade_notas: int = 2,
):
    return construir_nfe_kpi_consulta_de_row((
        ano,
        mes,
        "12345678000190",
        1,
        2,
        total_vendas,
        quantidade_notas,
        Decimal("50"),
        Decimal("80"),
        Decimal("20"),
        Decimal("10"),
        Decimal("5"),
        Decimal("3"),
        Decimal("2"),
        [{"cliente": "Cliente A", "valor_total": total_vendas}],
        [{"produto": "Produto A", "valor_total": total_vendas}],
        [{"municipio": "Sao Paulo", "valor_total": total_vendas}],
    ))


def _nfe_kpi(total_vendas: Decimal = Decimal("100"), quantidade_notas: int = 2):
    return construir_nfe_kpi_de_row((
        "12345678000190",
        1,
        2,
        total_vendas,
        quantidade_notas,
        Decimal("50"),
        Decimal("80"),
        Decimal("20"),
        Decimal("10"),
        Decimal("5"),
        Decimal("3"),
        Decimal("2"),
        [],
        [],
        [],
    ))


def test_normalizar_top_cidades_ignora_itens_invalidos_e_fallback():
    cidades = normalizar_top_cidades([
        {"municipio": "Sao Paulo", "valor_total": Decimal("10")},
        {"cidade": "", "valor_total": Decimal("5")},
        "invalido",
    ])

    assert cidades == [
        {"municipio": "Sao Paulo", "valor_total": Decimal("10"), "cidade": "Sao Paulo"},
        {"cidade": "Cidade não identificada", "valor_total": Decimal("5")},
    ]


def test_calcular_variacao_percentual():
    assert calcular_variacao_percentual(Decimal("120"), Decimal("100")) == Decimal("20.00")
    assert calcular_variacao_percentual(Decimal("0"), Decimal("0")) == Decimal("0.00")
    assert calcular_variacao_percentual(Decimal("10"), Decimal("0")) is None


def test_resolver_periodo_anterior_kpi():
    assert resolver_periodo_anterior_kpi(2025, 7) == (2025, 6)
    assert resolver_periodo_anterior_kpi(2025, 1) == (2024, 12)
    assert resolver_periodo_anterior_kpi(2025, 7, 2024, 7) == (2024, 7)


def test_construir_comparativo_kpis_com_periodo_anterior():
    comparativo = construir_comparativo_kpis(
        _nfe_kpi(Decimal("120"), 6),
        _nfe_kpi(Decimal("100"), 4),
    )

    assert comparativo.total_vendas.atual == Decimal("120")
    assert comparativo.total_vendas.anterior == Decimal("100")
    assert comparativo.total_vendas.variacao_percentual == Decimal("20.00")
    assert comparativo.quantidade_notas.atual == 6
    assert comparativo.quantidade_notas.anterior == 4
    assert comparativo.quantidade_notas.variacao_percentual == Decimal("50.00")


def test_construir_comparativo_kpis_sem_periodo_anterior():
    comparativo = construir_comparativo_kpis(_nfe_kpi(Decimal("120"), 6), None)

    assert comparativo.total_vendas.anterior == Decimal("0")
    assert comparativo.total_vendas.variacao_percentual is None
    assert comparativo.quantidade_notas.anterior == 0
    assert comparativo.quantidade_notas.variacao_percentual is None


def test_construir_nfe_kpi_de_row():
    kpi = construir_nfe_kpi_de_row((
        "12345678000190",
        1,
        2,
        Decimal("100"),
        3,
        Decimal("33.33"),
        Decimal("80"),
        Decimal("20"),
        Decimal("10"),
        Decimal("5"),
        Decimal("3"),
        Decimal("2"),
        [{"cliente": "A"}],
        [{"produto": "P"}],
        [{"municipio": "Sao Paulo"}],
    ))

    assert kpi.emitente_cnpj == "12345678000190"
    assert kpi.total_vendas == Decimal("100")
    assert kpi.top_cidades[0]["cidade"] == "Sao Paulo"


def test_construir_nfe_kpi_consulta_de_row():
    consulta = construir_nfe_kpi_consulta_de_row((
        2025,
        7,
        "12345678000190",
        1,
        2,
        Decimal("100"),
        3,
        Decimal("33.33"),
        Decimal("80"),
        Decimal("20"),
        Decimal("10"),
        Decimal("5"),
        Decimal("3"),
        Decimal("2"),
        [],
        [],
        [],
    ))

    assert consulta.periodo_ano == 2025
    assert consulta.periodo_mes == 7
    assert consulta.kpis.quantidade_notas == 3


def test_construir_sped_kpi_consulta():
    consulta = construir_sped_kpi_consulta(
        (
            1,
            2,
            "12345678000190",
            2025,
            7,
            Decimal("100"),
            3,
            Decimal("33.33"),
            Decimal("0"),
            Decimal("0"),
            Decimal("10"),
            Decimal("5"),
            Decimal("3"),
            Decimal("2"),
        ),
        top_clientes=[{"cliente": "A"}],
        top_produtos=[{"produto": "P"}],
        top_cidades=[{"cidade": "Sao Paulo"}],
    )

    assert consulta.periodo_ano == 2025
    assert consulta.kpis.top_clientes == [{"cliente": "A"}]
    assert consulta.kpis.total_icms == Decimal("10")


def test_obter_anos_disponiveis_kpis_e_resolver_ano_referencia():
    resultados = [
        _consulta_kpi(2024, 12),
        _consulta_kpi(2025, 1),
        _consulta_kpi(2025, 2),
    ]

    anos = obter_anos_disponiveis_kpis(resultados)

    assert anos == [2025, 2024]
    assert resolver_ano_referencia_dashboard(None, anos) == 2025
    assert resolver_ano_referencia_dashboard(2024, anos) == 2024
    assert resolver_ano_referencia_dashboard(None, []) is None


def test_selecionar_resultados_dashboard_mensal_e_anual():
    jan = _consulta_kpi(2025, 1)
    fev = _consulta_kpi(2025, 2)
    dez_anterior = _consulta_kpi(2024, 12)

    atual, anterior, ano_anterior, mes_anterior = selecionar_resultados_dashboard(
        [jan, fev],
        [dez_anterior],
        2025,
        1,
    )

    assert atual == [jan]
    assert anterior == [dez_anterior]
    assert (ano_anterior, mes_anterior) == (2024, 12)

    atual, anterior, ano_anterior, mes_anterior = selecionar_resultados_dashboard(
        [jan, fev],
        [dez_anterior],
        2025,
        None,
    )

    assert atual == [jan, fev]
    assert anterior == [dez_anterior]
    assert (ano_anterior, mes_anterior) == (2024, None)


def test_construir_periodos_dashboard_inclui_atual_anterior_e_meses_da_serie():
    periodos = construir_periodos_dashboard(
        2025,
        7,
        2025,
        6,
        [_consulta_kpi(2025, 7), _consulta_kpi(2025, 8)],
    )

    assert periodos == {(2025, 7), (2025, 6), (2025, 8)}


def test_construir_resumo_e_serie_mensal_dashboard():
    julho = _consulta_kpi(2025, 7, Decimal("100"), 2)
    agosto = _consulta_kpi(2025, 8, Decimal("200"), 4)
    totais_vendidos = {
        (2025, 7): Decimal("150"),
        (2025, 8): Decimal("250"),
    }
    totais_tributos = {
        (2025, 7): {
            "total_impostos_complementares": Decimal("11"),
            "total_tributos_reforma": Decimal("4"),
        },
        (2025, 8): {
            "total_impostos_complementares": Decimal("12"),
            "total_tributos_reforma": Decimal("5"),
        },
    }

    resumo = construir_resumo_dashboard(
        [julho],
        (2025, 7),
        totais_vendidos,
        totais_tributos,
        limite=5,
    )
    serie = construir_serie_mensal_dashboard(
        2025,
        [agosto, julho],
        totais_vendidos,
        totais_tributos,
    )

    assert resumo.total_vendido == Decimal("150")
    assert resumo.total_impostos_complementares == Decimal("11")
    assert resumo.total_tributos_reforma == Decimal("4")
    assert [item.periodo_mes for item in serie] == [7, 8]
    assert serie[0].total_vendido == Decimal("150")
    assert serie[0].total_impostos == Decimal("20")


def test_construir_dashboard_vendas_response():
    resumo_atual = construir_resumo_dashboard(
        [_consulta_kpi(2025, 7)],
        (2025, 7),
        {(2025, 7): Decimal("100")},
        {},
        limite=5,
    )
    resumo_anterior = construir_resumo_dashboard([], (2025, 6), {}, {}, limite=5)
    serie_mensal = construir_serie_mensal_dashboard(2025, [_consulta_kpi(2025, 7)], {}, {})

    response = construir_dashboard_vendas_response(
        "12345678000190",
        2025,
        7,
        [2025, 2024],
        resumo_atual,
        resumo_anterior,
        serie_mensal,
    )

    assert response.status == "ok"
    assert response.emitente_cnpj == "12345678000190"
    assert response.periodo_ano == 2025
    assert response.periodo_mes == 7
    assert response.anos_disponiveis == [2025, 2024]
    assert response.serie_mensal == serie_mensal
