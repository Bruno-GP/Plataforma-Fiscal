import os
from pathlib import Path
import sys
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient


APP_DIR = Path(__file__).resolve().parents[1]
API_DIR = APP_DIR.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.core.security import AuthenticatedUser, get_current_user, require_company_scope
from app.main import app


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def test_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        login_id=1,
        empresa_id=1,
        cnpj="12345678000190",
        email="teste@example.com",
        empresa_nome="Empresa Teste",
        tem_sped=False,
    )


@pytest.fixture
def client(test_user):
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[require_company_scope] = lambda: test_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client():
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

def _psycopg_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _is_safe_test_database(url: str) -> bool:
    parsed = urlparse(_psycopg_url(url))
    database = parsed.path.rsplit("/", 1)[-1].lower()
    return parsed.scheme in {"postgresql", "postgres"} and (
        "test" in database or "teste" in database
    )


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = os.getenv("PLATAFORMA_FISCAL_TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "Defina PLATAFORMA_FISCAL_TEST_DATABASE_URL para rodar os testes de banco."
        )
    if not _is_safe_test_database(url):
        pytest.fail(
            "PLATAFORMA_FISCAL_TEST_DATABASE_URL deve apontar para um banco descartavel "
            "com 'test' ou 'teste' no nome."
        )
    return url


@pytest.fixture(scope="session")
def migrated_db(test_database_url):
    psycopg = pytest.importorskip("psycopg")
    alembic_command = pytest.importorskip("alembic.command")
    alembic_config = pytest.importorskip("alembic.config")

    repo_root = Path(__file__).resolve().parents[3]
    alembic_ini = repo_root / "API" / "app" / "alembic.ini"

    previous_database_url = os.environ.get("DATABASE_URL")
    previous_postgres_dsn = os.environ.get("POSTGRES_DSN")
    os.environ["DATABASE_URL"] = test_database_url
    os.environ["POSTGRES_DSN"] = test_database_url

    schema_was_reset = False

    def reset_public_schema(skip_on_connection_error: bool = False) -> None:
        nonlocal schema_was_reset
        try:
            with psycopg.connect(_psycopg_url(test_database_url), autocommit=True) as conn:
                conn.execute("DROP SCHEMA IF EXISTS public CASCADE;")
                conn.execute("CREATE SCHEMA public;")
            schema_was_reset = True
        except psycopg.OperationalError as exc:
            if skip_on_connection_error:
                pytest.skip(
                    "PostgreSQL de teste indisponivel ou credenciais invalidas em "
                    f"PLATAFORMA_FISCAL_TEST_DATABASE_URL: {exc}"
                )
            raise

    try:
        reset_public_schema(skip_on_connection_error=True)

        cfg = alembic_config.Config(str(alembic_ini))
        cfg.set_main_option("script_location", str(APP_DIR / "alembic"))
        alembic_command.upgrade(cfg, "head")

        with psycopg.connect(_psycopg_url(test_database_url)) as conn:
            yield conn
    finally:
        if schema_was_reset:
            reset_public_schema()
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        if previous_postgres_dsn is None:
            os.environ.pop("POSTGRES_DSN", None)
        else:
            os.environ["POSTGRES_DSN"] = previous_postgres_dsn
