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

    def atualizar_senha(self, **kwargs):
        return None


class FailingValueLoginService(FakeLoginService):
    def registrar(self, **kwargs):
        raise ValueError("dados invalidos")

    def autenticar(self, **kwargs):
        raise ValueError("credenciais invalidas")

    def atualizar_senha(self, **kwargs):
        raise ValueError("senha invalida")


class FailingDatabaseLoginService(FakeLoginService):
    def registrar(self, **kwargs):
        raise psycopg.OperationalError("database down")

    def autenticar(self, **kwargs):
        raise psycopg.OperationalError("database down")

    def atualizar_senha(self, **kwargs):
        raise psycopg.OperationalError("database down")


class FakeCompanyProfileService:
    def obter_empresa(self, cnpj):
        return {
            "id": 1,
            "cnpj": cnpj,
            "nome": "Empresa Teste",
            "estado": "SP",
            "cidade": "Sao Paulo",
            "municipio_id": "3550308",
            "codigo_ibge": "3550308",
        }


def _cadastro_payload():
    return {
        "empresa_nome": "Empresa Teste",
        "email": "teste@example.com",
        "senha": "Senha@123456",
        "cnpj": "12345678000190",
        "tem_sped": False,
        "estado": "SP",
        "cidade": "Sao Paulo",
        "municipio_id": "3550308",
        "codigo_ibge": "3550308",
    }


def test_auth_registrar_preserva_status_cookie_e_payload(client, monkeypatch):
    monkeypatch.setattr("app.api.auth.routes.get_login_service", lambda: FakeLoginService())
    monkeypatch.setattr(
        "app.api.auth.routes.MunicipiosCatalogService.resolver_municipio",
        lambda **kwargs: {
            "municipio_id": "3550308",
            "codigo_ibge": "3550308",
            "nome": "Sao Paulo",
            "uf": "SP",
        },
    )
    monkeypatch.setattr(
        "app.api.auth.routes.EmpresaService",
        lambda: type("FakeEmpresaService", (), {"atualizar_localidade": lambda self, **kwargs: None})(),
    )

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
    monkeypatch.setattr(
        "app.api.auth.routes.MunicipiosCatalogService.resolver_municipio",
        lambda **kwargs: {
            "municipio_id": "3550308",
            "codigo_ibge": "3550308",
            "nome": "Sao Paulo",
            "uf": "SP",
        },
    )
    monkeypatch.setattr(
        "app.api.auth.routes.EmpresaService",
        lambda: type("FakeEmpresaService", (), {"atualizar_localidade": lambda self, **kwargs: None})(),
    )

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
    monkeypatch.setattr(
        "app.api.auth.routes.MunicipiosCatalogService.resolver_municipio",
        lambda **kwargs: {
            "municipio_id": "3550308",
            "codigo_ibge": "3550308",
            "nome": "Sao Paulo",
            "uf": "SP",
        },
    )
    monkeypatch.setattr(
        "app.api.auth.routes.EmpresaService",
        lambda: type("FakeEmpresaService", (), {"atualizar_localidade": lambda self, **kwargs: None})(),
    )

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
    monkeypatch.setattr(
        "app.api.auth.routes.EmpresaService",
        lambda: type("FakeEmpresaService", (), {"atualizar_localidade": lambda self, **kwargs: None})(),
    )
    monkeypatch.setattr(
        "app.api.auth.routes.MunicipiosCatalogService.resolver_municipio",
        lambda **kwargs: None,
    )

    response = client.post(
        "/api/auth/registrar",
        json={
            **_cadastro_payload(),
            "estado": "S",
        },
    )

    assert response.status_code == 400
    assert "UF informada" in response.json()["detail"]


def test_auth_registrar_rejeita_cidade_ausente(client, monkeypatch):
    monkeypatch.setattr("app.api.auth.routes.get_login_service", lambda: FakeLoginService())
    monkeypatch.setattr(
        "app.api.auth.routes.EmpresaService",
        lambda: type("FakeEmpresaService", (), {"atualizar_localidade": lambda self, **kwargs: None})(),
    )
    monkeypatch.setattr(
        "app.api.auth.routes.MunicipiosCatalogService.resolver_municipio",
        lambda **kwargs: None,
    )

    response = client.post(
        "/api/auth/registrar",
        json={
            **_cadastro_payload(),
            "cidade": None,
        },
    )

    assert response.status_code == 400
    assert "cidade" in response.json()["detail"].lower()


def test_auth_sessao_e_logout_preservam_contratos(client):
    sessao = client.get("/api/auth/sessao")
    logout = client.post("/api/auth/sair")

    assert sessao.status_code == 200
    assert sessao.json()["status"] == "ok"
    assert sessao.json()["cnpj"] == "12345678000190"
    assert sessao.json()["tem_xml_importado_valido"] is False
    assert logout.status_code == 204
    assert "plataforma_fiscal_session=" in logout.headers["set-cookie"]


def test_auth_perfil_retorna_dados_da_empresa_da_sessao(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.auth.routes.get_company_profile_service",
        lambda: FakeCompanyProfileService(),
    )

    response = client.get("/api/auth/perfil")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["cnpj"] == "12345678000190"
    assert payload["empresa_nome"] == "Empresa Teste"
    assert payload["estado"] == "SP"
    assert payload["cidade"] == "Sao Paulo"


def test_auth_senha_atualiza_somente_a_senha_do_usuario_logado(client, monkeypatch):
    chamadas = []

    class RecordingLoginService(FakeLoginService):
        def atualizar_senha(self, **kwargs):
            chamadas.append(kwargs)

    monkeypatch.setattr("app.api.auth.routes.get_login_service", lambda: RecordingLoginService())

    response = client.patch("/api/auth/senha", json={"nova_senha": "SenhaNova@123"})

    assert response.status_code == 200
    assert response.json()["message"] == "Senha atualizada com sucesso."
    assert chamadas == [{"login_id": 1, "nova_senha": "SenhaNova@123"}]


def test_auth_senha_rejeita_senha_em_branco(client, monkeypatch):
    monkeypatch.setattr("app.api.auth.routes.get_login_service", lambda: FailingValueLoginService())

    response = client.patch("/api/auth/senha", json={"nova_senha": "   "})

    assert response.status_code == 400
    assert "senha" in response.json()["detail"].lower()


def test_auth_senha_database_error_vira_503(client, monkeypatch):
    monkeypatch.setattr("app.api.auth.routes.get_login_service", lambda: FailingDatabaseLoginService())

    response = client.patch("/api/auth/senha", json={"nova_senha": "SenhaNova@123"})

    assert response.status_code == 503
    assert "indispon" in response.json()["detail"].lower()
