import os

from urllib.parse import parse_qs, unquote, urlparse


def _first_non_empty(*keys: str, default: str | None = None) -> str | None:
    for key in keys:
        value = os.environ.get(key)
        if value is not None and value.strip() != "":
            return value.strip()
    return default


def _porta_postgres(valor: str | None, default: int = 5432) -> int:
    if valor is None:
        return default

    try:
        return int(valor)
    except ValueError as exc:
        raise ValueError(f"Porta PostgreSQL inválida: {valor}") from exc


def _config_from_dsn(dsn: str | None) -> dict:
    if not dsn:
        return {}

    parsed = urlparse(dsn)
    if parsed.scheme not in {"postgres", "postgresql"}:
        return {}

    query = parse_qs(parsed.query)

    return {
        "host": parsed.hostname,
        "port": parsed.port,
        "database": parsed.path[1:] if parsed.path else None,
        "user": unquote(parsed.username) if parsed.username else None,
        "password": unquote(parsed.password) if parsed.password else None,
        "sslmode": query.get("sslmode", [None])[0],
    }

def carregar_config_postgres() -> dict:
    dsn = _first_non_empty("POSTGRES_NFE_DSN", "POSTGRES_DSN", "DATABASE_URL")
    dsn_config = _config_from_dsn(dsn)

    host = _first_non_empty(
        "POSTGRES_NFE_HOST",
        "POSTGRES_HOST",
        "PGHOST",
        default=dsn_config.get("host") or "localhost",
    )
    port = _porta_postgres(
        _first_non_empty("POSTGRES_NFE_PORT", "POSTGRES_PORT", "PGPORT", default=str(dsn_config.get("port") or ""))
        or None,
    )

    return {
        "conninfo": dsn,
        "host": host,
        "port": port,
        "database": _first_non_empty(
            "POSTGRES_NFE_DB",
            "POSTGRES_DB_NFE",
            "POSTGRES_DB",
            "PGDATABASE",
            default=dsn_config.get("database") or "postgres",
        ),
        "user": _first_non_empty(
            "POSTGRES_NFE_USER",
            "POSTGRES_USER",
            "PGUSER",
            default=dsn_config.get("user") or "postgres",
        ),
        "password": _first_non_empty(
            "POSTGRES_NFE_PASSWORD",
            "POSTGRES_PASSWORD",
            "PGPASSWORD",
            default=dsn_config.get("password") or "postgres",
        ),
        "sslmode": _first_non_empty(
            "POSTGRES_NFE_SSLMODE",
            "POSTGRES_SSLMODE",
            "PGSSLMODE",
            default=dsn_config.get("sslmode"),
        ),
    }