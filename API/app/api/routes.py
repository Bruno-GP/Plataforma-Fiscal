from fastapi import APIRouter, Query
from app.services.process_nfe import ProcessarNFeService
from app.models.schemas import (
  ConsultaNFeResponse,
  ProcessarNFeRequest, 
  ProcessarNFeResponse,
  ConnSQLResponse
)
from app.services.nfe_consulta_service import NFeConsultaService

router = APIRouter()

nfe_router = APIRouter(prefix="/nfe", tags=["NFe"])

@nfe_router.post("/processar", response_model=ProcessarNFeResponse)
def processar_nfe(request: ProcessarNFeRequest):
  return ProcessarNFeService().executar(request)

@router.get("/notas", response_model=ConsultaNFeResponse)
def consultar_notas(
  emitente_cnpj: str | None = Query(default=None),
  periodo_ano: int | None = Query(default=None, ge=2000, le=2100),
  periodo_mes: int | None = Query(default=None, ge=1, le=12),
  limite: int = Query(default=100, ge=1, le=500),
  offset: int = Query(default=0, ge=0),
):
  resultados = NFeConsultaService().listar_kpis(
    emitente_cnpj=emitente_cnpj,
    periodo_ano=periodo_ano,
    periodo_mes=periodo_mes,
    limite=limite,
    offset=offset,
  )
  return ConsultaNFeResponse(
    status="ok",
    total=len(resultados),
    resultados=resultados,
  )

router.include_router(nfe_router)