from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient


APP_DIR = Path(__file__).resolve().parents[1]
API_DIR = APP_DIR.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.core.security import AuthenticatedUser, require_company_scope
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
    app.dependency_overrides[require_company_scope] = lambda: test_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
