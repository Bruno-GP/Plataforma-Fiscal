from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import AuthenticatedUser, get_current_user
from app.models.nfe.schemas import (
    IBPTSyncRequest,
    IBPTSyncResponse,
    IBPTSyncUFResultado,
    NCMTributacaoResponse,
)
from app.services.NCM.ibpt_sync_service import IBPTSyncService


router = APIRouter()
ncm_router = APIRouter(prefix="/ncm", tags=["NCM"], dependencies=[Depends(get_current_user)])


@ncm_router.post("/ibpt/sincronizar", response_model=IBPTSyncResponse)
def sincronizar_ibpt(
    request: IBPTSyncRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    try:
        resultados = IBPTSyncService().sincronizar(
            uf=request.uf,
            todas_ufs=request.todas_ufs,
            ncm=request.ncm,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao sincronizar dados do IBPT: {exc}",
        ) from exc

    return IBPTSyncResponse(
        status="ok",
        executado_por=current_user.email,
        total_ufs=len(resultados),
        resultados=[
            IBPTSyncUFResultado(
                uf=item.uf,
                registros_recebidos=item.registros_recebidos,
                catalogo_sincronizado=item.catalogo_sincronizado,
                tributacao_sincronizada=item.tributacao_sincronizada,
            )
            for item in resultados
        ],
    )


@ncm_router.get("/tributacao", response_model=NCMTributacaoResponse)
def consultar_tributacao_ncm(
    codigo: str = Query(..., min_length=2, max_length=20),
    uf: str = Query(..., min_length=2, max_length=2),
    _: AuthenticatedUser = Depends(get_current_user),
):
    try:
        tributacao = IBPTSyncService().obter_tributacao(codigo_ncm=codigo, uf=uf)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not tributacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tributacao IBPT nao encontrada para o NCM/UF informado.",
        )

    return NCMTributacaoResponse(status="ok", **tributacao)


router.include_router(ncm_router)
