from decimal import Decimal
from datetime import date
from types import SimpleNamespace

import psycopg

from app.domain.nfe.extractor import ItemNota, NotaExtraida
from app.api.shared.company_validation import validar_empresa_sped, validar_empresa_xml
from app.repositories.nfe.notas_repository import NFeNotasRepository
from app.services.sped.sped_consulta_service import SpedConsultaService
from app.services.shared.analise_relatorio_service import executar_analise_com_relatorio_ia
from app.services.shared.compras_dashboard_service import montar_dashboard_compras
from app.services.shared.ia_report_service import injetar_relatorio_ia


CNPJ = "12345678000190"


class FakeNFeConsultaService:
    conn_params = {"dbname": "test"}

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def resolver_emitente_cnpj(self, emitente_cnpj=None, email=None):
        return emitente_cnpj or CNPJ

    def listar_kpis(self, **kwargs):
        self.calls.append(("listar_kpis", kwargs))
        return [
            SimpleNamespace(periodo_ano=2025, periodo_mes=1),
            SimpleNamespace(periodo_ano=2025, periodo_mes=2),
            SimpleNamespace(periodo_ano=2024, periodo_mes=12),
        ]

    def analisar_compras(self, **kwargs):
        self.calls.append(("analisar_compras", kwargs))
        return {
            "emitente_cnpj": kwargs["emitente_cnpj"],
            "periodo_ano": kwargs.get("periodo_ano"),
            "periodo_mes": kwargs.get("periodo_mes"),
            "total_comprado": Decimal("100.00"),
            "top_fornecedores_valor": [{"fornecedor": "Fornecedor A", "valor_total": Decimal("100")}],
            "top_fornecedores_quantidade": [],
            "top_produtos_valor": [],
            "top_produtos_quantidade": [],
        }

    def analisar_fiscal_hierarquia(self, **kwargs):
        self.calls.append(("analisar_fiscal_hierarquia", kwargs))
        return {
            "emitente_cnpj": kwargs["emitente_cnpj"],
            "periodo_ano": kwargs.get("periodo_ano"),
            "periodo_mes": kwargs.get("periodo_mes"),
            "nivel_atual": kwargs.get("nivel_atual") or "estado",
            "offset": kwargs.get("offset", 0),
            "limite": kwargs.get("limite", 0),
            "total_registros_nivel": 1,
            "possui_mais_registros": False,
            "total_faturamento": Decimal("1000.00"),
            "total_impostos": Decimal("100.00"),
            "total_tributos_reforma": Decimal("25.00"),
            "percentual_impostos_sobre_faturamento": Decimal("10.00"),
            "quantidade_documentos": 2,
            "total_estados": 1,
            "total_cidades": 1,
            "total_ncms": 1,
            "total_produtos": 1,
            "hierarquia": [],
            "itens_nivel_atual": [{"estado": "SP", "faturamento": Decimal("1000.00")}],
            "por_estado": [{"estado": "SP", "faturamento": Decimal("1000.00"), "imposto_valor": Decimal("100.00"), "imposto_percentual": Decimal("10.00")}],
            "por_cidade": [],
            "por_ncm": [],
            "por_produto": [],
        }

    def consultar_dashboard_vendas(self, **kwargs):
        self.calls.append(("consultar_dashboard_vendas", kwargs))
        return {
            "status": "ok",
            "emitente_cnpj": kwargs["emitente_cnpj"],
            "periodo_ano": kwargs.get("periodo_ano") or 2025,
            "periodo_mes": kwargs.get("periodo_mes"),
            "anos_disponiveis": [2025, 2024],
            "resumo_atual": {"total_vendido": Decimal("500.00"), "quantidade_notas": 5},
            "resumo_anterior": {"total_vendido": Decimal("300.00"), "quantidade_notas": 3},
            "serie_mensal": [
                {"periodo_ano": 2025, "periodo_mes": 1, "total_vendido": Decimal("500.00"), "quantidade_notas": 5}
            ],
        }

    def comparar_kpis_mensal(self, **kwargs):
        self.calls.append(("comparar_kpis_mensal", kwargs))
        return {
            "total_vendas": {"atual": Decimal("120.00"), "anterior": Decimal("100.00"), "variacao_percentual": Decimal("20.00")},
            "quantidade_notas": {"atual": 12, "anterior": 10, "variacao_percentual": Decimal("20.00")},
            "ticket_medio": {"atual": Decimal("10.00"), "anterior": Decimal("10.00"), "variacao_percentual": Decimal("0.00")},
            "maior_nota": {"atual": Decimal("50.00"), "anterior": Decimal("40.00"), "variacao_percentual": Decimal("25.00")},
            "menor_nota": {"atual": Decimal("5.00"), "anterior": Decimal("4.00"), "variacao_percentual": Decimal("25.00")},
            "total_icms": {"atual": Decimal("12.00"), "anterior": Decimal("10.00"), "variacao_percentual": Decimal("20.00")},
            "total_ipi": {"atual": Decimal("2.00"), "anterior": Decimal("1.00"), "variacao_percentual": Decimal("100.00")},
            "total_pis": {"atual": Decimal("1.20"), "anterior": Decimal("1.00"), "variacao_percentual": Decimal("20.00")},
            "total_cofins": {"atual": Decimal("5.00"), "anterior": Decimal("4.00"), "variacao_percentual": Decimal("25.00")},
        }

    def obter_periodos_disponiveis(self, emitente_cnpj):
        self.calls.append(("obter_periodos_disponiveis", {"emitente_cnpj": emitente_cnpj}))
        return [(2025, 3), (2025, 2)]

    def obter_ultimo_periodo(self, emitente_cnpj):
        self.calls.append(("obter_ultimo_periodo", {"emitente_cnpj": emitente_cnpj}))
        return 2025, 3


class FakeSpedConsultaService:
    conn_params = {"dbname": "test"}

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def listar_kpis(self, **kwargs):
        self.calls.append(("listar_kpis", kwargs))
        return [
            SimpleNamespace(periodo_ano=2025, periodo_mes=1),
            SimpleNamespace(periodo_ano=2024, periodo_mes=12),
        ]

    def analisar_compras(self, **kwargs):
        self.calls.append(("analisar_compras", kwargs))
        return {
            "emitente_cnpj": kwargs["emitente_cnpj"],
            "periodo_ano": kwargs.get("periodo_ano"),
            "periodo_mes": kwargs.get("periodo_mes"),
            "total_comprado": Decimal("80.00"),
            "top_fornecedores_valor": [],
            "top_fornecedores_quantidade": [],
            "top_produtos_valor": [],
            "top_produtos_quantidade": [],
        }

    def analisar_fiscal_hierarquia(self, **kwargs):
        self.calls.append(("analisar_fiscal_hierarquia", kwargs))
        return {
            "emitente_cnpj": kwargs["emitente_cnpj"],
            "periodo_ano": kwargs.get("periodo_ano"),
            "periodo_mes": kwargs.get("periodo_mes"),
            "nivel_atual": kwargs.get("nivel_atual") or "estado",
            "offset": kwargs.get("offset", 0),
            "limite": kwargs.get("limite", 0),
            "total_registros_nivel": 1,
            "possui_mais_registros": False,
            "total_faturamento": Decimal("900.00"),
            "total_impostos": Decimal("90.00"),
            "total_tributos_reforma": Decimal("10.00"),
            "percentual_impostos_sobre_faturamento": Decimal("10.00"),
            "quantidade_documentos": 3,
            "total_estados": 1,
            "total_cidades": 1,
            "total_ncms": 1,
            "total_produtos": 1,
            "hierarquia": [],
            "itens_nivel_atual": [{"estado": "SP", "faturamento": Decimal("900.00")}],
            "por_estado": [{"estado": "SP", "faturamento": Decimal("900.00"), "imposto_valor": Decimal("90.00"), "imposto_percentual": Decimal("10.00")}],
            "por_cidade": [],
            "por_ncm": [],
            "por_produto": [],
        }

    def consultar_dashboard_vendas(self, **kwargs):
        self.calls.append(("consultar_dashboard_vendas", kwargs))
        return {
            "status": "ok",
            "emitente_cnpj": kwargs["emitente_cnpj"],
            "periodo_ano": kwargs.get("periodo_ano") or 2025,
            "periodo_mes": kwargs.get("periodo_mes"),
            "anos_disponiveis": [2025, 2024],
            "resumo_atual": {"total_vendido": Decimal("300.00")},
            "resumo_anterior": {"total_vendido": Decimal("120.00")},
            "serie_mensal": [],
        }


class FailingNFeConsultaService(FakeNFeConsultaService):
    def analisar_compras(self, **kwargs):
        raise ValueError("periodo invalido")

    def analisar_vendas(self, **kwargs):
        raise RuntimeError("ia indisponivel")

    def analisar_fiscal_cfop(self, **kwargs):
        raise ValueError("cfop invalido")

    def comparar_kpis_mensal(self, **kwargs):
        self.calls.append(("comparar_kpis_mensal", kwargs))
        return None

    def obter_periodos_disponiveis(self, emitente_cnpj):
        raise ValueError("Nenhum processamento encontrado para o emitente.")

    def obter_ultimo_periodo(self, emitente_cnpj):
        raise ValueError("Nenhum processamento encontrado para o emitente.")


class FailingSpedConsultaService(FakeSpedConsultaService):
    def analisar_compras(self, **kwargs):
        raise ValueError("periodo invalido")

    def analisar_vendas(self, **kwargs):
        raise RuntimeError("ia indisponivel")

    def analisar_fiscal_cfop(self, **kwargs):
        raise ValueError("cfop invalido")


def _zero_tax_total(*args, **kwargs):
    return Decimal("0.00")


def _kpi_item(periodo_ano=2025, periodo_mes=1, total_vendas=Decimal("300.00")):
    return SimpleNamespace(
        periodo_ano=periodo_ano,
        periodo_mes=periodo_mes,
        kpis=SimpleNamespace(
            total_vendas=total_vendas,
            quantidade_notas=2,
            total_icms=Decimal("10.00"),
            total_ipi=Decimal("1.00"),
            total_pis=Decimal("2.00"),
            total_cofins=Decimal("3.00"),
            top_clientes=[{"cliente": "Cliente A", "valor_total": total_vendas}],
            top_produtos=[{"produto": "Produto A", "valor_total": total_vendas}],
            top_cidades=[{"cidade": "Cidade A", "valor_total": total_vendas}],
        ),
    )


def test_nfe_dashboard_compras_preserva_contrato_e_serie_mensal(client, monkeypatch):
    service = FakeNFeConsultaService()
    monkeypatch.setattr("app.api.nfe.routes.get_nfe_consulta_service", lambda: service)
    monkeypatch.setattr(
        "app.services.shared.compras_dashboard_service.obter_total_impostos_complementares_documentos",
        _zero_tax_total,
    )
    monkeypatch.setattr(
        "app.services.shared.compras_dashboard_service.obter_total_tributos_reforma_documentos",
        _zero_tax_total,
    )

    response = client.get(f"/api/nfe/analise/compras/dashboard?emitente_cnpj={CNPJ}&periodo_ano=2025&limite=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["emitente_cnpj"] == CNPJ
    assert payload["periodo_ano"] == 2025
    assert payload["anos_disponiveis"] == [2025, 2024]
    assert len(payload["serie_mensal"]) == 12
    assert payload["resumo_atual"]["total_comprado"] == "100.00"
    assert any(call[0] == "analisar_compras" and call[1]["periodo_mes"] == 12 for call in service.calls)


def test_nfe_hierarquia_fiscal_repassa_filtros_e_preserva_shape(client, monkeypatch):
    service = FakeNFeConsultaService()
    monkeypatch.setattr("app.api.nfe.routes.get_nfe_consulta_service", lambda: service)

    response = client.get(
        f"/api/nfe/analise/fiscal/hierarquia?emitente_cnpj={CNPJ}"
        "&periodo_ano=2025&periodo_mes=3&nivel_atual=cidade&estado=SP&limite=20&offset=5"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["nivel_atual"] == "cidade"
    assert payload["offset"] == 5
    assert payload["limite"] == 20
    assert payload["por_estado"][0]["estado"] == "SP"
    _, kwargs = service.calls[-1]
    assert kwargs["estado"] == "SP"
    assert kwargs["periodo_mes"] == 3


def test_nfe_dashboard_vendas_delega_para_service_sem_montagem_na_rota(client, monkeypatch):
    service = FakeNFeConsultaService()
    monkeypatch.setattr("app.api.nfe.routes.get_nfe_consulta_service", lambda: service)

    response = client.get(f"/api/nfe/analise/vendas/dashboard?emitente_cnpj={CNPJ}&periodo_ano=2025")

    assert response.status_code == 200
    payload = response.json()
    assert payload["resumo_atual"]["total_vendido"] == "500.00"
    assert service.calls[-1] == (
        "consultar_dashboard_vendas",
        {"emitente_cnpj": CNPJ, "periodo_ano": 2025, "periodo_mes": None, "limite": 5},
    )


def test_sped_dashboard_compras_preserva_contrato_e_valida_perfil(client, monkeypatch):
    service = FakeSpedConsultaService()
    monkeypatch.setattr("app.api.sped.routes.SpedConsultaService", lambda: service)
    monkeypatch.setattr("app.api.shared.company_validation.CompanyProfileService.empresa_tem_sped", lambda self, cnpj: True)
    monkeypatch.setattr(
        "app.services.shared.compras_dashboard_service.obter_total_impostos_complementares_documentos",
        _zero_tax_total,
    )
    monkeypatch.setattr(
        "app.services.shared.compras_dashboard_service.obter_total_tributos_reforma_documentos",
        _zero_tax_total,
    )

    response = client.get(f"/api/sped/analise/compras/dashboard?emitente_cnpj={CNPJ}&periodo_ano=2025")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["emitente_cnpj"] == CNPJ
    assert len(payload["serie_mensal"]) == 12
    assert payload["resumo_atual"]["total_comprado"] == "80.00"


def test_sped_dashboard_vendas_delega_para_service_sem_montagem_na_rota(client, monkeypatch):
    service = FakeSpedConsultaService()
    monkeypatch.setattr("app.api.sped.routes.SpedConsultaService", lambda: service)
    monkeypatch.setattr("app.api.shared.company_validation.CompanyProfileService.empresa_tem_sped", lambda self, cnpj: True)

    response = client.get(f"/api/sped/analise/vendas/dashboard?emitente_cnpj={CNPJ}&periodo_ano=2025")

    assert response.status_code == 200
    payload = response.json()
    assert payload["resumo_atual"]["total_vendido"] == "300.00"
    assert service.calls[-1] == (
        "consultar_dashboard_vendas",
        {"emitente_cnpj": CNPJ, "periodo_ano": 2025, "periodo_mes": None, "limite": 5},
    )


def test_dashboard_compras_compartilhado_preserva_periodos_e_origem(monkeypatch):
    service = FakeNFeConsultaService()
    chamadas_totais = []

    def fake_total(conn_params, origem_documento, emitente_cnpj, periodo_ano, periodo_mes, tipo_operacao):
        chamadas_totais.append((origem_documento, periodo_ano, periodo_mes, tipo_operacao))
        return Decimal("7.00")

    monkeypatch.setattr(
        "app.services.shared.compras_dashboard_service.obter_total_impostos_complementares_documentos",
        fake_total,
    )
    monkeypatch.setattr(
        "app.services.shared.compras_dashboard_service.obter_total_tributos_reforma_documentos",
        fake_total,
    )

    dashboard = montar_dashboard_compras(
        consulta_service=service,
        emitente_cnpj=CNPJ,
        origem_documento="nfe",
        periodo_ano=2025,
        periodo_mes=None,
        limite=5,
    )

    assert dashboard["periodo_ano"] == 2025
    assert dashboard["resumo_atual"]["total_impostos_complementares"] == Decimal("7.00")
    assert len(dashboard["serie_mensal"]) == 12
    assert ("nfe", 2025, 12, "entrada") in chamadas_totais
    assert ("nfe", 2024, None, "entrada") in chamadas_totais


def test_sped_dashboard_vendas_service_preserva_periodos_e_totais(monkeypatch):
    service = object.__new__(SpedConsultaService)
    service.conn_params = {"dbname": "test"}

    def fake_listar_kpis(**kwargs):
        if kwargs.get("periodo_ano") == 2024:
            return [_kpi_item(periodo_ano=2024, periodo_mes=12, total_vendas=Decimal("120.00"))]
        return [
            _kpi_item(periodo_ano=2025, periodo_mes=1, total_vendas=Decimal("300.00")),
            _kpi_item(periodo_ano=2025, periodo_mes=2, total_vendas=Decimal("400.00")),
        ]

    chamadas_totais = []

    def fake_total(conn_params, origem_documento, emitente_cnpj, periodo_ano, periodo_mes, tipo_operacao):
        chamadas_totais.append((origem_documento, periodo_ano, periodo_mes, tipo_operacao))
        return Decimal("9.00")

    service.listar_kpis = fake_listar_kpis
    monkeypatch.setattr(
        "app.services.sped.sped_consulta_service.obter_total_impostos_complementares_documentos",
        fake_total,
    )
    monkeypatch.setattr(
        "app.services.sped.sped_consulta_service.obter_total_tributos_reforma_documentos",
        fake_total,
    )

    dashboard = service.consultar_dashboard_vendas(
        emitente_cnpj=CNPJ,
        periodo_ano=2025,
        periodo_mes=1,
        limite=5,
    )

    assert dashboard.periodo_ano == 2025
    assert dashboard.periodo_mes == 1
    assert dashboard.resumo_atual.total_vendido == Decimal("300.00")
    assert dashboard.resumo_atual.total_impostos_complementares == Decimal("9.00")
    assert [item.periodo_mes for item in dashboard.serie_mensal] == [1, 2]
    assert ("sped", 2025, 1, "saida") in chamadas_totais
    assert ("sped", 2024, 12, "saida") in chamadas_totais


def test_ia_report_service_injeta_relatorio_por_tipo(monkeypatch):
    monkeypatch.setattr(
        "app.services.shared.ia_report_service.OpenAIReportService",
        lambda: FakeOpenAIReportService(),
    )
    resultado = {}

    injetar_relatorio_ia(resultado, "compras", "executivo", "compacto")

    assert resultado["relatorio_ia"] == "compras:executivo:compacto"


def test_ia_report_service_preserva_503_quando_indisponivel(monkeypatch):
    monkeypatch.setattr(
        "app.services.shared.ia_report_service.OpenAIReportService",
        lambda: FakeOpenAIReportService(disponivel=False),
    )

    try:
        injetar_relatorio_ia({}, "clientes", "analitico")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 503
        assert "OpenAI" in exc.detail
    else:
        raise AssertionError("esperava HTTPException quando OpenAI esta indisponivel")


def test_analise_relatorio_service_executa_analise_sem_relatorio():
    chamadas = []

    def analise_fn(**kwargs):
        chamadas.append(kwargs)
        return {"total": Decimal("10.00")}

    resultado = executar_analise_com_relatorio_ia(
        analise_fn=analise_fn,
        analise_kwargs={"emitente_cnpj": CNPJ},
        gerar_relatorio_ia=False,
        tipo_relatorio="compras",
        formato_relatorio="executivo",
        layout="compacto",
    )

    assert resultado == {"total": Decimal("10.00")}
    assert chamadas == [{"emitente_cnpj": CNPJ}]


def test_analise_relatorio_service_injeta_relatorio_quando_solicitado(monkeypatch):
    monkeypatch.setattr(
        "app.services.shared.ia_report_service.OpenAIReportService",
        lambda: FakeOpenAIReportService(),
    )

    resultado = executar_analise_com_relatorio_ia(
        analise_fn=lambda **kwargs: {"total": Decimal("10.00")},
        analise_kwargs={"emitente_cnpj": CNPJ},
        gerar_relatorio_ia=True,
        tipo_relatorio="vendas",
        formato_relatorio="analitico",
        layout="detalhado",
    )

    assert resultado["relatorio_ia"] == "vendas:analitico:detalhado"


def test_company_validation_preserva_regras_xml_e_sped(monkeypatch):
    monkeypatch.setattr(
        "app.api.shared.company_validation.CompanyProfileService",
        FakeCompanyProfileService,
    )
    validar_empresa_xml(CNPJ)

    try:
        validar_empresa_sped(CNPJ)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
        assert "SPED" in exc.detail
    else:
        raise AssertionError("esperava HTTPException para empresa sem perfil SPED")

    monkeypatch.setattr(
        "app.api.shared.company_validation.CompanyProfileService",
        FakeSpedCompanyProfileService,
    )
    validar_empresa_sped(CNPJ)

    try:
        validar_empresa_xml(CNPJ)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
        assert "XML" in exc.detail
    else:
        raise AssertionError("esperava HTTPException para empresa SPED em rota XML")


def test_sped_hierarquia_fiscal_repassa_filtros_e_preserva_shape(client, monkeypatch):
    service = FakeSpedConsultaService()
    monkeypatch.setattr("app.api.sped.routes.SpedConsultaService", lambda: service)
    monkeypatch.setattr("app.api.shared.company_validation.CompanyProfileService.empresa_tem_sped", lambda self, cnpj: True)

    response = client.get(
        f"/api/sped/analise/fiscal/hierarquia?emitente_cnpj={CNPJ}"
        "&periodo_ano=2025&periodo_mes=3&nivel_atual=estado&limite=15&offset=0"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["quantidade_documentos"] == 3
    assert payload["por_estado"][0]["faturamento"] == "900.00"
    _, kwargs = service.calls[-1]
    assert kwargs["emitente_cnpj"] == CNPJ
    assert kwargs["limite"] == 15


def test_nfe_rotas_analiticas_preservam_value_error_como_400(client, monkeypatch):
    service = FailingNFeConsultaService()
    monkeypatch.setattr("app.api.nfe.routes.get_nfe_consulta_service", lambda: service)

    compras = client.get(f"/api/nfe/analise/compras?emitente_cnpj={CNPJ}&periodo_ano=2025")
    cfop = client.get(f"/api/nfe/analise/fiscal/cfop?emitente_cnpj={CNPJ}&periodo_ano=2025")

    assert compras.status_code == 400
    assert compras.json()["detail"] == "periodo invalido"
    assert cfop.status_code == 400
    assert cfop.json()["detail"] == "cfop invalido"


def test_nfe_rota_analise_vendas_preserva_exception_como_502(client, monkeypatch):
    service = FailingNFeConsultaService()
    monkeypatch.setattr("app.api.nfe.routes.get_nfe_consulta_service", lambda: service)

    response = client.get(f"/api/nfe/analise/vendas?emitente_cnpj={CNPJ}&periodo_ano=2025")

    assert response.status_code == 502
    assert "Falha ao gerar" in response.json()["detail"]


def test_sped_rotas_analiticas_preservam_value_error_como_400(client, monkeypatch):
    service = FailingSpedConsultaService()
    monkeypatch.setattr("app.api.sped.routes.SpedConsultaService", lambda: service)
    monkeypatch.setattr("app.api.shared.company_validation.CompanyProfileService.empresa_tem_sped", lambda self, cnpj: True)

    compras = client.get(f"/api/sped/analise/compras?emitente_cnpj={CNPJ}&periodo_ano=2025")
    cfop = client.get(f"/api/sped/analise/fiscal/cfop?emitente_cnpj={CNPJ}&periodo_ano=2025")

    assert compras.status_code == 400
    assert compras.json()["detail"] == "periodo invalido"
    assert cfop.status_code == 400
    assert cfop.json()["detail"] == "cfop invalido"


def test_sped_rota_analise_vendas_preserva_exception_como_502(client, monkeypatch):
    service = FailingSpedConsultaService()
    monkeypatch.setattr("app.api.sped.routes.SpedConsultaService", lambda: service)
    monkeypatch.setattr("app.api.shared.company_validation.CompanyProfileService.empresa_tem_sped", lambda self, cnpj: True)

    response = client.get(f"/api/sped/analise/vendas?emitente_cnpj={CNPJ}&periodo_ano=2025")

    assert response.status_code == 502
    assert "Falha ao gerar" in response.json()["detail"]


def test_nfe_kpis_comparativo_calcula_periodo_anterior_default(client, monkeypatch):
    service = FakeNFeConsultaService()
    monkeypatch.setattr("app.api.nfe.routes.get_nfe_consulta_service", lambda: service)

    response = client.get(f"/api/nfe/kpis/comparativo?emitente_cnpj={CNPJ}&periodo_ano=2025&periodo_mes=3")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["periodo_atual_ano"] == 2025
    assert payload["periodo_atual_mes"] == 3
    assert payload["periodo_anterior_ano"] == 2025
    assert payload["periodo_anterior_mes"] == 2
    assert payload["kpis"]["total_vendas"]["atual"] == "120.00"
    _, kwargs = service.calls[-1]
    assert kwargs["periodo_anterior_ano"] == 2025
    assert kwargs["periodo_anterior_mes"] == 2


def test_nfe_kpis_comparativo_janeiro_usa_dezembro_ano_anterior(client, monkeypatch):
    service = FakeNFeConsultaService()
    monkeypatch.setattr("app.api.nfe.routes.get_nfe_consulta_service", lambda: service)

    response = client.get(f"/api/nfe/kpis/comparativo?emitente_cnpj={CNPJ}&periodo_ano=2025&periodo_mes=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["periodo_anterior_ano"] == 2024
    assert payload["periodo_anterior_mes"] == 12


def test_nfe_kpis_comparativo_retorna_404_quando_service_sem_kpis(client, monkeypatch):
    service = FailingNFeConsultaService()
    monkeypatch.setattr("app.api.nfe.routes.get_nfe_consulta_service", lambda: service)

    response = client.get(f"/api/nfe/kpis/comparativo?emitente_cnpj={CNPJ}&periodo_ano=2025&periodo_mes=3")

    assert response.status_code == 404
    assert "KPIs" in response.json()["detail"]


def test_nfe_kpis_comparativo_atual_usa_periodos_disponiveis(client, monkeypatch):
    service = FakeNFeConsultaService()
    monkeypatch.setattr("app.api.nfe.routes.get_nfe_consulta_service", lambda: service)

    response = client.get(f"/api/nfe/kpis/comparativo/atual?emitente_cnpj={CNPJ}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["periodo_atual_ano"] == 2025
    assert payload["periodo_atual_mes"] == 3
    assert payload["periodo_anterior_ano"] == 2025
    assert payload["periodo_anterior_mes"] == 2


def test_nfe_kpis_comparativo_atual_sem_periodo_retorna_404(client, monkeypatch):
    service = FailingNFeConsultaService()
    monkeypatch.setattr("app.api.nfe.routes.get_nfe_consulta_service", lambda: service)

    response = client.get(f"/api/nfe/kpis/comparativo/atual?emitente_cnpj={CNPJ}")

    assert response.status_code == 404
    assert "processamento" in response.json()["detail"]


def _nota_detalhada(numero_nf: int, item_id: int, cfop: str = "5102") -> NotaExtraida:
    item = ItemNota(
        numero_item=1,
        codigo_produto=f"P{item_id}",
        descricao="Produto Teste",
        ncm="12345678",
        cfop=cfop,
        unidade="UN",
        quantidade=Decimal("2"),
        valor_unitario=Decimal("10.00"),
        valor_total=Decimal("20.00"),
        id=item_id,
    )
    return NotaExtraida(
        chave=f"chave-{numero_nf}",
        numero_nf=numero_nf,
        emitente_cnpj=CNPJ,
        modelo="55",
        data_emissao=date(2025, 3, numero_nf),
        natureza_operacao="Venda",
        destinatario_documento="99999999000199",
        destinatario_nome="Cliente Teste",
        destinatario_cidade="Sao Paulo",
        destinatario_uf="SP",
        valor_total_nf=Decimal("20.00"),
        valor_icms=Decimal("2.00"),
        valor_ipi=Decimal("0.00"),
        valor_pis=Decimal("0.33"),
        valor_cofins=Decimal("1.52"),
        valor_produtos=Decimal("20.00"),
        valor_desconto=Decimal("0.00"),
        valor_frete=Decimal("0.00"),
        itens=[item],
        id=numero_nf,
    )


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class FakeNFeNotasService:
    conn_params = {"dbname": "test"}

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def listar_notas_periodo_para_operacao(self, **kwargs):
        self.calls.append(("listar_notas_periodo_para_operacao", kwargs))
        return [_nota_detalhada(1, 101, "5102"), _nota_detalhada(2, 102, "1102")]

    def listar_tributos_itens(self, conn, item_ids):
        self.calls.append(("listar_tributos_itens", {"item_ids": item_ids}))
        return {
            102: [
                {
                    "tributo_codigo": "ICMS",
                    "tributo_nome": "ICMS",
                    "base_calculo": Decimal("20.00"),
                    "aliquota": Decimal("10.00"),
                    "valor_debito": Decimal("2.00"),
                    "valor_credito": Decimal("0.00"),
                    "valor_tributo": Decimal("2.00"),
                    "natureza": "debito",
                    "origem": "nfe",
                    "status": "ativo",
                }
            ]
        }


class FakeNFeNotasRepository:
    instances: list["FakeNFeNotasRepository"] = []

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.__class__.instances.append(self)

    def listar_notas_detalhadas(self, **kwargs):
        self.calls.append(("listar_notas_detalhadas", kwargs))
        notas = [_nota_detalhada(1, 101, "5102"), _nota_detalhada(2, 102, "1102")]
        notas_slice = notas[kwargs["offset"] : kwargs["offset"] + kwargs["limite"]]
        return (
            len(notas),
            notas_slice,
            {
                102: [
                    {
                        "tributo_codigo": "ICMS",
                        "tributo_nome": "ICMS",
                        "base_calculo": Decimal("20.00"),
                        "aliquota": Decimal("10.00"),
                        "valor_debito": Decimal("2.00"),
                        "valor_credito": Decimal("0.00"),
                        "valor_tributo": Decimal("2.00"),
                        "natureza": "debito",
                        "origem": "nfe",
                        "status": "ativo",
                    }
                ]
            },
        )


class FakeNCMCatalogService:
    def obter_descricao(self, ncm):
        return f"Descricao {ncm}"


class FakeCompanyProfileService:
    def empresa_tem_sped(self, cnpj):
        return False


class FakeSpedCompanyProfileService:
    def empresa_tem_sped(self, cnpj):
        return True


class FakeOpenAIReportService:
    def __init__(self, disponivel=True):
        self._disponivel = disponivel

    def disponivel(self):
        return self._disponivel

    def gerar_relatorio_compras(self, resultado, formato_relatorio, layout):
        return f"compras:{formato_relatorio}:{layout}"

    def gerar_relatorio_vendas(self, resultado, formato_relatorio, layout):
        return f"vendas:{formato_relatorio}:{layout}"

    def gerar_relatorio_clientes(self, resultado, formato_relatorio):
        return f"clientes:{formato_relatorio}"


def test_nfe_notas_nao_implementado_preserva_501(client):
    response = client.get(f"/api/nfe/notas?emitente_cnpj={CNPJ}")

    assert response.status_code == 501
    assert "não implementada" in response.json()["detail"] or "implementada" in response.json()["detail"]


def test_nfe_notas_detalhado_preserva_periodo_default_paginacao_e_tributos(client, monkeypatch):
    consulta_service = FakeNFeConsultaService()
    FakeNFeNotasRepository.instances = []
    monkeypatch.setattr("app.api.nfe.routes.get_nfe_consulta_service", lambda: consulta_service)
    monkeypatch.setattr("app.api.shared.company_validation.CompanyProfileService", FakeCompanyProfileService)
    monkeypatch.setattr("app.api.nfe.routes.NFeNotasRepository", FakeNFeNotasRepository)
    monkeypatch.setattr("app.api.nfe.routes.NCMCatalogService", FakeNCMCatalogService)

    response = client.get(f"/api/nfe/notas/detalhado?emitente_cnpj={CNPJ}&limite=1&offset=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["total"] == 2
    assert len(payload["notas"]) == 1
    assert payload["notas"][0]["numero_nf"] == "2"
    assert payload["notas"][0]["itens"][0]["descricao_ncm"] == "Descricao 12345678"
    assert payload["notas"][0]["itens"][0]["tributos"][0]["tributo_codigo"] == "ICMS"
    assert consulta_service.calls[0] == ("obter_ultimo_periodo", {"emitente_cnpj": CNPJ})
    notas_repository = FakeNFeNotasRepository.instances[0]
    assert notas_repository.calls[0][1]["periodo_ano"] == 2025
    assert notas_repository.calls[0][1]["periodo_mes"] == 3
    assert notas_repository.calls[0][1]["tipo_operacao"] == "todas"
    assert notas_repository.calls[0][1]["limite"] == 1
    assert notas_repository.calls[0][1]["offset"] == 1


def test_nfe_notas_detalhado_com_mes_sem_ano_resolve_ano_do_ultimo_periodo(client, monkeypatch):
    consulta_service = FakeNFeConsultaService()
    FakeNFeNotasRepository.instances = []
    monkeypatch.setattr("app.api.nfe.routes.get_nfe_consulta_service", lambda: consulta_service)
    monkeypatch.setattr("app.api.shared.company_validation.CompanyProfileService", FakeCompanyProfileService)
    monkeypatch.setattr("app.api.nfe.routes.NFeNotasRepository", FakeNFeNotasRepository)
    monkeypatch.setattr("app.api.nfe.routes.NCMCatalogService", FakeNCMCatalogService)

    response = client.get(f"/api/nfe/notas/detalhado?emitente_cnpj={CNPJ}&periodo_mes=2&tipo_operacao=vendas")

    assert response.status_code == 200
    notas_repository = FakeNFeNotasRepository.instances[0]
    assert notas_repository.calls[0][1]["periodo_ano"] == 2025
    assert notas_repository.calls[0][1]["periodo_mes"] == 2
    assert notas_repository.calls[0][1]["tipo_operacao"] == "vendas"


def test_nfe_notas_detalhado_sem_periodo_retorna_404_quando_nao_ha_ultimo_periodo(client, monkeypatch):
    service = FailingNFeConsultaService()
    monkeypatch.setattr("app.api.nfe.routes.get_nfe_consulta_service", lambda: service)

    response = client.get(f"/api/nfe/notas/detalhado?emitente_cnpj={CNPJ}")

    assert response.status_code == 404
    assert "processamento" in response.json()["detail"]


def test_nfe_notas_detalhado_erro_banco_retorna_503(client, monkeypatch):
    consulta_service = FakeNFeConsultaService()
    monkeypatch.setattr("app.api.nfe.routes.get_nfe_consulta_service", lambda: consulta_service)
    monkeypatch.setattr("app.api.shared.company_validation.CompanyProfileService", FakeCompanyProfileService)

    class FailingNFeNotasRepository:
        def listar_notas_detalhadas(self, **kwargs):
            raise psycopg.OperationalError("database down")

    monkeypatch.setattr("app.api.nfe.routes.NFeNotasRepository", FailingNFeNotasRepository)

    response = client.get(f"/api/nfe/notas/detalhado?emitente_cnpj={CNPJ}&periodo_ano=2025&periodo_mes=3")

    assert response.status_code == 503
    assert "consultar as notas" in response.json()["detail"]


def test_nfe_notas_repository_preserva_paginacao_e_busca_tributos(monkeypatch):
    notas_service = FakeNFeNotasService()
    monkeypatch.setattr("app.repositories.nfe.notas_repository.psycopg.connect", lambda **kwargs: FakeConnection())

    total, notas_slice, tributos_por_item = NFeNotasRepository(
        notas_service=notas_service
    ).listar_notas_detalhadas(
        cnpj_empresa=CNPJ,
        periodo_ano=2025,
        periodo_mes=3,
        tipo_operacao="vendas",
        limite=1,
        offset=1,
    )

    assert total == 2
    assert [nota.numero_nf for nota in notas_slice] == [2]
    assert tributos_por_item[102][0]["tributo_codigo"] == "ICMS"
    assert notas_service.calls[0][1]["periodo_ano"] == 2025
    assert notas_service.calls[0][1]["periodo_mes"] == 3
    assert notas_service.calls[0][1]["tipo_operacao"] == "vendas"
    assert notas_service.calls[1][1]["item_ids"] == [102]
