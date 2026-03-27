import os


def get_auth_secret_key() -> str:
    return os.getenv("AUTH_SECRET_KEY", "dev-secret-change-me")


def get_auth_token_expire_minutes() -> int:
    raw_value = os.getenv("AUTH_TOKEN_EXPIRE_MINUTES", "480").strip()

    try:
        expire_minutes = int(raw_value)
    except ValueError as exc:
        raise ValueError("AUTH_TOKEN_EXPIRE_MINUTES deve ser um inteiro.") from exc

    return max(expire_minutes, 5)
