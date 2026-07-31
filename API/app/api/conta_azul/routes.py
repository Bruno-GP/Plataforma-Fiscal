import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.api.shared.company_validation import validar_empresa_conta_azul
from app.core.security import AuthenticatedUser, require_company_scope
from app.models.conta_azul.schemas import ConsultaContaAzulKpisResponse
from app.repositories.conta_azul.integracoes_repository import IntegracoesRepository
from app.services.conta_azul.conta_azul_consulta_service import ContaAzulConsultaService
from app.services.conta_azul.postgres_token_store import PostgresTokenStore, conn_params_conta_azul

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


OAUTH_STATE_TTL_MINUTES = 10


@conta_azul_router.get("/oauth/iniciar")
def iniciar_autorizacao_conta_azul(current_user: AuthenticatedUser = Depends(require_company_scope)):
  """Redireciona pra tela de autorizacao do Conta Azul. Ele depois redireciona
  o usuario pro callback fixo em GET /callback (registrado em app/main.py)."""
  if not current_user.tem_conta_azul:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Usuario nao pertence a uma empresa com Conta Azul habilitado.",
    )

  conta_azul_dir = Path(__file__).resolve().parents[3] / "integracoes" / "conta_azul"
  if str(conta_azul_dir) not in sys.path:
    sys.path.insert(0, str(conta_azul_dir))

  from contaazul.auth import ContaAzulAuth

  client_id = os.environ.get("CONTAAZUL_CLIENT_ID")
  client_secret = os.environ.get("CONTAAZUL_CLIENT_SECRET")
  redirect_uri = os.environ.get("CONTAAZUL_REDIRECT_URI")
  if not all([client_id, client_secret, redirect_uri]):
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail="Credenciais Conta Azul nao configuradas (CONTAAZUL_CLIENT_ID/SECRET/REDIRECT_URI).",
    )

  auth_client = ContaAzulAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    token_store=PostgresTokenStore(current_user.empresa_id),
  )
  url, state = auth_client.build_authorization_url()

  IntegracoesRepository(conn_params_conta_azul()).iniciar_autorizacao(
    current_user.empresa_id,
    state,
    datetime.now(timezone.utc) + timedelta(minutes=OAUTH_STATE_TTL_MINUTES),
  )

  return RedirectResponse(url)


router.include_router(conta_azul_router)
