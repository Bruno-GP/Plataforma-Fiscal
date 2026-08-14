from decimal import Decimal

from app.services.metas.metas_historico_service import MetasHistoricoService


class FakeIndicadoresRepository:
    def __init__(self, indicadores):
        self._indicadores = indicadores

    def listar(self, perfil="xml"):
        return self._indicadores


class FakeHistoricoRepository:
    def __init__(self, linhas_agregadas):
        self._linhas_agregadas = linhas_agregadas
        self.upserts = []

    def agregar_por_empresa(self, cnpj_normalizado):
        return self._linhas_agregadas

    def upsert_historico(self, empresa_id, indicador_id_por_chave, linhas):
        self.upserts.append((empresa_id, indicador_id_por_chave, linhas))
        return len(linhas) * len(indicador_id_por_chave)


def test_materializar_empresa_grava_uma_linha_por_indicador_por_mes():
    indicadores = [
        {"id": 1, "chave": "faturamento"},
        {"id": 2, "chave": "ticket_medio"},
    ]
    linhas_agregadas = [
        {"periodo_referencia": "2026-06-01", "faturamento": Decimal("10000.00"), "ticket_medio": Decimal("500.00")},
        {"periodo_referencia": "2026-07-01", "faturamento": Decimal("12000.00"), "ticket_medio": Decimal("550.00")},
    ]
    historico_repo = FakeHistoricoRepository(linhas_agregadas)
    service = MetasHistoricoService(
        indicadores_repository=FakeIndicadoresRepository(indicadores),
        historico_repository=historico_repo,
    )

    total_gravado = service.materializar_empresa(empresa_id=1, cnpj="11111111000191")

    assert total_gravado == 4
    empresa_id, indicador_id_por_chave, linhas = historico_repo.upserts[0]
    assert empresa_id == 1
    assert indicador_id_por_chave == {"faturamento": 1, "ticket_medio": 2}
    assert linhas == linhas_agregadas


def test_materializar_empresa_sem_dado_retorna_zero():
    service = MetasHistoricoService(
        indicadores_repository=FakeIndicadoresRepository([{"id": 1, "chave": "faturamento"}]),
        historico_repository=FakeHistoricoRepository([]),
    )

    total_gravado = service.materializar_empresa(empresa_id=1, cnpj="11111111000191")

    assert total_gravado == 0
