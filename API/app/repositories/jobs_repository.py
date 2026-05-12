from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.cache import ttl_cache
from app.models.jobs.schemas import JobStatus
from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


class JobsRepository:
    _schema_ensured = False

    def __init__(self) -> None:
        self.config = carregar_config_postgres()

    def _connect(self):
        last_error: Exception | None = None
        for options in opcoes_conexao_postgres(self.config):
            try:
                return psycopg.connect(**options, row_factory=dict_row)
            except psycopg.Error as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("Configuracao PostgreSQL invalida.")

    def _ensure_table(self) -> None:
        if JobsRepository._schema_ensured:
            return

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS processing_jobs (
                        id UUID PRIMARY KEY,
                        tipo VARCHAR(80) NOT NULL,
                        status VARCHAR(30) NOT NULL,
                        mensagem TEXT,
                        total_itens INTEGER DEFAULT 0,
                        itens_processados INTEGER DEFAULT 0,
                        erro TEXT,
                        criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        iniciado_em TIMESTAMPTZ,
                        finalizado_em TIMESTAMPTZ,
                        payload JSONB,
                        CONSTRAINT ck_processing_jobs_status
                            CHECK (status IN ('PENDING', 'QUEUED', 'RUNNING', 'SUCCESS', 'FAILED', 'CANCELED'))
                    );

                    CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs (status);
                    CREATE INDEX IF NOT EXISTS idx_processing_jobs_tipo ON processing_jobs (tipo);
                    CREATE INDEX IF NOT EXISTS idx_processing_jobs_criado_em ON processing_jobs (criado_em DESC);
                    """
                )
            conn.commit()

        JobsRepository._schema_ensured = True

    def _clear_read_caches(self) -> None:
        for cached_method in (self.list, self.metrics):
            cache_clear = getattr(cached_method, "cache_clear", None)
            if cache_clear:
                cache_clear()

    def create(
        self,
        *,
        tipo: str,
        payload: dict[str, Any],
        status: JobStatus = JobStatus.PENDING,
        mensagem: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_table()
        job_id = uuid4()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO processing_jobs (id, tipo, status, mensagem, payload)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (job_id, tipo, status.value, mensagem, Jsonb(payload)),
                )
                row = cur.fetchone()
            conn.commit()
        self._clear_read_caches()
        return dict(row)

    def get(self, job_id: str | UUID) -> dict[str, Any] | None:
        self._ensure_table()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM processing_jobs WHERE id = %s", (UUID(str(job_id)),))
                row = cur.fetchone()
        return dict(row) if row else None

    @ttl_cache(ttl_seconds=15, maxsize=128)
    def list(
        self,
        *,
        status: str | None = None,
        tipo: str | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[dict[str, Any]]]:
        self._ensure_table()
        filters: list[str] = []
        params: list[Any] = []

        if status:
            filters.append("status = %s")
            params.append(status)
        if tipo:
            filters.append("tipo = %s")
            params.append(tipo)
        if data_inicio:
            filters.append("criado_em >= %s")
            params.append(data_inicio)
        if data_fim:
            filters.append("criado_em < (%s::date + INTERVAL '1 day')")
            params.append(data_fim)

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) AS total FROM processing_jobs {where_clause}", params)
                total = int(cur.fetchone()["total"])
                cur.execute(
                    f"""
                    SELECT *
                    FROM processing_jobs
                    {where_clause}
                    ORDER BY criado_em DESC
                    LIMIT %s OFFSET %s
                    """,
                    [*params, limit, offset],
                )
                rows = [dict(row) for row in cur.fetchall()]

        return total, rows

    def mark_queued(self, job_id: str | UUID, *, mensagem: str = "Processamento enviado para fila") -> None:
        self.update_status(job_id, JobStatus.QUEUED, mensagem=mensagem)

    def mark_running(self, job_id: str | UUID, *, mensagem: str = "Processamento iniciado") -> None:
        self._ensure_table()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE processing_jobs
                    SET status = %s, mensagem = %s, iniciado_em = COALESCE(iniciado_em, NOW())
                    WHERE id = %s
                    """,
                    (JobStatus.RUNNING.value, mensagem, UUID(str(job_id))),
                )
            conn.commit()
        self._clear_read_caches()

    def update_status(
        self,
        job_id: str | UUID,
        status: JobStatus,
        *,
        mensagem: str | None = None,
        erro: str | None = None,
    ) -> None:
        self._ensure_table()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE processing_jobs
                    SET status = %s,
                        mensagem = COALESCE(%s, mensagem),
                        erro = COALESCE(%s, erro),
                        finalizado_em = CASE WHEN %s IN ('SUCCESS', 'FAILED', 'CANCELED') THEN NOW() ELSE finalizado_em END
                    WHERE id = %s
                    """,
                    (status.value, mensagem, erro, status.value, UUID(str(job_id))),
                )
            conn.commit()
        self._clear_read_caches()

    def update_progress(
        self,
        job_id: str | UUID,
        *,
        total_itens: int | None = None,
        itens_processados: int | None = None,
        mensagem: str | None = None,
    ) -> None:
        self._ensure_table()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE processing_jobs
                    SET total_itens = COALESCE(%s, total_itens),
                        itens_processados = COALESCE(%s, itens_processados),
                        mensagem = COALESCE(%s, mensagem)
                    WHERE id = %s
                    """,
                    (total_itens, itens_processados, mensagem, UUID(str(job_id))),
                )
            conn.commit()
        self._clear_read_caches()

    @ttl_cache(ttl_seconds=15, maxsize=128)
    def metrics(
        self,
        *,
        status: str | None = None,
        tipo: str | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> dict[str, Any]:
        self._ensure_table()
        filters: list[str] = []
        params: list[Any] = []

        if status:
            filters.append("status = %s")
            params.append(status)
        if tipo:
            filters.append("tipo = %s")
            params.append(tipo)
        if data_inicio:
            filters.append("criado_em >= %s")
            params.append(data_inicio)
        if data_fim:
            filters.append("criado_em < (%s::date + INTERVAL '1 day')")
            params.append(data_fim)

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) AS total FROM processing_jobs {where_clause}", params)
                total = int(cur.fetchone()["total"])

                cur.execute(
                    f"""
                    SELECT status, COUNT(*) AS total
                    FROM processing_jobs
                    {where_clause}
                    GROUP BY status
                    """,
                    params,
                )
                por_status = {
                    str(row["status"]): int(row["total"])
                    for row in cur.fetchall()
                }

                cur.execute(
                    f"""
                    SELECT tipo, COUNT(*) AS total
                    FROM processing_jobs
                    {where_clause}
                    GROUP BY tipo
                    """,
                    params,
                )
                por_tipo = {
                    str(row["tipo"]): int(row["total"])
                    for row in cur.fetchall()
                }

                cur.execute(
                    f"""
                    SELECT
                        tipo,
                        AVG(EXTRACT(EPOCH FROM (finalizado_em - iniciado_em)) * 1000) AS duracao_media_ms
                    FROM processing_jobs
                    {where_clause}
                    {"AND" if where_clause else "WHERE"} iniciado_em IS NOT NULL
                      AND finalizado_em IS NOT NULL
                    GROUP BY tipo
                    """,
                    params,
                )
                duracao_media_ms = {
                    str(row["tipo"]): round(float(row["duracao_media_ms"] or 0), 2)
                    for row in cur.fetchall()
                }

        return {
            "total_jobs": total,
            "por_status": por_status,
            "por_tipo": por_tipo,
            "duracao_media_ms": duracao_media_ms,
        }
