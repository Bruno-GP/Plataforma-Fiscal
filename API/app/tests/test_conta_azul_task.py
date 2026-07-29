from app.workers import conta_azul_tasks
from contaazul.client import ApiError


class FakeRepository:
    def __init__(self, empresas):
        self._empresas = empresas

    def listar_empresas_ativas(self):
        return self._empresas


def _set_credenciais(monkeypatch):
    monkeypatch.setenv("CONTAAZUL_CLIENT_ID", "id")
    monkeypatch.setenv("CONTAAZUL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("CONTAAZUL_REDIRECT_URI", "https://example.com/callback")


def test_falha_em_uma_empresa_nao_aborta_as_demais(monkeypatch):
    _set_credenciais(monkeypatch)
    monkeypatch.setattr(
        conta_azul_tasks,
        "_repositorio_empresas",
        lambda: FakeRepository([(1, "11111111000191"), (2, "22222222000192")]),
    )

    def _sincronizar_empresa(auth_client, empresa_id, inicio, fim):
        if empresa_id == 2:
            raise ApiError(500, {"erro": "instabilidade"})
        return 3

    monkeypatch.setattr(conta_azul_tasks, "_sincronizar_empresa", _sincronizar_empresa)

    resultado = conta_azul_tasks.sincronizar_kpis_conta_azul_task.run()

    assert resultado["status"] == "SUCCESS"
    assert resultado["empresas_ok"] == 1
    assert resultado["empresas_falha"] == 1


def test_aborta_sem_credenciais(monkeypatch):
    monkeypatch.delenv("CONTAAZUL_CLIENT_ID", raising=False)
    monkeypatch.delenv("CONTAAZUL_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("CONTAAZUL_REDIRECT_URI", raising=False)

    resultado = conta_azul_tasks.sincronizar_kpis_conta_azul_task.run()

    assert resultado["status"] == "FAILED"
