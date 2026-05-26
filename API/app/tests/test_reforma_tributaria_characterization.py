from datetime import datetime, timezone
from decimal import Decimal


CNPJ = "12345678000190"


class FakeReformaConsultaService:
    instances = []

    def __init__(self):
        self.calls = []
        self.__class__.instances.append(self)

    def listar_tributos(self, incluir_inativos=False):
        self.calls.append(("listar_tributos", {"incluir_inativos": incluir_inativos}))
        return [
            {
                "id": 1,
                "codigo": "ICMS",
                "nome": "ICMS",
                "esfera": "estadual",
                "tipo": "legado",
                "descricao": "Imposto estadual",
                "ativo": True,
            }
        ]

    def listar_apuracoes(self, **kwargs):
        self.calls.append(("listar_apuracoes", kwargs))
        return [
            {
                "id": 10,
                "empresa_cnpj": kwargs["emitente_cnpj"],
                "periodo_ano": kwargs["periodo_ano"],
                "periodo_mes": kwargs["periodo_mes"],
                "tributo_codigo": "ICMS",
                "tributo_nome": "ICMS",
                "total_debitos": Decimal("100.00"),
                "total_creditos": Decimal("40.00"),
                "saldo_apurado": Decimal("60.00"),
                "saldo_a_recolher": Decimal("60.00"),
                "status": "aberta",
            }
        ]

    def listar_documento_tributos(self, **kwargs):
        self.calls.append(("listar_documento_tributos", kwargs))
        return [
            {
                "id": 20,
                "nota_id": kwargs["documento_id"],
                "tributo_codigo": "ICMS",
                "tributo_nome": "ICMS",
                "empresa_cnpj": kwargs["emitente_cnpj"],
                "periodo_ano": 2025,
                "periodo_mes": 3,
                "base_calculo": Decimal("100.00"),
                "valor_debito": Decimal("12.00"),
                "valor_credito": Decimal("0.00"),
                "valor_tributo": Decimal("12.00"),
                "natureza": "debito",
                "origem": "nfe",
                "status": "ativo",
            }
        ]

    def listar_item_tributos(self, **kwargs):
        self.calls.append(("listar_item_tributos", kwargs))
        return [
            {
                "id": 30,
                "nota_item_id": kwargs["item_id"],
                "tributo_codigo": "ICMS",
                "tributo_nome": "ICMS",
                "empresa_cnpj": kwargs["emitente_cnpj"],
                "periodo_ano": 2025,
                "periodo_mes": 3,
                "numero_item": 1,
                "base_calculo": Decimal("50.00"),
                "valor_debito": Decimal("6.00"),
                "valor_credito": Decimal("0.00"),
                "valor_tributo": Decimal("6.00"),
                "natureza": "debito",
                "origem": "nfe",
                "status": "ativo",
            }
        ]

    def listar_memoria_calculo(self, **kwargs):
        self.calls.append(("listar_memoria_calculo", kwargs))
        return [
            {
                "id": 40,
                "tributo_codigo": "ICMS",
                "tributo_nome": "ICMS",
                "empresa_cnpj": kwargs["emitente_cnpj"],
                "periodo_ano": kwargs["periodo_ano"],
                "periodo_mes": kwargs["periodo_mes"],
                "etapa_calculo": "rateio_documento",
                "base_calculo": Decimal("100.00"),
                "valor_calculado": Decimal("12.00"),
                "fonte_dados": "nfe",
                "criado_em": datetime.now(timezone.utc),
            }
        ]

    def contar_memoria_calculo(self, **kwargs):
        self.calls.append(("contar_memoria_calculo", kwargs))
        return 1


class FakeConnection:
    committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def commit(self):
        self.committed = True


class FakeSyncService:
    calls = []

    def sincronizar_nfe_todos_periodos(self, conn, emitente_cnpj):
        self.calls.append(("nfe", emitente_cnpj))
        return [{"origem": "nfe", "periodo_ano": 2025, "periodo_mes": 3, "documentos": 2}]

    def sincronizar_sped_todos_periodos(self, conn, emitente_cnpj):
        self.calls.append(("sped", emitente_cnpj))
        return [{"origem": "sped", "periodo_ano": 2025, "periodo_mes": 3, "documentos": 1}]


def test_reforma_tributaria_lista_tributos_preserva_contrato(client, monkeypatch):
    FakeReformaConsultaService.instances = []
    monkeypatch.setattr(
        "app.api.reforma_tributaria.routes.ReformaTributariaConsultaService",
        FakeReformaConsultaService,
    )

    response = client.get("/api/reforma-tributaria/tributos?incluir_inativos=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["total"] == 1
    assert payload["resultados"][0]["codigo"] == "ICMS"
    assert FakeReformaConsultaService.instances[-1].calls[-1] == (
        "listar_tributos",
        {"incluir_inativos": True},
    )


def test_reforma_tributaria_apuracao_repassa_filtros(client, monkeypatch):
    FakeReformaConsultaService.instances = []
    monkeypatch.setattr(
        "app.api.reforma_tributaria.routes.ReformaTributariaConsultaService",
        FakeReformaConsultaService,
    )

    response = client.get(
        f"/api/reforma-tributaria/apuracao?emitente_cnpj={CNPJ}"
        "&periodo_ano=2025&periodo_mes=3&tributo_codigo=ICMS"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["emitente_cnpj"] == CNPJ
    assert payload["resultados"][0]["saldo_apurado"] == "60.00"
    _, kwargs = FakeReformaConsultaService.instances[-1].calls[-1]
    assert kwargs == {
        "emitente_cnpj": CNPJ,
        "periodo_ano": 2025,
        "periodo_mes": 3,
        "tributo_codigo": "ICMS",
    }


def test_reforma_tributaria_documento_e_item_usam_origem_no_path(client, monkeypatch):
    FakeReformaConsultaService.instances = []
    monkeypatch.setattr(
        "app.api.reforma_tributaria.routes.ReformaTributariaConsultaService",
        FakeReformaConsultaService,
    )

    documento = client.get(f"/api/reforma-tributaria/documentos/nfe/123/tributos?emitente_cnpj={CNPJ}")
    item = client.get(f"/api/reforma-tributaria/itens/nfe/456/tributos?emitente_cnpj={CNPJ}")

    assert documento.status_code == 200
    assert documento.json()["origem_documento"] == "nfe"
    assert documento.json()["documento_id"] == 123
    assert item.status_code == 200
    assert item.json()["origem_item"] == "nfe"
    assert item.json()["item_id"] == 456


def test_reforma_tributaria_memoria_preserva_paginacao_e_total(client, monkeypatch):
    FakeReformaConsultaService.instances = []
    monkeypatch.setattr(
        "app.api.reforma_tributaria.routes.ReformaTributariaConsultaService",
        FakeReformaConsultaService,
    )

    response = client.get(
        f"/api/reforma-tributaria/memoria-calculo?emitente_cnpj={CNPJ}"
        "&periodo_ano=2025&periodo_mes=3&limite=25&offset=50"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["limite"] == 25
    assert payload["offset"] == 50
    assert payload["resultados"][0]["etapa_calculo"] == "rateio_documento"


def test_reforma_tributaria_backfill_preserva_origem_e_commit(client, monkeypatch):
    connection = FakeConnection()
    FakeSyncService.calls = []
    monkeypatch.setattr(
        "app.api.reforma_tributaria.routes.carregar_config_postgres",
        lambda: {"host": "localhost", "port": 5432, "database": "test", "user": "u", "password": "p"},
    )
    monkeypatch.setattr("app.api.reforma_tributaria.routes.psycopg.connect", lambda **kwargs: connection)
    monkeypatch.setattr(
        "app.api.reforma_tributaria.routes.ReformaTributariaSyncService",
        FakeSyncService,
    )

    response = client.post(f"/api/reforma-tributaria/backfill?emitente_cnpj={CNPJ}&origem=sped")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["origem"] == "sped"
    assert payload["periodos_processados"] == 1
    assert connection.committed is True
    assert FakeSyncService.calls == [("sped", CNPJ)]
