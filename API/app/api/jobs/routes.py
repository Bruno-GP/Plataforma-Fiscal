from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.models.jobs.schemas import JobsMetricsResponse, ProcessingJobListResponse, ProcessingJobResponse
from app.repositories.jobs_repository import JobsRepository

router = APIRouter(prefix="/jobs", tags=["Jobs"])

_jobs_repository: JobsRepository | None = None
_jobs_repository_cls: type[JobsRepository] | None = None

def get_jobs_repository() -> JobsRepository:
    global _jobs_repository, _jobs_repository_cls
    if _jobs_repository is None or _jobs_repository_cls is not JobsRepository:
        _jobs_repository = JobsRepository()
        _jobs_repository_cls = JobsRepository
    return _jobs_repository


@router.get("/metrics", response_model=JobsMetricsResponse)
def obter_metricas_jobs(
    tipo: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
):
    return get_jobs_repository().metrics(tipo=tipo, status=status_filter, data_inicio=data_inicio, data_fim=data_fim)


@router.get("", response_model=ProcessingJobListResponse, response_model_by_alias=False)
def listar_jobs(
    status_filter: str | None = Query(default=None, alias="status"),
    tipo: str | None = Query(default=None),
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    total, rows = get_jobs_repository().list(
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


@router.get("/{job_id}", response_model=ProcessingJobResponse, response_model_by_alias=False)
def obter_job(job_id: UUID):
    job = get_jobs_repository().get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job nao encontrado.")
    return ProcessingJobResponse(**job)
