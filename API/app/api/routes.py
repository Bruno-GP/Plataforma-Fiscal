from fastapi import APIRouter
from app.models.schemas import ProcessarNFeRequest, ProcessarNFeResponse
from app.services.process_nfe import ProcessarNFeService

router = APIRouter(prefix="/nfe", tags=["NFe"])

@router.post("/processar", response_model=ProcessarNFeResponse)
def processar_nfe(request: ProcessarNFeRequest):
    return ProcessarNFeService().executar(request)