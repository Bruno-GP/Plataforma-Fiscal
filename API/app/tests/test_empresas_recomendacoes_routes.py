from decimal import Decimal

from app.api.empresas import recomendacoes_routes
from app.services.metas.indicador_recommendation_service import (
    EmpresaNaoEncontradaError,
    IndicadorRecomendado,
    IndicadorRecommendationResult,
)


class FakeIndicadorRecommendationService:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.calls = []

    def recomendar_para_empresa(self, empresa_id, perfil="xml"):
        self.calls.append({"empresa_id": empresa_id, "perfil": perfil})
        if self.should_fail:
            raise EmpresaNaoEncontradaError("nao encontrada")

        return IndicadorRecommendationResult(
            empresa_id=empresa_id,
            cnae_fiscal="4711302",
            cnae_fiscal_descricao="Comercio varejista de mercadorias em geral",
            segmento_sugerido="comercio_varejista",
            segmento_nome="Comercio varejista",
            fonte="cnae",
            confianca=0.8,
            motivo="CNAE 4711302 mapeado pelo prefixo 47.",
            indicadores=[
                IndicadorRecomendado(
                    indicador_id=1,
                    chave="faturamento",
                    nome="Faturamento",
                    unidade="moeda",
                    direcao_boa="maior_melhor",
                    perfil="xml",
                    prioridade=10,
                    status="sugerido",
                    motivo="Indicador base para acompanhar volume de vendas.",
                    obrigatorio=True,
                    score=Decimal("90"),
                )
            ],
        )


def test_listar_recomendacoes_indicadores_da_empresa_logada(client):
    fake_service = FakeIndicadorRecommendationService()
    client.app.dependency_overrides[
        recomendacoes_routes.get_indicador_recommendation_service
    ] = lambda: fake_service

    response = client.get("/api/empresas/me/recomendacoes-indicadores")

    assert response.status_code == 200
    payload = response.json()
    assert payload["empresa_id"] == 1
    assert payload["segmento_sugerido"] == "comercio_varejista"
    assert payload["fonte"] == "cnae"
    assert payload["indicadores"][0]["chave"] == "faturamento"
    assert payload["indicadores"][0]["score"] == "90"
    assert fake_service.calls == [{"empresa_id": 1, "perfil": "xml"}]


def test_listar_recomendacoes_indicadores_repassa_perfil(client):
    fake_service = FakeIndicadorRecommendationService()
    client.app.dependency_overrides[
        recomendacoes_routes.get_indicador_recommendation_service
    ] = lambda: fake_service

    response = client.get("/api/empresas/me/recomendacoes-indicadores?perfil=sped")

    assert response.status_code == 200
    assert fake_service.calls == [{"empresa_id": 1, "perfil": "sped"}]


def test_listar_recomendacoes_indicadores_empresa_inexistente_retorna_404(client):
    client.app.dependency_overrides[
        recomendacoes_routes.get_indicador_recommendation_service
    ] = lambda: FakeIndicadorRecommendationService(should_fail=True)

    response = client.get("/api/empresas/me/recomendacoes-indicadores")

    assert response.status_code == 404
    assert response.json()["detail"] == "Empresa da sessao atual nao encontrada."
