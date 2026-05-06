from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class JobType(StrEnum):
    NFE_PROCESSAMENTO_IMPORTADOS = "NFE_PROCESSAMENTO_IMPORTADOS"
    SPED_PROCESSAMENTO_IMPORTADOS = "SPED_PROCESSAMENTO_IMPORTADOS"


class JobCreateResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    message: str


class ProcessingJobResponse(BaseModel):
    job_id: UUID = Field(alias="id")
    tipo: str
    status: str
    mensagem: str | None = None
    total_itens: int = 0
    itens_processados: int = 0
    erro: str | None = None
    criado_em: datetime
    iniciado_em: datetime | None = None
    finalizado_em: datetime | None = None

    class Config:
        populate_by_name = True


class ProcessingJobListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    resultados: list[ProcessingJobResponse]


class JobsMetricsResponse(BaseModel):
    total_jobs: int
    por_status: dict[str, int]
    por_tipo: dict[str, int]
    duracao_media_ms: dict[str, float]


class JobDispatchPayload(BaseModel):
    tipo: JobType
    payload: dict[str, Any]
