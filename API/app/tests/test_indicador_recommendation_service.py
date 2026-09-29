from decimal import Decimal

import pytest

from app.services.metas.indicador_recommendation_service import (
    EmpresaNaoEncontradaError,
    IndicadorRecommendationService,
)


class FakeIndicadorRecomendacoesRepository:
    def __init__(self, empresas=None, recomendacoes=None):
        self.empresas = empresas or {}
        self.recomendacoes = recomendacoes or {}
        self.calls = []

    def obter_empresa_cnae(self, empresa_id):
        self.calls.append(("obter_empresa_cnae", empresa_id))
        return self.empresas.get(empresa_id)

    def listar_por_segmento(self, *, empresa_id, segmento_chave, perfil="xml"):
        self.calls.append(
            (
                "listar_por_segmento",
                {
                    "empresa_id": empresa_id,
                    "segmento_chave": segmento_chave,
                    "perfil": perfil,
                },
            )
        )
        return self.recomendacoes.get((segmento_chave, perfil), [])


def _recomendacao(
    indicador_id=1,
    chave="faturamento",
    nome="Faturamento",
    prioridade=10,
    status="sugerido",
    score=90,
    obrigatorio=True,
):
    return {
        "indicador_id": indicador_id,
        "chave": chave,
        "nome": nome,
        "unidade": "moeda",
        "direcao_boa": "maior_melhor",
        "perfil": "xml",
        "prioridade": prioridade,
        "status": status,
        "score": score,
        "motivo": "Indicador base para acompanhar volume de vendas.",
        "obrigatorio": obrigatorio,
    }


def test_recomendar_para_empresa_classifica_cnae_e_retorna_indicadores():
    repository = FakeIndicadorRecomendacoesRepository(
        empresas={
            1: {
                "id": 1,
                "cnpj": "12345678000190",
                "cnae_fiscal": "47.11-3/02",
                "cnae_fiscal_descricao": "Comercio varejista de mercadorias em geral",
            }
        },
        recomendacoes={
            (
                "comercio_varejista",
                "xml",
            ): [
                _recomendacao(),
                _recomendacao(
                    indicador_id=2,
                    chave="ticket_medio",
                    nome="Ticket medio",
                    prioridade=20,
                    status="aceito",
                    score=75,
                    obrigatorio=False,
                ),
            ]
        },
    )
    service = IndicadorRecommendationService(repository=repository)

    resultado = service.recomendar_para_empresa(empresa_id=1, perfil="xml")

    assert resultado.empresa_id == 1
    assert resultado.cnae_fiscal == "4711302"
    assert resultado.segmento_sugerido == "comercio_varejista"
    assert resultado.segmento_nome == "Comercio varejista"
    assert resultado.fonte == "cnae"
    assert resultado.confianca == 0.8
    assert [indicador.chave for indicador in resultado.indicadores] == ["faturamento", "ticket_medio"]
    assert resultado.indicadores[0].score == Decimal("90")
    assert resultado.indicadores[1].status == "aceito"
    assert repository.calls[-1] == (
        "listar_por_segmento",
        {
            "empresa_id": 1,
            "segmento_chave": "comercio_varejista",
            "perfil": "xml",
        },
    )


def test_recomendar_para_empresa_sem_cnae_nao_busca_recomendacoes():
    repository = FakeIndicadorRecomendacoesRepository(
        empresas={1: {"id": 1, "cnpj": "12345678000190", "cnae_fiscal": None}}
    )
    service = IndicadorRecommendationService(repository=repository)

    resultado = service.recomendar_para_empresa(empresa_id=1)

    assert resultado.cnae_fiscal is None
    assert resultado.segmento_sugerido is None
    assert resultado.fonte is None
    assert resultado.indicadores == []
    assert repository.calls == [("obter_empresa_cnae", 1)]


def test_recomendar_para_empresa_com_cnae_desconhecido_nao_busca_recomendacoes():
    repository = FakeIndicadorRecomendacoesRepository(
        empresas={1: {"id": 1, "cnpj": "12345678000190", "cnae_fiscal": "0111301"}}
    )
    service = IndicadorRecommendationService(repository=repository)

    resultado = service.recomendar_para_empresa(empresa_id=1)

    assert resultado.cnae_fiscal == "0111301"
    assert resultado.segmento_sugerido is None
    assert resultado.indicadores == []
    assert repository.calls == [("obter_empresa_cnae", 1)]


def test_recomendar_para_empresa_inexistente_levanta_erro():
    service = IndicadorRecommendationService(repository=FakeIndicadorRecomendacoesRepository())

    with pytest.raises(EmpresaNaoEncontradaError):
        service.recomendar_para_empresa(empresa_id=999)
