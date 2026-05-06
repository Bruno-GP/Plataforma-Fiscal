from __future__ import annotations

from typing import Any

from app.models.jobs.schemas import JobCreateResponse, JobStatus, JobType
from app.repositories.jobs_repository import JobsRepository


class JobService:
    def __init__(self, repository: JobsRepository | None = None) -> None:
        self.repository = repository or JobsRepository()

    def _task_runs_eagerly(self, task: Any) -> bool:
        app = getattr(task, "app", None)
        conf = getattr(app, "conf", None)
        return bool(getattr(conf, "task_always_eager", False))

    def _response_after_dispatch(self, *, job: dict[str, Any], task: Any, payload: dict[str, Any], queue: str) -> JobCreateResponse:
        task.apply_async(
            args=[str(job["id"]), payload],
            queue=queue,
        )

        if self._task_runs_eagerly(task):
            current_job = self.repository.get(job["id"]) or job
            return JobCreateResponse(
                job_id=job["id"],
                status=JobStatus(current_job["status"]),
                message=current_job.get("mensagem") or "Processamento executado",
            )

        self.repository.mark_queued(job["id"])
        return JobCreateResponse(job_id=job["id"], status=JobStatus.QUEUED, message="Processamento enviado para fila")

    def criar_processamento_nfe_importados(self, *, cnpj_emitente: str) -> JobCreateResponse:
        payload = {"cnpj_emitente": cnpj_emitente}
        job = self.repository.create(
            tipo=JobType.NFE_PROCESSAMENTO_IMPORTADOS.value,
            payload=payload,
            mensagem="Job NFe criado",
        )
        from app.workers.nfe_tasks import processar_nfe_importados_task

        return self._response_after_dispatch(
            job=job,
            task=processar_nfe_importados_task,
            payload=payload,
            queue="nfe",
        )

    def criar_processamento_sped_importados(self, *, cnpj_emitente: str) -> JobCreateResponse:
        payload = {"cnpj_emitente": cnpj_emitente}
        job = self.repository.create(
            tipo=JobType.SPED_PROCESSAMENTO_IMPORTADOS.value,
            payload=payload,
            mensagem="Job SPED criado",
        )
        from app.workers.sped_tasks import processar_sped_importados_task

        return self._response_after_dispatch(
            job=job,
            task=processar_sped_importados_task,
            payload=payload,
            queue="sped",
        )

    def obter(self, job_id: str) -> dict[str, Any] | None:
        return self.repository.get(job_id)
