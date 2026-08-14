from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.security import AuthenticatedUser, get_current_user
from app.models.metas.schemas import (
    IndicadorHistoricoPontoResponse,
    IndicadorHistoricoResponse,
    IndicadorListResponse,
    IndicadorResponse,
)
from app.repositories.metas.indicadores_repository import IndicadoresRepository

router = APIRouter(prefix="/indicadores", tags=["Indicadores"])

_indicadores_repository: IndicadoresRepository | None = None


def get_indicadores_repository() -> IndicadoresRepository:
    global _indicadores_repository
    if _indicadores_repository is None:
        _indicadores_repository = IndicadoresRepository()
    return _indicadores_repository


@router.get("", response_model=IndicadorListResponse)
def listar_indicadores(
    perfil: str = Query(default="xml"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: IndicadoresRepository = Depends(get_indicadores_repository),
):
    resultados = repository.listar(perfil=perfil)
    return IndicadorListResponse(resultados=[IndicadorResponse(**item) for item in resultados])


@router.get("/{indicador_id}/historico", response_model=IndicadorHistoricoResponse)
def historico_indicador(
    indicador_id: int,
    meses: int = Query(default=12, ge=1, le=36),
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: IndicadoresRepository = Depends(get_indicadores_repository),
):
    resultados = repository.historico(empresa_id=current_user.empresa_id, indicador_id=indicador_id, meses=meses)
    return IndicadorHistoricoResponse(
        indicador_id=indicador_id,
        resultados=[IndicadorHistoricoPontoResponse(periodo=item["periodo"], valor=item["valor"]) for item in resultados],
    )
