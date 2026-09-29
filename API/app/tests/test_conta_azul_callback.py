import pytest
from fastapi.testclient import TestClient

from app.core.security import AuthenticatedUser, get_current_user
from app.main import app


class FakeIntegracoesRepository:
    rows: dict[int, dict] = {}

    def __init__(self, conn_params=None):
        pass

    def validar_state(self, empresa_id, state):
        row = self.rows.get(empresa_id)
        if row and row.get("oauth_state") == state:
            return row
        return None

    def marcar_erro(self, empresa_id, erro_mensagem):
        self.rows.setdefault(empresa_id, {})["erro_mensagem"] = erro_mensagem


def _set_credenciais(monkeypatch):
    monkeypatch.setenv("CONTAAZUL_CLIENT_ID", "id")
    monkeypatch.setenv("CONTAAZUL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("CONTAAZUL_REDIRECT_URI", "http://localhost:8000/callback")


@pytest.fixture
def client_conta_azul(monkeypatch):
    FakeIntegracoesRepository.rows = {1: {"oauth_state": "state-valido"}}
    monkeypatch.setattr("app.main.IntegracoesRepository", FakeIntegracoesRepository)

    user = AuthenticatedUser(
        login_id=1,
        empresa_id=1,
        cnpj="12345678000190",
        email="teste@example.com",
        empresa_nome="Empresa Teste",
        tem_sped=False,
        tem_conta_azul=True,
        tem_xml=False,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_callback_troca_code_por_token(client_conta_azul, monkeypatch):
    _set_credenciais(monkeypatch)

    from contaazul.auth import ContaAzulAuth, TokenSet

    def _fake_exchange(self, code):
        assert code == "57810f50-5286-4ecd-afb1-56c888067d9b"
        return TokenSet(access_token="a", refresh_token="r", expires_in=3600, obtained_at=0)

    monkeypatch.setattr(ContaAzulAuth, "exchange_code_for_token", _fake_exchange)

    response = client_conta_azul.get(
        "/callback",
        params={"code": "57810f50-5286-4ecd-afb1-56c888067d9b", "state": "state-valido"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_callback_rejeita_state_incorreto(client_conta_azul):
    response = client_conta_azul.get("/callback", params={"code": "x", "state": "state-forjado"})

    assert response.status_code == 400


def test_callback_rejeita_sem_state(client_conta_azul):
    response = client_conta_azul.get("/callback", params={"code": "x"})

    assert response.status_code == 400


def test_callback_rejeita_empresa_sem_conta_azul(client):
    response = client.get("/callback", params={"code": "x", "state": "qualquer"})

    assert response.status_code == 403


def test_callback_propaga_erro_da_autorizacao(client):
    response = client.get("/callback", params={"code": "x", "error": "access_denied"})

    assert response.status_code == 400


def test_callback_exige_code(client):
    response = client.get("/callback")

    assert response.status_code == 422


def test_callback_exige_login(unauthenticated_client):
    response = unauthenticated_client.get("/callback", params={"code": "x"})

    assert response.status_code == 401
