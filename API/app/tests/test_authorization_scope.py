from fastapi.testclient import TestClient
import pytest

from app.core.security import AuthenticatedUser, get_current_user
from app.main import app


@pytest.fixture
def scoped_client(test_user: AuthenticatedUser):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: test_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/nfe/xml/pendencias?cnpj_emitente=99999999000199"),
        ("post", "/api/nfe/xml/processar-importados?cnpj_emitente=99999999000199"),
        ("get", "/api/nfe/kpis?emitente_cnpj=99999999000199"),
        ("get", "/api/sped/pendencias?cnpj_emitente=99999999000199"),
        ("post", "/api/sped/processar-importados?cnpj_emitente=99999999000199"),
        ("get", "/api/sped/kpis?emitente_cnpj=99999999000199"),
        ("get", "/api/reforma-tributaria/apuracao?emitente_cnpj=99999999000199"),
        ("post", "/api/reforma-tributaria/backfill?emitente_cnpj=99999999000199"),
    ],
)
def test_rotas_fiscais_rejeitam_escopo_de_outra_empresa(scoped_client, method, path):
    response = getattr(scoped_client, method)(path)

    assert response.status_code == 403
    assert "empresa" in response.json()["detail"]


def test_rota_nfe_rejeita_email_de_outro_usuario(scoped_client):
    response = scoped_client.get("/api/nfe/analise/compras?email=outro@example.com")

    assert response.status_code == 403
    assert "usuário" in response.json()["detail"]
