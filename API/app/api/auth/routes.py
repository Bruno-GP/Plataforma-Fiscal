from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Response, status
import psycopg

from app.core.audit import log_security_event
from app.core.security import (
    AuthenticatedUser,
    clear_auth_cookie,
    create_access_token,
    get_current_user,
    get_session_expires_in,
    set_auth_cookie,
)
from app.models.nfe.auth.schemas import (
    LoginCadastroRequest,
    LoginCadastroResponse,
    LoginRequest,
    LoginResponse,
    SessaoResponse,
)
from app.services.nfe.auth.login_service import LoginService

router = APIRouter()
auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@lru_cache(maxsize=1)
def get_login_service() -> LoginService:
    return LoginService()


def _build_auth_payload(resultado) -> tuple[AuthenticatedUser, str, int]:
    user = AuthenticatedUser(
        login_id=resultado.login_id,
        empresa_id=resultado.empresa_id,
        cnpj=resultado.cnpj,
        email=resultado.email,
        empresa_nome=resultado.empresa_nome,
        tem_sped=resultado.tem_sped,
    )
    access_token, expires_in = create_access_token(user)
    return user, access_token, expires_in


def _build_response_payload(
    user: AuthenticatedUser,
    expires_in: int,
    status_value: str,
    access_token: str | None = None,
) -> dict:
    payload = {
        "status": status_value,
        "login_id": user.login_id,
        "empresa_id": user.empresa_id,
        "cnpj": user.cnpj,
        "email": user.email,
        "empresa_nome": user.empresa_nome,
        "tem_sped": user.tem_sped,
        "expires_in": expires_in,
    }
    if access_token is not None:
        payload["access_token"] = access_token
    return payload


@auth_router.post(
    "/registrar",
    response_model=LoginCadastroResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar_login(request: LoginCadastroRequest, response: Response):
    try:
        resultado = get_login_service().registrar(
            empresa_nome=request.empresa_nome,
            email=request.email,
            senha=request.senha,
            cnpj=request.cnpj,
            tem_sped=request.tem_sped,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except psycopg.OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de autenticação indisponível no momento.",
        ) from exc

    user, access_token, expires_in = _build_auth_payload(resultado)
    set_auth_cookie(response, access_token, expires_in)
    return LoginCadastroResponse(**_build_response_payload(user, expires_in, "ok", access_token))


@auth_router.post("/entrar", response_model=LoginResponse)
def autenticar_login(request: LoginRequest, response: Response):
    try:
        resultado = get_login_service().autenticar(
            email=request.email,
            senha=request.senha,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except psycopg.OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de autenticação indisponível no momento.",
        ) from exc

    user, access_token, expires_in = _build_auth_payload(resultado)
    set_auth_cookie(response, access_token, expires_in)
    return LoginResponse(**_build_response_payload(user, expires_in, "ok", access_token))


@auth_router.get("/sessao", response_model=SessaoResponse)
def obter_sessao_atual(current_user: AuthenticatedUser = Depends(get_current_user)):
    return SessaoResponse(**_build_response_payload(current_user, get_session_expires_in(), "ok"))


@auth_router.post("/sair", status_code=status.HTTP_204_NO_CONTENT)
def sair(response: Response):
    clear_auth_cookie(response)
    log_security_event("logout", outcome="success", reason="user_logout")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


router.include_router(auth_router)
