from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.audit import log_security_event
from app.core.config import (
    get_auth_secret_key,
    get_auth_token_expire_minutes,
    get_session_cookie_domain,
    get_session_cookie_name,
    get_session_cookie_path,
    get_session_cookie_samesite,
    get_session_cookie_secure,
)
from app.services.nfe.empresa_service import normalizar_cnpj


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    login_id: int
    empresa_id: int
    cnpj: str
    email: str
    empresa_nome: str
    tem_sped: bool


def create_access_token(user: AuthenticatedUser) -> tuple[str, int]:
    expires_in = get_auth_token_expire_minutes() * 60
    payload = {
        "sub": str(user.login_id),
        "empresa_id": user.empresa_id,
        "cnpj": user.cnpj,
        "email": user.email,
        "empresa_nome": user.empresa_nome,
        "tem_sped": user.tem_sped,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, get_auth_secret_key(), algorithm="HS256")
    return token, expires_in


def get_session_expires_in() -> int:
    return get_auth_token_expire_minutes() * 60


def set_auth_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    response.set_cookie(
        key=get_session_cookie_name(),
        value=token,
        max_age=max_age_seconds,
        httponly=True,
        secure=get_session_cookie_secure(),
        samesite=get_session_cookie_samesite(),
        path=get_session_cookie_path(),
        domain=get_session_cookie_domain(),
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=get_session_cookie_name(),
        path=get_session_cookie_path(),
        domain=get_session_cookie_domain(),
        secure=get_session_cookie_secure(),
        samesite=get_session_cookie_samesite(),
    )


def decode_access_token(token: str) -> AuthenticatedUser:
    try:
        payload = jwt.decode(token, get_auth_secret_key(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão expirada. Faça login novamente.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso inválido.",
        ) from exc

    return AuthenticatedUser(
        login_id=int(payload["sub"]),
        empresa_id=int(payload["empresa_id"]),
        cnpj=normalizar_cnpj(str(payload["cnpj"])),
        email=str(payload["email"]).strip().lower(),
        empresa_nome=str(payload.get("empresa_nome", "")).strip(),
        tem_sped=bool(payload.get("tem_sped", False)),
    )


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    cookie_token = request.cookies.get(get_session_cookie_name())
    if cookie_token:
        return decode_access_token(cookie_token)

    if credentials is not None and credentials.scheme.lower() == "bearer":
        return decode_access_token(credentials.credentials)

    log_security_event(
        "auth_required",
        outcome="rejected",
        auth_source="missing",
        reason="missing_credentials",
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autenticação obrigatória.",
    )


def require_company_scope(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    query_params = request.query_params
    cnpj_params = (
        query_params.get("emitente_cnpj"),
        query_params.get("cnpj_emitente"),
        query_params.get("cnpj_empresa_origem"),
    )

    for cnpj_value in cnpj_params:
        if cnpj_value and normalizar_cnpj(cnpj_value) != current_user.cnpj:
            log_security_event(
                "access_denied",
                outcome="rejected",
                reason="cnpj_scope_mismatch",
                login_id=current_user.login_id,
                empresa_id=current_user.empresa_id,
                email=current_user.email,
                cnpj=current_user.cnpj,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem acesso a esta empresa.",
            )

    email_param = request.query_params.get("email")
    if email_param and email_param.strip().lower() != current_user.email:
        log_security_event(
            "access_denied",
            outcome="rejected",
            reason="email_scope_mismatch",
            login_id=current_user.login_id,
            empresa_id=current_user.empresa_id,
            email=current_user.email,
            cnpj=current_user.cnpj,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a este usuário.",
        )

    return current_user
