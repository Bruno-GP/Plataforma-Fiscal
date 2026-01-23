from fastapi import APIRouter, Query, HTTPException, status

from app.services.nfe.process_nfe import ProcessarNFeService
from app.services.nfe.nfe_consulta_service import NFeConsultaService
from app.models.nfe.schemas import (
  ComparativoKPIMensalResponse,
  ConsultaNFeResponse,
  ConsultaKPIResponse,
  ProcessarNFeRequest,
  ProcessarNFeResponse
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
# Comparativo mensal de KPIs
# -------------------------
@nfe_router.get(
  "/kpis/comparativo",
  response_model=ComparativoKPIMensalResponse,
)
def comparar_kpis_mensal(
  emitente_cnpj: str | None = Query(default=None),
  periodo_ano: int = Query(..., ge=2000, le=2100),
  periodo_mes: int = Query(..., ge=1, le=12),
  periodo_anterior_ano: int | None = Query(default=None, ge=2000, le=2100),
  periodo_anterior_mes: int | None = Query(default=None, ge=1, le=12),
):
  if periodo_anterior_ano is None or periodo_anterior_mes is None:
    if periodo_mes == 1:
      periodo_anterior_mes = 12
      periodo_anterior_ano = periodo_ano - 1
    else:
      periodo_anterior_mes = periodo_mes - 1
      periodo_anterior_ano = periodo_ano

  kpis = NFeConsultaService().comparar_kpis_mensal(
    emitente_cnpj=emitente_cnpj,
    periodo_ano=periodo_ano,
    periodo_mes=periodo_mes,
    periodo_anterior_ano=periodo_anterior_ano,
    periodo_anterior_mes=periodo_anterior_mes,
  )

  if not kpis:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=(
        "KPIs não encontrados para o período atual e/ou "
        "o período anterior."
      ),
    )

  return ComparativoKPIMensalResponse(
    status="ok",
    periodo_atual_ano=periodo_ano,
    periodo_atual_mes=periodo_mes,
    periodo_anterior_ano=periodo_anterior_ano,
    periodo_anterior_mes=periodo_anterior_mes,
    emitente_cnpj=emitente_cnpj,
    kpis=kpis,
  )

# -------------------------
# Comparativo mensal de KPIs (auto)
# -------------------------
@nfe_router.get(
  "/kpis/comparativo/atual",
  response_model=ComparativoKPIMensalResponse,
)
def comparar_kpis_mensal_atual(
  emitente_cnpj: str | None = Query(default=None),
):
  service = NFeConsultaService()
  try:
    periodo_ano, periodo_mes = service.obter_ultimo_periodo(emitente_cnpj)
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=str(exc),
    ) from exc

  kpis = service.comparar_kpis_mensal(
    emitente_cnpj=emitente_cnpj,
    periodo_ano=periodo_ano,
    periodo_mes=periodo_mes,
  )

  if not kpis:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=(
        "KPIs não encontrados para o período atual e/ou "
        "o período anterior."
      ),
    )

  if periodo_mes == 1:
    periodo_anterior_mes = 12
    periodo_anterior_ano = periodo_ano - 1
  else:
    periodo_anterior_mes = periodo_mes - 1
    periodo_anterior_ano = periodo_ano

  return ComparativoKPIMensalResponse(
    status="ok",
    periodo_atual_ano=periodo_ano,
    periodo_atual_mes=periodo_mes,
    periodo_anterior_ano=periodo_anterior_ano,
    periodo_anterior_mes=periodo_anterior_mes,
    emitente_cnpj=emitente_cnpj,
    kpis=kpis,
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