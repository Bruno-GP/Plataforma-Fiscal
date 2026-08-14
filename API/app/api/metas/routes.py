from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import AuthenticatedUser, get_current_user
from app.models.metas.schemas import (
    AnaliseMetaResponse,
    IndicadorHistoricoPontoResponse,
    MetaCreateRequest,
    MetaListResponse,
    MetaResponse,
    MetaUpdateRequest,
)
from app.repositories.metas.metas_historico_repository import MetasHistoricoRepository
from app.services.metas.metas_service import IndicadorInvalidoError, MetaNaoEncontradaError, MetasService
from app.services.nfe.empresa_service import normalizar_cnpj

router = APIRouter(prefix="/metas", tags=["Metas"])

_metas_service: MetasService | None = None


def get_metas_service() -> MetasService:
    global _metas_service
    if _metas_service is None:
        _metas_service = MetasService()
    return _metas_service


def _valor_realizado_atual(indicador_chave: str, periodo_inicio: date, periodo_fim: date, cnpj: str) -> Decimal:
    linhas = MetasHistoricoRepository().agregar_por_empresa(normalizar_cnpj(cnpj))
    for linha in linhas:
        periodo_referencia = linha["periodo_referencia"]
        if periodo_inicio <= periodo_referencia <= periodo_fim and indicador_chave in linha:
            return Decimal(str(linha[indicador_chave]))
    return Decimal("0")


@router.post("", response_model=MetaResponse, status_code=status.HTTP_201_CREATED)
def criar_meta(
    payload: MetaCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: MetasService = Depends(get_metas_service),
):
    try:
        meta = service.criar(
            empresa_id=current_user.empresa_id,
            indicador_id=payload.indicador_id,
            titulo=payload.titulo,
            descricao=payload.descricao,
            valor_alvo=payload.valor_alvo,
            tipo_meta=payload.tipo_meta.value,
            periodo_tipo=payload.periodo_tipo.value,
            periodo_inicio=payload.periodo_inicio,
            periodo_fim=payload.periodo_fim,
            criado_por=current_user.login_id,
        )
    except IndicadorInvalidoError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MetaResponse(**meta)


@router.get("", response_model=MetaListResponse)
def listar_metas(
    status_filter: str | None = Query(default=None, alias="status"),
    indicador_id: int | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: MetasService = Depends(get_metas_service),
):
    resultados = service.listar(current_user.empresa_id, status=status_filter, indicador_id=indicador_id)
    return MetaListResponse(total=len(resultados), resultados=[MetaResponse(**meta) for meta in resultados])


@router.get("/{meta_id}", response_model=MetaResponse)
def obter_meta(
    meta_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: MetasService = Depends(get_metas_service),
):
    try:
        meta = service.obter(meta_id, current_user.empresa_id)
    except MetaNaoEncontradaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta nao encontrada.") from exc
    return MetaResponse(**meta)


@router.patch("/{meta_id}", response_model=MetaResponse)
def atualizar_meta(
    meta_id: int,
    payload: MetaUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: MetasService = Depends(get_metas_service),
):
    campos = {
        chave: (valor.value if hasattr(valor, "value") else valor)
        for chave, valor in payload.model_dump(exclude_unset=True).items()
    }
    try:
        meta = service.atualizar(meta_id, current_user.empresa_id, campos)
    except MetaNaoEncontradaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta nao encontrada.") from exc
    return MetaResponse(**meta)


@router.delete("/{meta_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancelar_meta(
    meta_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: MetasService = Depends(get_metas_service),
):
    try:
        service.cancelar(meta_id, current_user.empresa_id)
    except MetaNaoEncontradaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta nao encontrada.") from exc


@router.get("/{meta_id}/analise", response_model=AnaliseMetaResponse)
def analisar_meta_endpoint(
    meta_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: MetasService = Depends(get_metas_service),
):
    try:
        meta = service.obter(meta_id, current_user.empresa_id)
    except MetaNaoEncontradaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta nao encontrada.") from exc

    indicador = service.indicadores_repository.obter_por_id(meta["indicador_id"])
    if not indicador:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Indicador nao encontrado.")

    valor_atual = _valor_realizado_atual(
        indicador["chave"],
        meta["periodo_inicio"],
        meta["periodo_fim"],
        current_user.cnpj,
    )

    analise = service.analisar(meta_id, current_user.empresa_id, valor_realizado_atual=valor_atual)

    return AnaliseMetaResponse(
        meta_id=meta_id,
        valor_alvo=analise.valor_alvo,
        valor_realizado_atual=analise.valor_realizado_atual,
        percentual_atingido=analise.percentual_atingido,
        tempo_decorrido_pct=analise.tempo_decorrido_pct,
        status_ritmo=analise.status_ritmo.value,
        tendencia=analise.tendencia.value,
        media_periodos_anteriores=analise.media_periodos_anteriores,
        mediana_periodos_anteriores=analise.mediana_periodos_anteriores,
        desvio_padrao_periodos_anteriores=analise.desvio_padrao_periodos_anteriores,
        variacao_vs_media_pct=analise.variacao_vs_media_pct,
        diagnostico=analise.diagnostico,
        serie_historica=[
            IndicadorHistoricoPontoResponse(periodo=p.periodo, valor=p.valor)
            for p in analise.serie_historica
        ],
        projecao_fim_periodo=analise.projecao_fim_periodo,
        comparativo_ano_anterior_pct=analise.comparativo_ano_anterior_pct,
    )
