from fastapi import APIRouter
from app.services.process_nfe import ProcessarNFeService
from app.models.schemas import (
    ProcessarNFeRequest, 
    ProcessarNFeResponse,
    ConnSQLResponse
)
from app.services.db_conn import ConnPostgresService

router = APIRouter(prefix="/nfe", tags=["NFe"])
#router = APIRouter()

nfe_router = APIRouter(prefix="/nfe", tags=["NFe"])

@router.post("/processar", response_model=ProcessarNFeResponse)
def processar_nfe(request: ProcessarNFeRequest):
    return ProcessarNFeService().executar(request)

infra_router = APIRouter(prefix="/infra", tags=["Infra"])

@infra_router.get("/postgres/testar", response_model=ConnSQLResponse)
def testar_conexao_postgres():
  return ConnPostgresService().executar()

router.include_router(nfe_router)
router.include_router(infra_router)