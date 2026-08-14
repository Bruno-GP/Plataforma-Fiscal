from datetime import date
from decimal import Decimal

import pytest

from app.services.metas.metas_service import IndicadorInvalidoError, MetaNaoEncontradaError, MetasService


class FakeMetasRepository:
    def __init__(self, metas=None):
        self._metas = metas or {}
        self._next_id = max(self._metas.keys(), default=0) + 1

    def criar(self, **campos):
        meta_id = self._next_id
        self._next_id += 1
        meta = {
            "id": meta_id,
            "status": "ativa",
            "criado_em": "2026-08-13T00:00:00",
            "atualizado_em": "2026-08-13T00:00:00",
            **campos,
        }
        self._metas[meta_id] = meta
        return meta

    def obter(self, meta_id, empresa_id):
        meta = self._metas.get(meta_id)
        if not meta or meta["empresa_id"] != empresa_id:
            return None
        return meta

    def listar(self, empresa_id, status=None, indicador_id=None):
        return [m for m in self._metas.values() if m["empresa_id"] == empresa_id]

    def atualizar(self, meta_id, empresa_id, campos):
        meta = self.obter(meta_id, empresa_id)
        if not meta:
            return None
        meta.update(campos)
        return meta

    def cancelar(self, meta_id, empresa_id):
        meta = self.obter(meta_id, empresa_id)
        if not meta:
            return False
        meta["status"] = "cancelada"
        return True


class FakeIndicadoresRepository:
    def __init__(self, indicadores):
        self._indicadores = {i["id"]: i for i in indicadores}

    def obter_por_id(self, indicador_id):
        return self._indicadores.get(indicador_id)

    def historico(self, empresa_id, indicador_id, meses=12):
        return []


def _service(metas=None, indicadores=None):
    return MetasService(
        metas_repository=FakeMetasRepository(metas),
        indicadores_repository=FakeIndicadoresRepository(
            indicadores or [{"id": 1, "chave": "faturamento", "direcao_boa": "maior_melhor", "ativo": True, "perfil": "xml"}]
        ),
    )


def test_criar_meta_com_indicador_valido():
    service = _service()

    meta = service.criar(
        empresa_id=1,
        indicador_id=1,
        titulo="Crescer faturamento",
        descricao=None,
        valor_alvo=Decimal("50000.00"),
        tipo_meta="crescimento",
        periodo_tipo="mensal",
        periodo_inicio=date(2026, 8, 1),
        periodo_fim=date(2026, 8, 31),
        criado_por=1,
    )

    assert meta["indicador_id"] == 1
    assert meta["empresa_id"] == 1


def test_criar_meta_com_indicador_inexistente_levanta_erro():
    service = _service(indicadores=[])

    with pytest.raises(IndicadorInvalidoError):
        service.criar(
            empresa_id=1,
            indicador_id=999,
            titulo="Meta invalida",
            descricao=None,
            valor_alvo=Decimal("1000.00"),
            tipo_meta="crescimento",
            periodo_tipo="mensal",
            periodo_inicio=date(2026, 8, 1),
            periodo_fim=date(2026, 8, 31),
            criado_por=1,
        )


def test_obter_meta_de_outra_empresa_levanta_nao_encontrada():
    service = _service(
        metas={
            1: {
                "id": 1,
                "empresa_id": 2,
                "indicador_id": 1,
                "titulo": "X",
                "valor_alvo": Decimal("100"),
                "periodo_inicio": date(2026, 8, 1),
                "periodo_fim": date(2026, 8, 31),
                "status": "ativa",
            }
        }
    )

    with pytest.raises(MetaNaoEncontradaError):
        service.obter(meta_id=1, empresa_id=1)


def test_analisar_meta_usa_indicador_e_historico():
    metas = {
        1: {
            "id": 1,
            "empresa_id": 1,
            "indicador_id": 1,
            "titulo": "X",
            "valor_alvo": Decimal("50000.00"),
            "periodo_inicio": date(2026, 8, 1),
            "periodo_fim": date(2026, 8, 31),
            "status": "ativa",
            "periodo_tipo": "mensal",
        }
    }
    service = _service(metas=metas)

    analise = service.analisar(
        meta_id=1,
        empresa_id=1,
        valor_realizado_atual=Decimal("30000.00"),
        data_referencia=date(2026, 8, 20),
    )

    assert analise.valor_alvo == Decimal("50000.00")
