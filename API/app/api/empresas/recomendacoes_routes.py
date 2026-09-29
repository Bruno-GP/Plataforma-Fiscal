from __future__ import annotations

from functools import lru_cache

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import AuthenticatedUser, get_current_user
from app.models.metas.schemas import (
    IndicadorPerfil,
    IndicadorRecomendacoesEmpresaResponse,
    IndicadorRecomendadoResponse,
)
from app.services.metas.indicador_recommendation_service import (
    EmpresaNaoEncontradaError,
    IndicadorRecommendationService,
)

router = APIRouter(prefix="/empresas/me/recomendacoes-indicadores", tags=["Empresas"])


@lru_cache(maxsize=1)
def get_indicador_recommendation_service() -> IndicadorRecommendationService:
    return IndicadorRecommendationService()


@router.get("", response_model=IndicadorRecomendacoesEmpresaResponse)
def listar_recomendacoes_indicadores(
    perfil: IndicadorPerfil | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: IndicadorRecommendationService = Depends(get_indicador_recommendation_service),
):
    perfil_efetivo = perfil or (IndicadorPerfil.SPED if current_user.tem_sped else IndicadorPerfil.XML)

    try:
        resultado = service.recomendar_para_empresa(current_user.empresa_id, perfil=perfil_efetivo.value)
    except EmpresaNaoEncontradaError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa da sessao atual nao encontrada.",
        ) from exc
    except psycopg.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponivel.",
        ) from exc

    return IndicadorRecomendacoesEmpresaResponse(
        empresa_id=resultado.empresa_id,
        cnae_fiscal=resultado.cnae_fiscal,
        cnae_fiscal_descricao=resultado.cnae_fiscal_descricao,
        segmento_sugerido=resultado.segmento_sugerido,
        segmento_nome=resultado.segmento_nome,
        fonte=resultado.fonte,
        confianca=resultado.confianca,
        motivo=resultado.motivo,
        indicadores=[
            IndicadorRecomendadoResponse(
                indicador_id=indicador.indicador_id,
                chave=indicador.chave,
                nome=indicador.nome,
                unidade=indicador.unidade,
                direcao_boa=indicador.direcao_boa,
                perfil=indicador.perfil,
                prioridade=indicador.prioridade,
                status=indicador.status,
                motivo=indicador.motivo,
                obrigatorio=indicador.obrigatorio,
                score=indicador.score,
            )
            for indicador in resultado.indicadores
        ],
    )
