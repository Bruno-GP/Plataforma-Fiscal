import os


def _env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def get_log_level() -> str:
    raw_value = os.getenv("LOG_LEVEL", "CRITICAL").strip().upper()
    return raw_value if raw_value in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"} else "WARNING"


def get_api_request_logs_enabled() -> bool:
    return _env_bool("API_REQUEST_LOGS", False)


def get_auth_secret_key() -> str:
    return os.getenv("AUTH_SECRET_KEY", "dev-secret-change-me")


def get_auth_token_expire_minutes() -> int:
    raw_value = os.getenv("AUTH_TOKEN_EXPIRE_MINUTES", "480").strip()

    try:
        expire_minutes = int(raw_value)
    except ValueError as exc:
        raise ValueError("AUTH_TOKEN_EXPIRE_MINUTES deve ser um inteiro.") from exc

    return max(expire_minutes, 5)


def get_app_env() -> str:
    return os.getenv("APP_ENV", "development").strip().lower()


def is_production() -> bool:
    return get_app_env() == "production"


def get_session_cookie_name() -> str:
    return os.getenv("AUTH_COOKIE_NAME", "plataforma_fiscal_session").strip() or "plataforma_fiscal_session"


def get_session_cookie_domain() -> str | None:
    raw_value = os.getenv("AUTH_COOKIE_DOMAIN", "").strip()
    return raw_value or None


def get_session_cookie_path() -> str:
    return os.getenv("AUTH_COOKIE_PATH", "/").strip() or "/"


def get_session_cookie_samesite() -> str:
    raw_value = os.getenv("AUTH_COOKIE_SAMESITE", "lax").strip().lower()
    if raw_value not in {"lax", "strict", "none"}:
        return "lax"
    return raw_value


def get_session_cookie_secure() -> bool:
    raw_value = os.getenv("AUTH_COOKIE_SECURE", "").strip().lower()
    if raw_value in {"true", "1", "yes"}:
        return True
    if raw_value in {"false", "0", "no"}:
        return False
    return is_production()


def get_cors_allow_origins() -> str:
    if is_production():
        default_value = ""
    else:
        default_value = ",".join(
            [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:8080",
                "http://127.0.0.1:8080",
            ]
        )

    raw_value = os.getenv("CORS_ALLOW_ORIGINS")
    if raw_value is None:
        return default_value

    normalized = raw_value.strip()
    if not normalized and not is_production():
        return default_value

    if normalized == "*" and not is_production():
        return default_value

    return raw_value


def get_cors_allow_origin_regex() -> str:
    if is_production():
        default_value = ""
    else:
        default_value = r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    raw_value = os.getenv("CORS_ALLOW_ORIGIN_REGEX")
    if raw_value is None:
        return default_value

    normalized = raw_value.strip()
    if not normalized and not is_production():
        return default_value

    return normalized


def get_cors_allow_credentials() -> bool:
    return os.getenv("CORS_ALLOW_CREDENTIALS", "true").strip().lower() == "true"


def validate_production_config() -> None:
    if not is_production():
        return

    errors: list[str] = []
    auth_secret = get_auth_secret_key().strip()
    insecure_auth_secrets = {"dev-secret-change-me", "change-me", ""}

    if auth_secret in insecure_auth_secrets or len(auth_secret) < 32:
        errors.append("AUTH_SECRET_KEY deve ser forte, exclusivo e ter pelo menos 32 caracteres")

    cors_origins = [
        origin.strip()
        for origin in get_cors_allow_origins().split(",")
        if origin.strip()
    ]
    cors_origin_regex = get_cors_allow_origin_regex().strip()

    if not cors_origins and not cors_origin_regex:
        errors.append("CORS_ALLOW_ORIGINS ou CORS_ALLOW_ORIGIN_REGEX deve ser definido")

    if "*" in cors_origins:
        errors.append("CORS_ALLOW_ORIGINS nao deve usar wildcard em producao")

    if cors_origin_regex in {".*", "^.*$", ".*$"}:
        errors.append("CORS_ALLOW_ORIGIN_REGEX nao deve aceitar qualquer origem em producao")

    if not get_session_cookie_secure():
        errors.append("AUTH_COOKIE_SECURE deve estar habilitado em producao")

    if get_session_cookie_samesite() == "none" and not get_session_cookie_secure():
        errors.append("AUTH_COOKIE_SAMESITE=none exige cookie secure")

    if errors:
        raise RuntimeError("Configuracao de producao insegura: " + "; ".join(errors) + ".")


def get_login_max_failed_attempts() -> int:
    raw_value = os.getenv("AUTH_MAX_FAILED_ATTEMPTS", "5").strip()
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise ValueError("AUTH_MAX_FAILED_ATTEMPTS deve ser um inteiro.") from exc
    return max(parsed, 1)


def get_login_lockout_minutes() -> int:
    raw_value = os.getenv("AUTH_LOCKOUT_MINUTES", "15").strip()
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise ValueError("AUTH_LOCKOUT_MINUTES deve ser um inteiro.") from exc
    return max(parsed, 1)


def get_login_success_cache_ttl_seconds() -> int:
    raw_value = os.getenv("AUTH_SUCCESS_CACHE_TTL_SECONDS", "300").strip()
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise ValueError("AUTH_SUCCESS_CACHE_TTL_SECONDS deve ser um inteiro.") from exc
    return max(parsed, 0)


def get_password_min_length() -> int:
    raw_value = os.getenv("AUTH_PASSWORD_MIN_LENGTH", "12").strip()
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise ValueError("AUTH_PASSWORD_MIN_LENGTH deve ser um inteiro.") from exc
    return max(parsed, 8)


def get_upload_max_xml_bytes() -> int:
    raw_value = os.getenv("UPLOAD_MAX_XML_BYTES", str(5 * 1024 * 1024)).strip()
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise ValueError("UPLOAD_MAX_XML_BYTES deve ser um inteiro.") from exc
    return max(parsed, 1024)


def get_upload_max_txt_bytes() -> int:
    raw_value = os.getenv("UPLOAD_MAX_TXT_BYTES", str(20 * 1024 * 1024)).strip()
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise ValueError("UPLOAD_MAX_TXT_BYTES deve ser um inteiro.") from exc
    return max(parsed, 1024)


def get_upload_max_total_bytes() -> int:
    raw_value = os.getenv("UPLOAD_MAX_TOTAL_BYTES", str(50 * 1024 * 1024)).strip()
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise ValueError("UPLOAD_MAX_TOTAL_BYTES deve ser um inteiro.") from exc
    return max(parsed, 1024)


def get_processamento_batch_root_dir() -> str | None:
    raw_value = os.getenv("PROCESSAMENTO_BATCH_ROOT_DIR", "").strip()
    return raw_value or None


def get_ibpt_sync_min_interval_seconds() -> int:
    raw_value = os.getenv("IBPT_SYNC_MIN_INTERVAL_SECONDS", "300").strip()
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise ValueError("IBPT_SYNC_MIN_INTERVAL_SECONDS deve ser um inteiro.") from exc
    return max(parsed, 0)


def get_ibpt_sync_admin_emails() -> set[str]:
    raw_value = os.getenv("IBPT_SYNC_ADMIN_EMAILS", "")
    return {
        email.strip().lower()
        for email in raw_value.split(",")
        if email.strip()
    }
