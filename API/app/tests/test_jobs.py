from datetime import datetime, timezone
import logging
from uuid import uuid4

import pytest

from app.models.jobs.schemas import JobStatus


def _job_row(job_id=None, status="QUEUED", tipo="NFE_PROCESSAMENTO_IMPORTADOS", cnpj="12345678000190"):
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
        "payload": {"cnpj_emitente": cnpj},
    }


class FakeJobsRepository:
    rows = [_job_row()]

    def get(self, job_id):
        return {**self.rows[0], "id": job_id}

    def list(self, **kwargs):
        cnpj_emitente = kwargs.get("cnpj_emitente")
        rows = [
            row
            for row in self.rows
            if not cnpj_emitente or row.get("payload", {}).get("cnpj_emitente") == cnpj_emitente
        ]
        return len(rows), rows

    def metrics(self, **kwargs):
        cnpj_emitente = kwargs.get("cnpj_emitente")
        rows = [
            row
            for row in self.rows
            if not cnpj_emitente or row.get("payload", {}).get("cnpj_emitente") == cnpj_emitente
        ]
        return {
            "total_jobs": len(rows),
            "por_status": {"QUEUED": len(rows)} if rows else {},
            "por_tipo": {"NFE_PROCESSAMENTO_IMPORTADOS": len(rows)} if rows else {},
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


def test_jobs_exigem_autenticacao(unauthenticated_client, monkeypatch):
    monkeypatch.setattr("app.api.jobs.routes.JobsRepository", FakeJobsRepository)

    assert unauthenticated_client.get("/api/jobs").status_code == 401
    assert unauthenticated_client.get(f"/api/jobs/{uuid4()}").status_code == 401
    assert unauthenticated_client.get("/api/jobs/metrics").status_code == 401


def test_listar_jobs_filtra_por_empresa_autenticada(client, monkeypatch):
    class ScopedRepo(FakeJobsRepository):
        rows = [
            _job_row(cnpj="12345678000190"),
            _job_row(cnpj="99999999000199"),
        ]

    monkeypatch.setattr("app.api.jobs.routes.JobsRepository", ScopedRepo)

    response = client.get("/api/jobs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["resultados"]) == 1


def test_metricas_jobs_filtra_por_empresa_autenticada(client, monkeypatch):
    class ScopedRepo(FakeJobsRepository):
        rows = [
            _job_row(cnpj="12345678000190"),
            _job_row(cnpj="99999999000199"),
        ]

    monkeypatch.setattr("app.api.jobs.routes.JobsRepository", ScopedRepo)

    response = client.get("/api/jobs/metrics")

    assert response.status_code == 200
    assert response.json()["total_jobs"] == 1


def test_obter_job_de_outra_empresa_retorna_404(client, monkeypatch):
    class ForeignRepo(FakeJobsRepository):
        rows = [_job_row(cnpj="99999999000199")]

    monkeypatch.setattr("app.api.jobs.routes.JobsRepository", ForeignRepo)

    response = client.get(f"/api/jobs/{uuid4()}")

    assert response.status_code == 404


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


def test_job_success_simulado(monkeypatch, caplog):
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

    with caplog.at_level(logging.INFO, logger="workers.nfe"):
        result = processar_nfe_importados_task.run("job-1", {"cnpj_emitente": "12345678000190"})

    assert result["status"] == "SUCCESS"
    assert any(item[0] == "status" and item[1] == JobStatus.SUCCESS for item in updates)
    completed = next(record for record in caplog.records if record.message == "job_completed")
    assert completed.job_id == "job-1"
    assert completed.tipo_job == "NFE_PROCESSAMENTO_IMPORTADOS"
    assert completed.cnpj_emitente == "12345678000190"
    assert completed.etapa == "complete"
    assert completed.status == "SUCCESS"
    assert completed.total_itens == 1
    assert completed.itens_processados == 1


def test_job_failed_simulado(monkeypatch, caplog):
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

    with caplog.at_level(logging.ERROR, logger="workers.nfe"):
        with pytest.raises(ValueError):
            processar_nfe_importados_task.run("job-1", {"cnpj_emitente": "12345678000190"})

    assert updates[0][0] == JobStatus.FAILED
    failed = next(record for record in caplog.records if record.message == "job_failed")
    assert failed.job_id == "job-1"
    assert failed.tipo_job == "NFE_PROCESSAMENTO_IMPORTADOS"
    assert failed.cnpj_emitente == "12345678000190"
    assert failed.etapa == "failed"
    assert failed.status == "FAILED"
    assert failed.erro_tipo == "ValueError"


def test_nfe_job_falha_quando_processador_nao_consolida(monkeypatch, caplog):
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
            erro = {"mensagem": "Falha fiscal"}
            return type("Resp", (), {"status": "erro", "erros": [erro]})(), []

    monkeypatch.setattr("app.workers.nfe_tasks.JobsRepository", Repo)
    monkeypatch.setattr("app.workers.nfe_tasks.XMLImportacaoService", Importacao)
    monkeypatch.setattr("app.workers.nfe_tasks.ProcessarNFeService", Processador)

    from app.workers.nfe_tasks import processar_nfe_importados_task

    with caplog.at_level(logging.ERROR, logger="workers.nfe"):
        with pytest.raises(RuntimeError, match="Falha fiscal"):
            processar_nfe_importados_task.run("job-nfe-erro", {"cnpj_emitente": "12345678000190"})

    assert ("marcar", []) not in updates
    status_update = next(item for item in updates if item[0] == "status")
    assert status_update[1] == JobStatus.FAILED
    assert status_update[2]["erro"] == "Falha fiscal"
    failed = next(record for record in caplog.records if record.message == "job_failed")
    assert failed.erro_tipo == "RuntimeError"
    assert failed.status == "FAILED"


def test_sped_job_success_loga_contexto_operacional(monkeypatch, caplog):
    updates = []

    class Repo:
        def mark_running(self, job_id, mensagem=None):
            updates.append(("running", mensagem))

        def update_progress(self, job_id, **kwargs):
            updates.append(("progress", kwargs))

        def update_status(self, job_id, status, **kwargs):
            updates.append(("status", status, kwargs))

    class Importacao:
        def contar_pendentes(self, cnpj):
            return 1

        def processar_importados(self, cnpj):
            return {"C100": 2}, 10, [7]

        def marcar_como_processados(self, ids):
            updates.append(("marcar", ids))

    class Processador:
        config = {"database": "plataforma_fiscal_test"}

    monkeypatch.setattr("app.workers.sped_tasks.JobsRepository", Repo)
    monkeypatch.setattr("app.workers.sped_tasks.SpedImportacaoService", Importacao)
    monkeypatch.setattr("app.workers.sped_tasks.ProcessarSpedFiscalService", Processador)

    from app.workers.sped_tasks import processar_sped_importados_task

    with caplog.at_level(logging.INFO, logger="workers.sped"):
        result = processar_sped_importados_task.run("job-sped-1", {"cnpj_emitente": "12345678000190"})

    assert result["status"] == "SUCCESS"
    completed = next(record for record in caplog.records if record.message == "job_completed")
    assert completed.job_id == "job-sped-1"
    assert completed.tipo_job == "SPED_PROCESSAMENTO_IMPORTADOS"
    assert completed.cnpj_emitente == "12345678000190"
    assert completed.etapa == "complete"
    assert completed.status == "SUCCESS"
    assert completed.total_itens == 1
    assert completed.itens_processados == 1


def test_sped_job_falha_quando_processamento_nao_retorna_ids(monkeypatch, caplog):
    updates = []

    class Repo:
        def mark_running(self, job_id, mensagem=None):
            updates.append(("running", mensagem))

        def update_progress(self, job_id, **kwargs):
            updates.append(("progress", kwargs))

        def update_status(self, job_id, status, **kwargs):
            updates.append(("status", status, kwargs))

    class Importacao:
        def contar_pendentes(self, cnpj):
            return 1

        def processar_importados(self, cnpj):
            return {}, 0, []

        def marcar_como_processados(self, ids):
            updates.append(("marcar", ids))

    monkeypatch.setattr("app.workers.sped_tasks.JobsRepository", Repo)
    monkeypatch.setattr("app.workers.sped_tasks.SpedImportacaoService", Importacao)

    from app.workers.sped_tasks import processar_sped_importados_task

    with caplog.at_level(logging.ERROR, logger="workers.sped"):
        with pytest.raises(ValueError, match="Nenhum arquivo SPED pendente"):
            processar_sped_importados_task.run("job-sped-erro", {"cnpj_emitente": "12345678000190"})

    assert ("marcar", []) not in updates
    assert any(item[0] == "progress" and item[1]["total_itens"] == 1 for item in updates)
    status_update = next(item for item in updates if item[0] == "status")
    assert status_update[1] == JobStatus.FAILED
    failed = next(record for record in caplog.records if record.message == "job_failed")
    assert failed.erro_tipo == "ValueError"
    assert failed.status == "FAILED"
