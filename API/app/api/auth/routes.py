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
    CompanyProfileResponse,
    LoginCadastroRequest,
    LoginCadastroResponse,
    LoginRequest,
    LoginResponse,
    UpdatePasswordRequest,
    UpdatePasswordResponse,
    SessaoResponse,
)
from app.services.company_profile_service import CompanyProfileService
from app.services.Municipios.municipios_catalog_service import MunicipiosCatalogService
from app.services.nfe.auth.login_service import LoginService
from app.services.nfe.empresa_service import EmpresaService
from app.services.nfe.xml_importacao_service import XMLImportacaoService

router = APIRouter()
auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@lru_cache(maxsize=1)
def get_login_service() -> LoginService:
    return LoginService()


@lru_cache(maxsize=1)
def get_company_profile_service() -> CompanyProfileService:
    return CompanyProfileService()


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


def _obter_tem_xml_importado_valido(cnpj: str) -> bool:
    return XMLImportacaoService().empresa_tem_xml_importado_valido(cnpj)


def _validar_localidade_cadastro(
    estado: str | None,
    cidade: str | None,
    municipio_id: str | None = None,
    codigo_ibge: str | None = None,
) -> None:
    estado_bruto = (estado or "").strip()
    uf_normalizada = MunicipiosCatalogService.normalizar_uf(estado)
    cidade_normalizada = (cidade or "").strip()
    municipio_catalogo = MunicipiosCatalogService.resolver_municipio(
        uf=uf_normalizada,
        nome=cidade_normalizada,
        municipio_id=municipio_id,
        codigo_ibge=codigo_ibge,
    )

    if estado_bruto and not uf_normalizada:
        raise ValueError("UF informada precisa ter duas letras e existir no catalogo de municipios.")

    if cidade_normalizada and not uf_normalizada:
        raise ValueError("Informe uma UF valida antes da cidade.")

    if cidade_normalizada and not municipio_catalogo:
        raise ValueError("UF e cidade informadas precisam existir no catalogo de municipios.")

    if uf_normalizada and not cidade_normalizada:
        ufs_disponiveis = MunicipiosCatalogService.listar_ufs(busca=uf_normalizada)
        if not ufs_disponiveis:
            raise ValueError("UF informada precisa existir no catalogo de municipios.")


def _build_response_payload(
    user: AuthenticatedUser,
    expires_in: int,
    status_value: str,
    access_token: str | None = None,
    tem_xml_importado_valido: bool = False,
) -> dict:
    payload = {
        "status": status_value,
        "login_id": user.login_id,
        "empresa_id": user.empresa_id,
        "cnpj": user.cnpj,
        "email": user.email,
        "empresa_nome": user.empresa_nome,
        "tem_sped": user.tem_sped,
        "tem_xml_importado_valido": tem_xml_importado_valido,
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
        _validar_localidade_cadastro(
            request.estado,
            request.cidade,
            request.municipio_id,
            request.codigo_ibge,
        )
        resultado = get_login_service().registrar(
            empresa_nome=request.empresa_nome,
            email=request.email,
            senha=request.senha,
            cnpj=request.cnpj,
            tem_sped=request.tem_sped,
            estado=request.estado,
            cidade=request.cidade,
        )
        EmpresaService().atualizar_localidade(
            cnpj_emitente=resultado.cnpj,
            estado=request.estado,
            cidade=request.cidade,
            municipio_id=request.municipio_id,
            codigo_ibge=request.codigo_ibge,
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
    return LoginCadastroResponse(
        **_build_response_payload(
            user,
            expires_in,
            "ok",
            access_token,
            tem_xml_importado_valido=_obter_tem_xml_importado_valido(user.cnpj),
        )
    )


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
    return LoginResponse(
        **_build_response_payload(
            user,
            expires_in,
            "ok",
            access_token,
            tem_xml_importado_valido=_obter_tem_xml_importado_valido(user.cnpj),
        )
    )


@auth_router.get("/sessao", response_model=SessaoResponse)
def obter_sessao_atual(current_user: AuthenticatedUser = Depends(get_current_user)):
    return SessaoResponse(
        **_build_response_payload(
            current_user,
            get_session_expires_in(),
            "ok",
            tem_xml_importado_valido=_obter_tem_xml_importado_valido(current_user.cnpj),
        )
    )


@auth_router.get("/perfil", response_model=CompanyProfileResponse)
def obter_perfil_empresa(current_user: AuthenticatedUser = Depends(get_current_user)):
    perfil = get_company_profile_service().obter_empresa(current_user.cnpj)
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nao foi possivel localizar os dados da empresa da sessao atual.",
        )

    return CompanyProfileResponse(
        status="ok",
        login_id=current_user.login_id,
        empresa_id=current_user.empresa_id,
        cnpj=perfil.get("cnpj", current_user.cnpj),
        empresa_nome=perfil.get("nome") or current_user.empresa_nome,
        estado=perfil.get("estado") or "",
        cidade=perfil.get("cidade") or "",
    )


@auth_router.patch("/senha", response_model=UpdatePasswordResponse)
def atualizar_senha(
    request: UpdatePasswordRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    try:
        get_login_service().atualizar_senha(
            login_id=current_user.login_id,
            nova_senha=request.nova_senha,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except psycopg.OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servico de autenticacao indisponivel no momento.",
        ) from exc

    return UpdatePasswordResponse(
        status="ok",
        message="Senha atualizada com sucesso.",
    )


@auth_router.post("/sair", status_code=status.HTTP_204_NO_CONTENT)
def sair(response: Response):
    clear_auth_cookie(response)
    log_security_event("logout", outcome="success", reason="user_logout")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


router.include_router(auth_router)
