from __future__ import annotations

import logging
import time

from app.models.jobs.schemas import JobStatus
from app.repositories.jobs_repository import JobsRepository
from app.services.nfe.process_nfe import ProcessarNFeService
from app.services.nfe.xml_importacao_service import XMLImportacaoService
from app.workers.celery_app import celery_app

logger = logging.getLogger("workers.nfe")


@celery_app.task(
    name="processar_nfe_importados_task",
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def processar_nfe_importados_task(job_id: str, payload: dict) -> dict:
    repository = JobsRepository()
    started_at = time.perf_counter()
    cnpj_emitente = str(payload.get("cnpj_emitente") or "")
    logger.info("job_started", extra={"job_id": job_id, "tipo_job": "NFE_PROCESSAMENTO_IMPORTADOS", "etapa": "start"})
    repository.mark_running(job_id, mensagem="Processando XMLs importados")

    try:
        service_importacao = XMLImportacaoService()
        xmls_importados = service_importacao.listar_xmls_importados_nao_processados(cnpj_emitente)
        repository.update_progress(job_id, total_itens=len(xmls_importados), itens_processados=0)
        if not xmls_importados:
            raise ValueError("Nenhum XML pendente encontrado para o CNPJ informado.")

        resposta, ids_processados = ProcessarNFeService().executar_xmls_importados(
            cnpj_emitente=cnpj_emitente,
            xmls_importados=xmls_importados,
        )
        if resposta.status != "processado":
            erro = "; ".join(str(item.get("mensagem", item)) for item in resposta.erros) or "Falha no processamento NFe."
            raise RuntimeError(erro)

        service_importacao.marcar_como_processados(ids_processados)
        repository.update_progress(
            job_id,
            total_itens=len(xmls_importados),
            itens_processados=len(ids_processados),
            mensagem="XMLs importados processados",
        )
        repository.update_status(job_id, JobStatus.SUCCESS, mensagem="Processamento NFe concluido")
        duracao_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "job_completed",
            extra={
                "job_id": job_id,
                "tipo_job": "NFE_PROCESSAMENTO_IMPORTADOS",
                "status": "SUCCESS",
                "duracao_ms": duracao_ms,
                "total_itens": len(xmls_importados),
                "itens_processados": len(ids_processados),
            },
        )
        return {"status": "SUCCESS", "job_id": job_id}
    except Exception as exc:
        repository.update_status(job_id, JobStatus.FAILED, mensagem="Falha no processamento NFe", erro=str(exc))
        logger.exception(
            "job_failed",
            extra={"job_id": job_id, "tipo_job": "NFE_PROCESSAMENTO_IMPORTADOS", "status": "FAILED", "erro": str(exc)},
        )
        raise
