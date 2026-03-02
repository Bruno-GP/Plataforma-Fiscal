from fastapi import APIRouter

from app.models.sped.schemas import ProcessarSpedFiscalRequest, ProcessarSpedFiscalResponse
from app.services.sped.sped_process_service import ProcessarSpedFiscalService

router = APIRouter()
sped_router = APIRouter(prefix="/sped", tags=["SPED Fiscal"])

@sped_router.post("/processar", response_model=ProcessarSpedFiscalResponse)
def processar_sped_fiscal(request: ProcessarSpedFiscalRequest):
  return ProcessarSpedFiscalService().executar(request)

router.include_router(sped_router)