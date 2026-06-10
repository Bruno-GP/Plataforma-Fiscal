from dataclasses import dataclass

import psycopg


@dataclass
class FakeLoginResult:
    login_id: int = 1
    empresa_id: int = 2
    cnpj: str = "12345678000190"
    email: str = "teste@example.com"
    empresa_nome: str = "Empresa Teste"
    tem_sped: bool = False
    tem_xml_importado_valido: bool = False


class FakeLoginService:
    def registrar(self, **kwargs):
        return FakeLoginResult(
            cnpj=kwargs["cnpj"],
            email=kwargs["email"],
            empresa_nome=kwargs["empresa_nome"],
            tem_sped=kwargs["tem_sped"],
            tem_xml_importado_valido=False,
        )

    def autenticar(self, **kwargs):
        return FakeLoginResult(email=kwargs["email"])


class FailingValueLoginService(FakeLoginService):
    def registrar(self, **kwargs):
        raise ValueError("dados invalidos")

    def autenticar(self, **kwargs):
        raise ValueError("credenciais invalidas")


class FailingDatabaseLoginService(FakeLoginService):
    def registrar(self, **kwargs):
        raise psycopg.OperationalError("database down")

    def autenticar(self, **kwargs):
        raise psycopg.OperationalError("database down")


def _cadastro_payload():
    return {
        "empresa_nome": "Empresa Teste",
        "email": "teste@example.com",
        "senha": "Senha@123456",
        "cnpj": "12345678000190",
        "tem_sped": False,
    }


def test_auth_registrar_preserva_status_cookie_e_payload(client, monkeypatch):
    monkeypatch.setattr("app.api.auth.routes.get_login_service", lambda: FakeLoginService())

    response = client.post("/api/auth/registrar", json=_cadastro_payload())

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["cnpj"] == "12345678000190"
    assert payload["email"] == "teste@example.com"
    assert payload["empresa_nome"] == "Empresa Teste"
    assert payload["tem_sped"] is False
    assert payload["tem_xml_importado_valido"] is False
    assert payload["expires_in"] > 0
    assert isinstance(payload["access_token"], str)
    assert payload["access_token"]
    assert "plataforma_fiscal_session=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]


def test_auth_entrar_preserva_status_cookie_e_payload(client, monkeypatch):
    monkeypatch.setattr("app.api.auth.routes.get_login_service", lambda: FakeLoginService())

    response = client.post(
        "/api/auth/entrar",
        json={"email": "teste@example.com", "senha": "Senha@123456"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["email"] == "teste@example.com"
    assert payload["tem_xml_importado_valido"] is False
    assert isinstance(payload["access_token"], str)
    assert payload["access_token"]
    assert "plataforma_fiscal_session=" in response.headers["set-cookie"]


def test_auth_registrar_value_error_vira_400(client, monkeypatch):
    monkeypatch.setattr("app.api.auth.routes.get_login_service", lambda: FailingValueLoginService())

    response = client.post("/api/auth/registrar", json=_cadastro_payload())

    assert response.status_code == 400
    assert response.json()["detail"] == "dados invalidos"


def test_auth_entrar_value_error_vira_401(client, monkeypatch):
    monkeypatch.setattr("app.api.auth.routes.get_login_service", lambda: FailingValueLoginService())

    response = client.post(
        "/api/auth/entrar",
        json={"email": "teste@example.com", "senha": "Senha@123456"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "credenciais invalidas"


def test_auth_database_error_vira_503(client, monkeypatch):
    monkeypatch.setattr("app.api.auth.routes.get_login_service", lambda: FailingDatabaseLoginService())

    cadastro = client.post("/api/auth/registrar", json=_cadastro_payload())
    login = client.post(
        "/api/auth/entrar",
        json={"email": "teste@example.com", "senha": "Senha@123456"},
    )

    assert cadastro.status_code == 503
    assert login.status_code == 503
    assert "autentica" in cadastro.json()["detail"]
    assert "indispon" in cadastro.json()["detail"]
    assert "autentica" in login.json()["detail"]
    assert "indispon" in login.json()["detail"]


def test_auth_registrar_rejeita_uf_invalida_antes_de_salvar(client, monkeypatch):
    monkeypatch.setattr("app.api.auth.routes.get_login_service", lambda: FakeLoginService())

    response = client.post(
        "/api/auth/registrar",
        json={
            **_cadastro_payload(),
            "estado": "S",
        },
    )

    assert response.status_code == 400
    assert "UF informada" in response.json()["detail"]


def test_auth_sessao_e_logout_preservam_contratos(client):
    sessao = client.get("/api/auth/sessao")
    logout = client.post("/api/auth/sair")

    assert sessao.status_code == 200
    assert sessao.json()["status"] == "ok"
    assert sessao.json()["cnpj"] == "12345678000190"
    assert sessao.json()["tem_xml_importado_valido"] is False
    assert logout.status_code == 204
    assert "plataforma_fiscal_session=" in logout.headers["set-cookie"]
