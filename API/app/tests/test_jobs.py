from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.jobs.schemas import JobStatus


def _job_row(job_id=None, status="QUEUED", tipo="NFE_PROCESSAMENTO_IMPORTADOS"):
    return {
        "id": job_id or uuid4(),
        "tipo": tipo,
        "status": status,
        "mensagem": "ok",
        "total_itens": 1,
        "itens_processados": 0,
        "erro": None,
        "criado_em": datetime.now(timezone.utc),
        "iniciado_em": None,
        "finalizado_em": None,
        "payload": {},
    }


class FakeJobsRepository:
    rows = [_job_row()]

    def get(self, job_id):
        return {**self.rows[0], "id": job_id}

    def list(self, **kwargs):
        return len(self.rows), self.rows

    def metrics(self, **kwargs):
        return {
            "total_jobs": 1,
            "por_status": {"QUEUED": 1},
            "por_tipo": {"NFE_PROCESSAMENTO_IMPORTADOS": 1},
            "duracao_media_ms": {},
        }


def test_listar_jobs(client, monkeypatch):
    monkeypatch.setattr("app.api.jobs.routes.JobsRepository", FakeJobsRepository)

    response = client.get("/api/jobs?status=QUEUED")

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_obter_job(client, monkeypatch):
    monkeypatch.setattr("app.api.jobs.routes.JobsRepository", FakeJobsRepository)
    job_id = uuid4()

    response = client.get(f"/api/jobs/{job_id}")

    assert response.status_code == 200
    assert response.json()["job_id"] == str(job_id)


def test_metricas_jobs(client, monkeypatch):
    monkeypatch.setattr("app.api.jobs.routes.JobsRepository", FakeJobsRepository)

    response = client.get("/api/jobs/metrics")

    assert response.status_code == 200
    assert response.json()["por_status"]["QUEUED"] == 1


def test_endpoint_nfe_processar_importados_retorna_202(client, monkeypatch):
    job_id = uuid4()
    monkeypatch.setattr("app.api.nfe.routes.CompanyProfileService.empresa_tem_sped", lambda self, cnpj: False)
    monkeypatch.setattr("app.api.nfe.routes.XMLImportacaoService.contar_xmls_pendentes", lambda self, cnpj: 1)
    monkeypatch.setattr(
        "app.api.nfe.routes.JobService.criar_processamento_nfe_importados",
        lambda self, cnpj_emitente: {"job_id": job_id, "status": "QUEUED", "message": "Processamento enviado para fila"},
    )

    response = client.post("/api/nfe/xml/processar-importados?cnpj_emitente=12345678000190")

    assert response.status_code == 202
    assert response.json()["job_id"] == str(job_id)


def test_endpoint_sped_processar_importados_retorna_202(client, monkeypatch):
    job_id = uuid4()
    monkeypatch.setattr("app.api.sped.routes.CompanyProfileService.empresa_tem_sped", lambda self, cnpj: True)
    monkeypatch.setattr("app.api.sped.routes.SpedImportacaoService.contar_pendentes", lambda self, cnpj: 1)
    monkeypatch.setattr(
        "app.api.sped.routes.JobService.criar_processamento_sped_importados",
        lambda self, cnpj_emitente: {"job_id": job_id, "status": "QUEUED", "message": "Processamento enviado para fila"},
    )

    response = client.post("/api/sped/processar-importados?cnpj_emitente=12345678000190")

    assert response.status_code == 202
    assert response.json()["job_id"] == str(job_id)


def test_job_service_dispatch_normal_marca_queued():
    from app.services.jobs.job_service import JobService

    job_id = uuid4()
    calls = []

    class Repo:
        def get(self, job_id):
            return None

        def mark_queued(self, job_id):
            calls.append(("queued", job_id))

    class Task:
        app = type("App", (), {"conf": type("Conf", (), {"task_always_eager": False})()})()

        def apply_async(self, **kwargs):
            calls.append(("apply", kwargs))

    service = JobService(repository=Repo())

    response = service._response_after_dispatch(job=_job_row(job_id), task=Task(), payload={}, queue="nfe")

    assert response.status == JobStatus.QUEUED
    assert calls[-1] == ("queued", job_id)


def test_job_service_dispatch_eager_retorna_status_atual():
    from app.services.jobs.job_service import JobService

    job_id = uuid4()
    calls = []

    class Repo:
        def get(self, job_id):
            return _job_row(job_id, status="SUCCESS")

        def mark_queued(self, job_id):
            calls.append(("queued", job_id))

    class Task:
        app = type("App", (), {"conf": type("Conf", (), {"task_always_eager": True})()})()

        def apply_async(self, **kwargs):
            calls.append(("apply", kwargs))

    service = JobService(repository=Repo())

    response = service._response_after_dispatch(job=_job_row(job_id), task=Task(), payload={}, queue="nfe")

    assert response.status == JobStatus.SUCCESS
    assert ("queued", job_id) not in calls


def test_job_success_simulado(monkeypatch):
    updates = []

    class Repo:
        def mark_running(self, job_id, mensagem=None):
            updates.append(("running", mensagem))

        def update_progress(self, job_id, **kwargs):
            updates.append(("progress", kwargs))

        def update_status(self, job_id, status, **kwargs):
            updates.append(("status", status, kwargs))

    class Importacao:
        def listar_xmls_importados_nao_processados(self, cnpj):
            return [(1, "nfe.xml", b"<xml/>")]

        def marcar_como_processados(self, ids):
            updates.append(("marcar", ids))

    class Processador:
        def executar_xmls_importados(self, cnpj_emitente, xmls_importados):
            return type("Resp", (), {"status": "processado", "erros": []})(), [1]

    monkeypatch.setattr("app.workers.nfe_tasks.JobsRepository", Repo)
    monkeypatch.setattr("app.workers.nfe_tasks.XMLImportacaoService", Importacao)
    monkeypatch.setattr("app.workers.nfe_tasks.ProcessarNFeService", Processador)

    from app.workers.nfe_tasks import processar_nfe_importados_task

    result = processar_nfe_importados_task.run("job-1", {"cnpj_emitente": "12345678000190"})

    assert result["status"] == "SUCCESS"
    assert any(item[0] == "status" and item[1] == JobStatus.SUCCESS for item in updates)


def test_job_failed_simulado(monkeypatch):
    updates = []

    class Repo:
        def mark_running(self, job_id, mensagem=None):
            pass

        def update_progress(self, job_id, **kwargs):
            pass

        def update_status(self, job_id, status, **kwargs):
            updates.append((status, kwargs))

    class Importacao:
        def listar_xmls_importados_nao_processados(self, cnpj):
            return []

    monkeypatch.setattr("app.workers.nfe_tasks.JobsRepository", Repo)
    monkeypatch.setattr("app.workers.nfe_tasks.XMLImportacaoService", Importacao)

    from app.workers.nfe_tasks import processar_nfe_importados_task

    with pytest.raises(ValueError):
        processar_nfe_importados_task.run("job-1", {"cnpj_emitente": "12345678000190"})

    assert updates[0][0] == JobStatus.FAILED
