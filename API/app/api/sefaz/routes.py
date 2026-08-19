from __future__ import annotations

import base64
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.core.security import AuthenticatedUser, require_company_scope
from app.domain.sefaz.periodo import intervalo_do_ano
from app.models.sefaz.schemas import (
    CertificadoStatusResponse,
    ManifestacaoRequest,
    ManifestacaoResponse,
    SefazDocumentoDetalheResponse,
    SefazDocumentoListResponse,
    SefazDocumentoResponse,
    SefazSyncLogListResponse,
    SefazSyncLogResponse,
    SefazSyncResponse,
    SefazSyncStatusResponse,
)
from app.repositories.sefaz.documentos_repository import DocumentosRepository
from app.repositories.sefaz.sync_log_repository import SyncLogRepository
from app.services.sefaz.certificado_service import CertificadoInvalidoError, CertificadoService
from app.services.sefaz.manifestacao_destinatario_service import (
    DocumentoNaoPertenceEmpresaError,
    ManifestacaoDestinatarioService,
    ManifestacaoInvalidaError,
)
from app.workers.celery_app import celery_app


router = APIRouter()
sefaz_router = APIRouter(prefix="/sefaz", tags=["SEFAZ"], dependencies=[Depends(require_company_scope)])
SEFAZ_SYNC_COOLDOWN = timedelta(hours=1)


def _date_response(valor):
    if isinstance(valor, datetime):
        return valor.date()
    return valor


def _documento_response(documento: dict) -> SefazDocumentoResponse:
    return SefazDocumentoResponse(
        id=documento["id"],
        chave_acesso=documento["chave_acesso"],
        tipo_documento=documento["tipo_documento"],
        direcao=documento["direcao"],
        cnpj_emitente=documento["cnpj_emitente"],
        cnpj_destinatario=documento.get("cnpj_destinatario"),
        nsu=documento["nsu"],
        data_emissao=_date_response(documento.get("data_emissao")),
        valor_total=documento.get("valor_total"),
        situacao=documento.get("situacao"),
        manifestacao_status=documento.get("manifestacao_status"),
        criado_em=documento.get("criado_em"),
        atualizado_em=documento.get("atualizado_em"),
        processado_fiscal_em=documento.get("processado_fiscal_em"),
    )


def _sync_log_response(sync_log: dict) -> SefazSyncLogResponse:
    return SefazSyncLogResponse(
        id=sync_log["id"],
        empresa_id=sync_log["empresa_id"],
        iniciado_em=sync_log["iniciado_em"],
        finalizado_em=sync_log.get("finalizado_em"),
        documentos_novos=sync_log["documentos_novos"],
        nsu_inicial=sync_log.get("nsu_inicial"),
        nsu_final=sync_log.get("nsu_final"),
        status=sync_log["status"],
        erro_detalhe=sync_log.get("erro_detalhe"),
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _sync_status_response(empresa_id: int, *, now: datetime | None = None) -> SefazSyncStatusResponse:
    now = now or _utc_now()
    ultima_sync = SyncLogRepository().obter_ultimo_sucesso_com_documentos(empresa_id)
    if not ultima_sync:
        return SefazSyncStatusResponse(disponivel=True)

    finalizado_em = ultima_sync["finalizado_em"]
    if finalizado_em.tzinfo is None:
        finalizado_em = finalizado_em.replace(tzinfo=timezone.utc)

    bloqueado_ate = finalizado_em + SEFAZ_SYNC_COOLDOWN
    segundos_restantes = max(0, int((bloqueado_ate - now).total_seconds()))

    return SefazSyncStatusResponse(
        disponivel=segundos_restantes == 0,
        bloqueado_ate=bloqueado_ate,
        segundos_restantes=segundos_restantes,
        ultima_sincronizacao_com_notas_em=finalizado_em,
        documentos_novos_ultima_sync=ultima_sync["documentos_novos"],
    )


@sefaz_router.post("/certificados", response_model=CertificadoStatusResponse)
async def cadastrar_certificado(
    arquivo: UploadFile = File(...),
    senha: str = Form(...),
    current_user: AuthenticatedUser = Depends(require_company_scope),
):
    nome_arquivo = Path(arquivo.filename or "").name
    if not nome_arquivo.lower().endswith((".pfx", ".p12")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie um certificado .pfx ou .p12.",
        )

    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo do certificado esta vazio.",
        )
    if len(conteudo) > 10_000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O certificado enviado excede o limite de 10000 bytes.",
        )

    try:
        status_certificado = CertificadoService().cadastrar(
            current_user.empresa_id,
            conteudo,
            senha,
            current_user.cnpj,
        )
    except CertificadoInvalidoError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return CertificadoStatusResponse.model_validate(status_certificado, from_attributes=True)


@sefaz_router.get("/certificados/status", response_model=CertificadoStatusResponse)
def obter_status_certificado(current_user: AuthenticatedUser = Depends(require_company_scope)):
    status_certificado = CertificadoService().status(current_user.empresa_id)
    return CertificadoStatusResponse.model_validate(status_certificado, from_attributes=True)


@sefaz_router.post("/sync", response_model=SefazSyncResponse, status_code=status.HTTP_202_ACCEPTED)
def iniciar_sync(current_user: AuthenticatedUser = Depends(require_company_scope)):
    sync_status = _sync_status_response(current_user.empresa_id)
    if not sync_status.disponivel:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"A sincronizacao SEFAZ estara disponivel novamente em {sync_status.segundos_restantes} segundos.",
            headers={"Retry-After": str(sync_status.segundos_restantes)},
        )

    celery_app.send_task(
        "sefaz_sync_empresa_task",
        args=[current_user.empresa_id, current_user.cnpj],
        queue="sefaz",
    )
    return SefazSyncResponse(
        status="accepted",
        message="Sincronizacao SEFAZ enfileirada com sucesso.",
        empresa_id=current_user.empresa_id,
    )


@sefaz_router.get("/sync-status", response_model=SefazSyncStatusResponse)
def obter_sync_status(current_user: AuthenticatedUser = Depends(require_company_scope)):
    return _sync_status_response(current_user.empresa_id)


@sefaz_router.get("/documentos", response_model=SefazDocumentoListResponse)
def listar_documentos(
    direcao: str | None = Query(default=None),
    situacao: str | None = Query(default=None),
    manifestacao_pendente: bool | None = Query(default=None),
    ano: int | None = Query(default=None, ge=2000, le=2100),
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: AuthenticatedUser = Depends(require_company_scope),
):
    if ano is not None and (data_inicio is not None or data_fim is not None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nao e possivel combinar 'ano' com 'data_inicio'/'data_fim'.",
        )
    if ano is not None:
        data_inicio, data_fim = intervalo_do_ano(ano)

    total, documentos = DocumentosRepository().listar(
        empresa_id=current_user.empresa_id,
        direcao=direcao,
        situacao=situacao,
        manifestacao_pendente=manifestacao_pendente,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limit=limit,
        offset=offset,
    )
    return SefazDocumentoListResponse(
        total=total,
        limit=limit,
        offset=offset,
        resultados=[_documento_response(documento) for documento in documentos],
    )


@sefaz_router.get("/documentos/{documento_id}", response_model=SefazDocumentoDetalheResponse)
def obter_documento(documento_id: int, current_user: AuthenticatedUser = Depends(require_company_scope)):
    documento = DocumentosRepository().obter_por_id(current_user.empresa_id, documento_id)
    if documento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento nao encontrado.",
        )

    xml_armazenado = documento.get("xml_armazenado")
    xml_base64 = None
    if xml_armazenado:
        if hasattr(xml_armazenado, "tobytes"):
            xml_armazenado = xml_armazenado.tobytes()
        elif not isinstance(xml_armazenado, (bytes, bytearray)):
            xml_armazenado = bytes(xml_armazenado)
        xml_base64 = base64.b64encode(bytes(xml_armazenado)).decode("ascii")

    return SefazDocumentoDetalheResponse(
        **_documento_response(documento).model_dump(),
        xml_armazenado_base64=xml_base64,
    )


@sefaz_router.post("/documentos/{documento_id}/manifestacao", response_model=ManifestacaoResponse)
def manifestar_documento(
    documento_id: int,
    payload: ManifestacaoRequest,
    current_user: AuthenticatedUser = Depends(require_company_scope),
):
    try:
        resultado = ManifestacaoDestinatarioService().manifestar(
            current_user.empresa_id,
            documento_id,
            payload.tipo_manifestacao,
        )
    except DocumentoNaoPertenceEmpresaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ManifestacaoInvalidaError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ManifestacaoResponse.model_validate(resultado, from_attributes=True)


@sefaz_router.get("/sync-log", response_model=SefazSyncLogListResponse)
def listar_sync_log(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: AuthenticatedUser = Depends(require_company_scope),
):
    total, itens = SyncLogRepository().listar(
        current_user.empresa_id,
        limit=limit,
        offset=offset,
    )
    return SefazSyncLogListResponse(
        total=total,
        limit=limit,
        offset=offset,
        resultados=[_sync_log_response(item) for item in itens],
    )


router.include_router(sefaz_router)
