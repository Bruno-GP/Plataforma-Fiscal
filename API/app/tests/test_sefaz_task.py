from app.services.sefaz.sefaz_distribuicao_service import ResultadoSincronizacao
from app.workers import sefaz_tasks


class FakeCertificadosRepository:
    def __init__(self, certificados):
        self._certificados = certificados

    def listar_ativos_com_validade(self):
        return self._certificados


def test_sync_diario_dispara_uma_task_por_certificado_ativo(monkeypatch):
    monkeypatch.setattr(
        sefaz_tasks,
        "_repositorio_certificados",
        lambda: FakeCertificadosRepository(
            [
                {"empresa_id": 1, "cnpj_titular": "11111111000191"},
                {"empresa_id": 2, "cnpj_titular": "22222222000192"},
            ]
        ),
    )
    chamadas = []
    monkeypatch.setattr(
        sefaz_tasks.sefaz_sync_empresa_task,
        "apply_async",
        lambda args, queue: chamadas.append((args, queue)),
    )

    resultado = sefaz_tasks.sefaz_sync_diario_task.run()

    assert resultado["status"] == "SUCCESS"
    assert resultado["empresas_disparadas"] == 2
    assert chamadas == [
        ([1, "11111111000191"], "sefaz"),
        ([2, "22222222000192"], "sefaz"),
    ]


def test_sync_diario_sem_certificados_dispara_zero():
    from app.workers import sefaz_tasks as modulo

    original = modulo._repositorio_certificados
    modulo._repositorio_certificados = lambda: FakeCertificadosRepository([])
    try:
        resultado = modulo.sefaz_sync_diario_task.run()
    finally:
        modulo._repositorio_certificados = original

    assert resultado == {"status": "SUCCESS", "empresas_disparadas": 0}


def test_sync_empresa_task_retorna_resultado_do_service(monkeypatch):
    monkeypatch.setattr(
        sefaz_tasks,
        "_sincronizar_empresa",
        lambda empresa_id, cnpj_titular: ResultadoSincronizacao(
            status="sucesso", documentos_novos=5, nsu_inicial="0", nsu_final="10"
        ),
    )

    resultado = sefaz_tasks.sefaz_sync_empresa_task.run(1, "11111111000191")

    assert resultado == {"status": "sucesso", "documentos_novos": 5, "empresa_id": 1}


def test_sync_empresa_task_propaga_excecao_para_autoretry(monkeypatch):
    import pytest

    def _levanta_erro_transiente(empresa_id, cnpj_titular):
        raise ConnectionError("Falha ao consultar distDFeInt: timeout")

    monkeypatch.setattr(sefaz_tasks, "_sincronizar_empresa", _levanta_erro_transiente)

    with pytest.raises(ConnectionError):
        sefaz_tasks.sefaz_sync_empresa_task.run(1, "11111111000191")


def test_evento_documento_novo_task_roda_sem_erro():
    resultado = sefaz_tasks.sefaz_evento_documento_novo_task.run(
        1, "35260812345678000190550010000000011234567890"
    )

    assert resultado == {"status": "SUCCESS"}
