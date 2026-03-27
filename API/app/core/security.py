import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_auth_secret_key, get_auth_token_expire_minutes
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


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}")


def create_access_token(user: AuthenticatedUser) -> tuple[str, int]:
    expire_minutes = get_auth_token_expire_minutes()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {
        "sub": str(user.login_id),
        "empresa_id": user.empresa_id,
        "cnpj": user.cnpj,
        "email": user.email,
        "empresa_nome": user.empresa_nome,
        "tem_sped": user.tem_sped,
        "exp": int(expires_at.timestamp()),
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = _base64url_encode(payload_json)
    signature = hmac.new(
        get_auth_secret_key().encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    token = f"{encoded_payload}.{_base64url_encode(signature)}"
    return token, expire_minutes * 60


def decode_access_token(token: str) -> AuthenticatedUser:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso inválido.",
        ) from exc

    expected_signature = hmac.new(
        get_auth_secret_key().encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    actual_signature = _base64url_decode(encoded_signature)

    if not hmac.compare_digest(expected_signature, actual_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso inválido.",
        )

    try:
        payload = json.loads(_base64url_decode(encoded_payload).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso inválido.",
        ) from exc

    expires_at = int(payload.get("exp", 0))
    if expires_at <= int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão expirada. Faça login novamente.",
        )

    return AuthenticatedUser(
        login_id=int(payload["sub"]),
        empresa_id=int(payload["empresa_id"]),
        cnpj=normalizar_cnpj(str(payload["cnpj"])),
        email=str(payload["email"]).strip().lower(),
        empresa_nome=str(payload.get("empresa_nome", "")).strip(),
        tem_sped=bool(payload.get("tem_sped", False)),
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação obrigatória.",
        )

    return decode_access_token(credentials.credentials)


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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem acesso a esta empresa.",
            )

    email_param = query_params.get("email")
    if email_param and email_param.strip().lower() != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a este usuário.",
        )

    return current_user
