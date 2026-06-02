import psycopg
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import require_company_scope
from app.models.reforma_tributaria.schemas import (
  BackfillReformaTributariaResponse,
  ConsultaApuracaoTributariaResponse,
  ConsultaDocumentoFiscalTributosResponse,
  ConsultaItemDocumentoFiscalTributosResponse,
  ConsultaMemoriaCalculoTributariaResponse,
  ConsultaTributosResponse,
)
from app.repositories.reforma_tributaria.backfill_repository import (
  ReformaTributariaBackfillRepository,
)
from app.services.reforma_tributaria.reforma_tributaria_consulta_service import (
  ReformaTributariaConsultaService,
)


logger = logging.getLogger("ReformaTributariaRoutes")
# logger.setLevel(logging.INFO)

router = APIRouter()
reforma_router = APIRouter(
  prefix="/reforma-tributaria",
  tags=["Reforma Tributaria"],
  dependencies=[Depends(require_company_scope)],
)


@reforma_router.get("/tributos", response_model=ConsultaTributosResponse)
def listar_tributos(
  incluir_inativos: bool = Query(default=False),
):
  resultados = ReformaTributariaConsultaService().listar_tributos(
    incluir_inativos=incluir_inativos,
  )

  return ConsultaTributosResponse(
    status="ok",
    total=len(resultados),
    resultados=resultados,
  )


@reforma_router.post("/backfill", response_model=BackfillReformaTributariaResponse)
def backfill_reforma_tributaria(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  origem: str = Query(default="nfe", pattern="^(nfe|sped)$"),
):
  # logger.info("Requisicao de backfill da Reforma recebida: emitente_cnpj=%s origem=%s", emitente_cnpj, origem)
  try:
    resultados = ReformaTributariaBackfillRepository().executar(
      emitente_cnpj=emitente_cnpj,
      origem=origem,
    )
  except psycopg.Error as exc:
    logger.exception("Falha no backfill da Reforma: emitente_cnpj=%s origem=%s", emitente_cnpj, origem)
    raise HTTPException(
      status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
      detail=f"Falha ao executar backfill da Reforma Tributaria: {exc}",
    ) from exc

  # logger.info(
  #   "Backfill da Reforma concluido: emitente_cnpj=%s origem=%s periodos=%s resultados=%s",
  #   emitente_cnpj,
  #   origem,
  #   len(resultados),
  #   resultados,
  # )
  return BackfillReformaTributariaResponse(
    status="ok",
    emitente_cnpj=emitente_cnpj,
    origem=origem,
    periodos_processados=len(resultados),
    resultados=resultados,
  )

@reforma_router.get("/apuracao", response_model=ConsultaApuracaoTributariaResponse)
def listar_apuracoes(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None, ge=1, le=12),
  tributo_codigo: str | None = Query(default=None, min_length=2, max_length=20),
):
  resultados = ReformaTributariaConsultaService().listar_apuracoes(
    emitente_cnpj=emitente_cnpj,
    periodo_ano=periodo_ano,
    periodo_mes=periodo_mes,
    tributo_codigo=tributo_codigo,
  )

  return ConsultaApuracaoTributariaResponse(
    status="ok",
    emitente_cnpj=emitente_cnpj,
    periodo_ano=periodo_ano,
    periodo_mes=periodo_mes,
    total=len(resultados),
    resultados=resultados,
  )


@reforma_router.get(
  "/documentos/{origem_documento}/{documento_id}/tributos",
  response_model=ConsultaDocumentoFiscalTributosResponse,
)
def listar_documento_tributos(
  origem_documento: str,
  documento_id: int,
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
):
  try:
    resultados = ReformaTributariaConsultaService().listar_documento_tributos(
      emitente_cnpj=emitente_cnpj,
      origem_documento=origem_documento,
      documento_id=documento_id,
    )
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=str(exc),
    ) from exc

  return ConsultaDocumentoFiscalTributosResponse(
    status="ok",
    origem_documento=origem_documento,
    documento_id=documento_id,
    total=len(resultados),
    resultados=resultados,
  )


@reforma_router.get(
  "/itens/{origem_item}/{item_id}/tributos",
  response_model=ConsultaItemDocumentoFiscalTributosResponse,
)
def listar_item_tributos(
  origem_item: str,
  item_id: int,
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
):
  try:
    resultados = ReformaTributariaConsultaService().listar_item_tributos(
      emitente_cnpj=emitente_cnpj,
      origem_item=origem_item,
      item_id=item_id,
    )
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=str(exc),
    ) from exc

  return ConsultaItemDocumentoFiscalTributosResponse(
    status="ok",
    origem_item=origem_item,
    item_id=item_id,
    total=len(resultados),
    resultados=resultados,
  )


@reforma_router.get("/memoria-calculo", response_model=ConsultaMemoriaCalculoTributariaResponse)
def listar_memoria_calculo(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None, ge=1, le=12),
  tributo_codigo: str | None = Query(default=None, min_length=2, max_length=20),
  documento_tributo_id: int | None = Query(default=None, ge=1),
  item_tributo_id: int | None = Query(default=None, ge=1),
  limite: int = Query(default=100, ge=1, le=1000),
  offset: int = Query(default=0, ge=0),
):
  service = ReformaTributariaConsultaService()
  resultados = service.listar_memoria_calculo(
    emitente_cnpj=emitente_cnpj,
    periodo_ano=periodo_ano,
    periodo_mes=periodo_mes,
    tributo_codigo=tributo_codigo,
    documento_tributo_id=documento_tributo_id,
    item_tributo_id=item_tributo_id,
    limite=limite,
    offset=offset,
  )
  total = service.contar_memoria_calculo(
    emitente_cnpj=emitente_cnpj,
    periodo_ano=periodo_ano,
    periodo_mes=periodo_mes,
    tributo_codigo=tributo_codigo,
    documento_tributo_id=documento_tributo_id,
    item_tributo_id=item_tributo_id,
  )

  return ConsultaMemoriaCalculoTributariaResponse(
    status="ok",
    emitente_cnpj=emitente_cnpj,
    periodo_ano=periodo_ano,
    periodo_mes=periodo_mes,
    total=total,
    limite=limite,
    offset=offset,
    resultados=resultados,
  )


router.include_router(reforma_router)
