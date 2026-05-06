from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.models.jobs.schemas import JobsMetricsResponse, ProcessingJobListResponse, ProcessingJobResponse
from app.repositories.jobs_repository import JobsRepository

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/metrics", response_model=JobsMetricsResponse)
def obter_metricas_jobs(
    tipo: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
):
    return JobsRepository().metrics(tipo=tipo, status=status_filter, data_inicio=data_inicio, data_fim=data_fim)


@router.get("", response_model=ProcessingJobListResponse)
def listar_jobs(
    status_filter: str | None = Query(default=None, alias="status"),
    tipo: str | None = Query(default=None),
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    total, rows = JobsRepository().list(
        status=status_filter,
        tipo=tipo,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limit=limit,
        offset=offset,
    )
    return ProcessingJobListResponse(
        total=total,
        limit=limit,
        offset=offset,
        resultados=[ProcessingJobResponse(**row) for row in rows],
    )


@router.get("/{job_id}", response_model=ProcessingJobResponse)
def obter_job(job_id: UUID):
    job = JobsRepository().get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job nao encontrado.")
    return ProcessingJobResponse(**job)
