from __future__ import annotations

import logging
import time

from app.models.jobs.schemas import JobStatus
from app.models.sped.schemas import RegistroSpedResumo
from app.repositories.jobs_repository import JobsRepository
from app.services.sped.sped_importacao_service import SpedImportacaoService
from app.services.sped.sped_process_service import ProcessarSpedFiscalService
from app.workers.celery_app import celery_app

logger = logging.getLogger("workers.sped")


@celery_app.task(
    name="processar_sped_importados_task",
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def processar_sped_importados_task(job_id: str, payload: dict) -> dict:
    repository = JobsRepository()
    started_at = time.perf_counter()
    cnpj_emitente = str(payload.get("cnpj_emitente") or "")
    logger.info("job_started", extra={"job_id": job_id, "tipo_job": "SPED_PROCESSAMENTO_IMPORTADOS", "etapa": "start"})
    repository.mark_running(job_id, mensagem="Processando arquivos SPED importados")

    try:
        service = SpedImportacaoService()
        pendentes = service.contar_pendentes(cnpj_emitente)
        repository.update_progress(job_id, total_itens=pendentes, itens_processados=0)
        registros, total_linhas, ids_processados = service.processar_importados(cnpj_emitente)

        if not ids_processados:
            raise ValueError("Nenhum arquivo SPED pendente encontrado para o CNPJ informado.")

        service.marcar_como_processados(ids_processados)
        config = ProcessarSpedFiscalService().config
        resumo_ordenado = sorted(registros.items(), key=lambda item: (-item[1], item[0]))
        resumo = [RegistroSpedResumo(registro=registro, quantidade=quantidade).model_dump() for registro, quantidade in resumo_ordenado]
        repository.update_progress(
            job_id,
            total_itens=pendentes,
            itens_processados=len(ids_processados),
            mensagem="Arquivos SPED processados",
        )
        repository.update_status(job_id, JobStatus.SUCCESS, mensagem="Processamento SPED concluido")
        duracao_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "job_completed",
            extra={
                "job_id": job_id,
                "tipo_job": "SPED_PROCESSAMENTO_IMPORTADOS",
                "status": "SUCCESS",
                "duracao_ms": duracao_ms,
                "total_itens": pendentes,
                "itens_processados": len(ids_processados),
            },
        )
        return {
            "status": "SUCCESS",
            "job_id": job_id,
            "total_linhas": total_linhas,
            "total_registros_identificados": sum(registros.values()),
            "total_arquivos_processados": len(ids_processados),
            "resumo_registros": resumo,
            "banco_sped": config["database"],
        }
    except Exception as exc:
        repository.update_status(job_id, JobStatus.FAILED, mensagem="Falha no processamento SPED", erro=str(exc))
        logger.exception(
            "job_failed",
            extra={"job_id": job_id, "tipo_job": "SPED_PROCESSAMENTO_IMPORTADOS", "status": "FAILED", "erro": str(exc)},
        )
        raise
