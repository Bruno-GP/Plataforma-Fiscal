from fastapi import APIRouter, HTTPException, status
import psycopg

from app.core.security import AuthenticatedUser, create_access_token
from app.models.nfe.auth.schemas import (
    LoginCadastroRequest,
    LoginCadastroResponse,
    LoginRequest,
    LoginResponse,
)
from app.services.nfe.auth.login_service import LoginService

router = APIRouter()

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


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


@auth_router.post(
    "/registrar",
    response_model=LoginCadastroResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar_login(request: LoginCadastroRequest):
    try:
        resultado = LoginService().registrar(
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

    return LoginCadastroResponse(
        status="cadastrado",
        login_id=user.login_id,
        empresa_id=user.empresa_id,
        cnpj=user.cnpj,
        email=user.email,
        empresa_nome=user.empresa_nome,
        tem_sped=user.tem_sped,
        access_token=access_token,
        token_type="Bearer",
        expires_in=expires_in,
    )


@auth_router.post("/entrar", response_model=LoginResponse)
def autenticar_login(request: LoginRequest):
    try:
        resultado = LoginService().autenticar(
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

    return LoginResponse(
        status="ok",
        login_id=user.login_id,
        empresa_id=user.empresa_id,
        cnpj=user.cnpj,
        email=user.email,
        empresa_nome=user.empresa_nome,
        tem_sped=user.tem_sped,
        access_token=access_token,
        token_type="Bearer",
        expires_in=expires_in,
    )


router.include_router(auth_router)
