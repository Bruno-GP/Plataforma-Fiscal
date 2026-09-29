from logging.config import fileConfig
import os
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import create_engine, pool


ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - Alembic can still run with exported env vars.
    def load_dotenv(*args, **kwargs):
        return False


APP_DIR = Path(__file__).resolve().parents[1]
load_dotenv(
    APP_DIR / ".env",
    # Fail-closed: so sobrescreve env vars reais com o .env quando APP_ENV e
    # explicitamente "development". Ausente/vazio/typo -> nao sobrescreve.
    override=os.getenv("APP_ENV", "").strip().lower() == "development",
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def _first_non_empty(*keys: str) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value is not None and value.strip():
            return value.strip()
    return None


def _database_url() -> str:
    url = _first_non_empty(
        "ALEMBIC_DATABASE_URL",
        "DATABASE_URL",
        "POSTGRES_DSN",
        "POSTGRES_NFE_DSN",
    )
    if url:
        return url

    if os.getenv("APP_ENV", "").strip().lower() == "production":
        raise RuntimeError(
            "Defina ALEMBIC_DATABASE_URL, DATABASE_URL, POSTGRES_DSN ou "
            "POSTGRES_NFE_DSN para executar migrations em producao."
        )

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "postgres")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


def _sqlalchemy_url() -> str:
    url = _database_url()
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_sqlalchemy_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_sqlalchemy_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
