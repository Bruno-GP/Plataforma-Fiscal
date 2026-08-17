from __future__ import annotations

import logging

from app.repositories.sefaz.certificados_repository import CertificadosRepository
from app.services.sefaz.sefaz_distribuicao_service import SefazDistribuicaoService
from app.workers.celery_app import celery_app


logger = logging.getLogger("workers.sefaz")

AMBIENTE_PRODUCAO = 1


def _repositorio_certificados() -> CertificadosRepository:
    return CertificadosRepository()


def _sincronizar_empresa(empresa_id: int, cnpj_titular: str):
    return SefazDistribuicaoService().sincronizar_empresa(
        empresa_id,
        cnpj_titular,
        ambiente=AMBIENTE_PRODUCAO,
    )


@celery_app.task(
    name="sefaz_sync_empresa_task",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def sefaz_sync_empresa_task(empresa_id: int, cnpj_titular: str) -> dict:
    resultado = _sincronizar_empresa(empresa_id, cnpj_titular)
    return {
        "status": resultado.status,
        "documentos_novos": resultado.documentos_novos,
        "empresa_id": empresa_id,
    }


@celery_app.task(name="sefaz_sync_diario_task")
def sefaz_sync_diario_task() -> dict:
    """Dispara uma task por empresa com certificado SEFAZ ativo."""
    certificados = _repositorio_certificados().listar_ativos_com_validade()
    disparados = 0

    for certificado in certificados:
        sefaz_sync_empresa_task.apply_async(
            args=[certificado["empresa_id"], certificado["cnpj_titular"]],
            queue="sefaz",
        )
        disparados += 1

    logger.info("sefaz_sync_diario_disparado", extra={"empresas": disparados})
    return {"status": "SUCCESS", "empresas_disparadas": disparados}


@celery_app.task(name="sefaz_evento_documento_novo_task")
def sefaz_evento_documento_novo_task(empresa_id: int, chave_acesso: str) -> dict:
    """Hook best-effort para reação futura do módulo fiscal/NCM."""
    logger.info(
        "sefaz_documento_novo_evento_recebido",
        extra={"empresa_id": empresa_id, "chave_acesso": chave_acesso},
    )
    return {"status": "SUCCESS"}
