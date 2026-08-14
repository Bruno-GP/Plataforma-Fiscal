from datetime import date, datetime
from decimal import Decimal

from app.api.metas import indicadores_routes, routes as metas_routes
from app.services.metas.metas_service import IndicadorInvalidoError, MetaNaoEncontradaError


class FakeIndicadoresRepository:
    def obter_por_id(self, indicador_id):
        return {"id": indicador_id, "chave": "faturamento", "direcao_boa": "maior_melhor", "ativo": True, "perfil": "xml"}

    def listar(self, perfil="xml"):
        return [
            {
                "id": 1,
                "chave": "faturamento",
                "nome": "Faturamento",
                "unidade": "moeda",
                "direcao_boa": "maior_melhor",
                "perfil": "xml",
            }
        ]

    def historico(self, empresa_id, indicador_id, meses=12):
        return [{"periodo": date(2026, 7, 1), "valor": Decimal("1000.00")}]


class FakeMetasService:
    def __init__(self):
        self.metas = {}
        self._next_id = 1
        self.indicadores_repository = FakeIndicadoresRepository()

    def criar(self, **campos):
        meta_id = self._next_id
        self._next_id += 1
        if campos["indicador_id"] != 1:
            raise IndicadorInvalidoError("indicador invalido")
        meta = {
            "id": meta_id,
            "criado_em": datetime(2026, 8, 13),
            "atualizado_em": datetime(2026, 8, 13),
            "status": "ativa",
            **campos,
        }
        self.metas[meta_id] = meta
        return meta

    def obter(self, meta_id, empresa_id):
        meta = self.metas.get(meta_id)
        if not meta or meta["empresa_id"] != empresa_id:
            raise MetaNaoEncontradaError("nao encontrada")
        return meta

    def listar(self, empresa_id, status=None, indicador_id=None):
        return [m for m in self.metas.values() if m["empresa_id"] == empresa_id]

    def atualizar(self, meta_id, empresa_id, campos):
        meta = self.obter(meta_id, empresa_id)
        meta.update(campos)
        return meta

    def cancelar(self, meta_id, empresa_id):
        meta = self.obter(meta_id, empresa_id)
        meta["status"] = "cancelada"

    def analisar(self, meta_id, empresa_id, *, valor_realizado_atual, data_referencia=None):
        from app.services.metas.analise_meta_service import AnaliseMeta, StatusRitmo, Tendencia

        meta = self.obter(meta_id, empresa_id)
        return AnaliseMeta(
            valor_alvo=meta["valor_alvo"],
            valor_realizado_atual=valor_realizado_atual,
            percentual_atingido=Decimal("62.00"),
            tempo_decorrido_pct=Decimal("70.00"),
            status_ritmo=StatusRitmo.EM_RISCO,
            tendencia=Tendencia.QUEDA_LEVE,
            media_periodos_anteriores=Decimal("33500.00"),
            mediana_periodos_anteriores=Decimal("33000.00"),
            desvio_padrao_periodos_anteriores=Decimal("1000.00"),
            variacao_vs_media_pct=Decimal("-7.50"),
            projecao_fim_periodo=Decimal("43500.00"),
            diagnostico="Voce esta 7.5% abaixo da media dos periodos anteriores.",
            serie_historica=[],
            comparativo_ano_anterior_pct=None,
        )


def _payload_meta_valida():
    return {
        "indicador_id": 1,
        "titulo": "Crescer faturamento",
        "valor_alvo": "50000.00",
        "tipo_meta": "crescimento",
        "periodo_tipo": "mensal",
        "periodo_inicio": "2026-08-01",
        "periodo_fim": "2026-08-31",
    }


def test_criar_meta(client):
    fake_service = FakeMetasService()
    client.app.dependency_overrides[metas_routes.get_metas_service] = lambda: fake_service

    response = client.post("/api/metas", json=_payload_meta_valida())

    assert response.status_code == 201
    assert response.json()["indicador_id"] == 1


def test_criar_meta_com_indicador_invalido_retorna_400(client):
    fake_service = FakeMetasService()
    client.app.dependency_overrides[metas_routes.get_metas_service] = lambda: fake_service

    payload = _payload_meta_valida()
    payload["indicador_id"] = 999
    response = client.post("/api/metas", json=payload)

    assert response.status_code == 400


def test_criar_meta_com_periodo_invalido_retorna_422(client):
    payload = _payload_meta_valida()
    payload["periodo_inicio"] = "2026-08-31"
    payload["periodo_fim"] = "2026-08-01"

    response = client.post("/api/metas", json=payload)

    assert response.status_code == 422


def test_obter_meta_de_outra_empresa_retorna_404(client):
    fake_service = FakeMetasService()
    fake_service.metas[1] = {
        "id": 1,
        "empresa_id": 999,
        "indicador_id": 1,
        "titulo": "Outra empresa",
        "descricao": None,
        "valor_alvo": Decimal("100.00"),
        "tipo_meta": "crescimento",
        "periodo_tipo": "mensal",
        "periodo_inicio": date(2026, 8, 1),
        "periodo_fim": date(2026, 8, 31),
        "status": "ativa",
        "criado_em": datetime(2026, 8, 13),
        "atualizado_em": datetime(2026, 8, 13),
    }
    client.app.dependency_overrides[metas_routes.get_metas_service] = lambda: fake_service

    response = client.get("/api/metas/1")

    assert response.status_code == 404


def test_analise_meta(client, monkeypatch):
    fake_service = FakeMetasService()
    fake_service.metas[1] = fake_service.criar(
        empresa_id=1,
        indicador_id=1,
        titulo="Crescer",
        descricao=None,
        valor_alvo=Decimal("50000.00"),
        tipo_meta="crescimento",
        periodo_tipo="mensal",
        periodo_inicio=date(2026, 8, 1),
        periodo_fim=date(2026, 8, 31),
        criado_por=1,
    )
    client.app.dependency_overrides[metas_routes.get_metas_service] = lambda: fake_service
    monkeypatch.setattr(
        metas_routes.MetasHistoricoRepository,
        "agregar_por_empresa",
        lambda self, cnpj: [{"periodo_referencia": date(2026, 8, 1), "faturamento": Decimal("31000.00")}],
    )

    response = client.get("/api/metas/1/analise")

    assert response.status_code == 200
    assert response.json()["status_ritmo"] == "em_risco"


def test_listar_indicadores(client):
    client.app.dependency_overrides[indicadores_routes.get_indicadores_repository] = lambda: FakeIndicadoresRepository()

    response = client.get("/api/indicadores")

    assert response.status_code == 200
    assert response.json()["resultados"][0]["chave"] == "faturamento"


def test_historico_indicador(client):
    client.app.dependency_overrides[indicadores_routes.get_indicadores_repository] = lambda: FakeIndicadoresRepository()

    response = client.get("/api/indicadores/1/historico")

    assert response.status_code == 200
    assert response.json()["resultados"][0]["valor"] == "1000.00"
