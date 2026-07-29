from fastapi import APIRouter, Depends, Query

from app.api.shared.company_validation import validar_empresa_conta_azul
from app.core.security import AuthenticatedUser, require_company_scope
from app.models.conta_azul.schemas import ConsultaContaAzulKpisResponse
from app.services.conta_azul.conta_azul_consulta_service import ContaAzulConsultaService

router = APIRouter()
conta_azul_router = APIRouter(
  prefix="/conta-azul", tags=["Conta Azul"], dependencies=[Depends(require_company_scope)]
)


@conta_azul_router.get("/analise/kpis", response_model=ConsultaContaAzulKpisResponse)
def consultar_kpis_conta_azul(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  limite: int = Query(default=12, ge=1, le=120),
  current_user: AuthenticatedUser = Depends(require_company_scope),
):
  validar_empresa_conta_azul(emitente_cnpj)

  resultados = ContaAzulConsultaService().listar_kpis(current_user.empresa_id, limite)

  return ConsultaContaAzulKpisResponse(status="ok", resultados=resultados)


router.include_router(conta_azul_router)
