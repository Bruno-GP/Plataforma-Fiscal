from fastapi import APIRouter, HTTPException, status
import psycopg

from app.models.nfe.auth.schemas import (
    LoginCadastroRequest,
    LoginCadastroResponse,
    LoginRequest,
    LoginResponse,
)
from app.services.nfe.auth.login_service import LoginService

router = APIRouter()

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


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

    return LoginCadastroResponse(
        status="cadastrado",
        login_id=resultado.login_id,
        empresa_id=resultado.empresa_id,
        cnpj=resultado.cnpj,
        email=resultado.email,
        empresa_nome=resultado.empresa_nome,
        tem_sped=resultado.tem_sped,
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

    return LoginResponse(
        status="ok",
        login_id=resultado.login_id,
        empresa_id=resultado.empresa_id,
        cnpj=resultado.cnpj,
        email=resultado.email,
        empresa_nome=resultado.empresa_nome,
        tem_sped=resultado.tem_sped,
    )


router.include_router(auth_router)