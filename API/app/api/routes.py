from fastapi import APIRouter, Query, HTTPException, status

from app.services.process_nfe import ProcessarNFeService
from app.services.nfe_consulta_service import NFeConsultaService
from app.models.schemas import (
  ConsultaNFeResponse,
  ConsultaKPIResponse,
  ProcessarNFeRequest,
  ProcessarNFeResponse,
)

router = APIRouter()

nfe_router = APIRouter(prefix="/nfe", tags=["NFe"])

# -------------------------
# Processamento
# -------------------------
@nfe_router.post("/processar", response_model=ProcessarNFeResponse)
def processar_nfe(request: ProcessarNFeRequest):
  return ProcessarNFeService().executar(request)

# -------------------------
# Consulta de KPIs (consolidado)
# -------------------------
@nfe_router.get("/kpis", response_model=ConsultaKPIResponse)
def consultar_kpis(
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

  return ConsultaKPIResponse(
    status="ok",
    total=len(resultados),
    resultados=resultados,
  )

# -------------------------
# Consulta de notas (detalhado)
# -------------------------
@nfe_router.get("/notas", response_model=ConsultaNFeResponse)
def consultar_notas(
  emitente_cnpj: str | None = Query(default=None),
  periodo_ano: int | None = Query(default=None, ge=2000, le=2100),
  periodo_mes: int | None = Query(default=None, ge=1, le=12),
  limite: int = Query(default=100, ge=1, le=500),
  offset: int = Query(default=0, ge=0),
):
  # ⚠️ Ainda não existe um service de consulta detalhada de notas no seu código.
  # Mantive a rota separada para o front/Make já ficar com a arquitetura certa.
  raise HTTPException(
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    detail="Consulta detalhada de notas ainda não implementada. Use GET /nfe/kpis para KPIs consolidados.",
  )


router.include_router(nfe_router)