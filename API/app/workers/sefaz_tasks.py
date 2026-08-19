from __future__ import annotations

import logging

from app.repositories.sefaz.certificados_repository import CertificadosRepository
from app.repositories.sefaz.documentos_repository import DocumentosRepository
from app.services.sefaz.sefaz_fiscal_transport_service import SefazFiscalTransportService
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
    sefaz_backfill_fiscal_task.apply_async(args=[empresa_id, cnpj_titular], queue="sefaz")
    return {
        "status": resultado.status,
        "documentos_novos": resultado.documentos_novos,
        "empresa_id": empresa_id,
        "nsu_inicial": resultado.nsu_inicial,
        "nsu_final": resultado.nsu_final,
        "erro_detalhe": resultado.erro_detalhe,
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
    """Transporta os itens do documento para o banco Fiscal quando elegivel."""
    logger.info(
        "sefaz_documento_novo_evento_recebido",
        extra={"empresa_id": empresa_id, "chave_acesso": chave_acesso},
    )

    documento = DocumentosRepository().obter_por_chave(empresa_id, chave_acesso)
    if documento is None:
        return {"status": "SUCCESS", "motivo": "documento_nao_encontrado"}

    total_marcados = SefazFiscalTransportService().transportar_documentos(
        empresa_id=empresa_id,
        cnpj_empresa=documento["cnpj_emitente"],
        documentos=[documento],
    )
    return {"status": "SUCCESS", "total_marcados": total_marcados}


@celery_app.task(name="sefaz_backfill_fiscal_task")
def sefaz_backfill_fiscal_task(empresa_id: int, cnpj_empresa: str) -> dict:
    """Reprocessa documentos 'emitida' pendentes de transporte para o banco Fiscal."""
    pendentes = DocumentosRepository().listar_pendentes_fiscal(empresa_id)
    total_marcados = SefazFiscalTransportService().transportar_documentos(
        empresa_id=empresa_id,
        cnpj_empresa=cnpj_empresa,
        documentos=pendentes,
    )
    logger.info(
        "sefaz_backfill_fiscal_concluido",
        extra={
            "empresa_id": empresa_id,
            "total_pendentes": len(pendentes),
            "total_marcados": total_marcados,
        },
    )
    return {
        "status": "SUCCESS",
        "total_pendentes": len(pendentes),
        "total_marcados": total_marcados,
    }
