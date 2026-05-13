import httpx
import pytest

from app.core.http_client import ExternalServiceError, get_json
from app.services.NCM.ibpt_sync_service import IBPTSyncService


class FakeResponse:
    def __init__(self, payload=None, *, status_code=200, json_error: Exception | None = None):
        self.payload = payload
        self.status_code = status_code
        self.json_error = json_error
        self.request = httpx.Request("GET", "https://example.test")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "erro externo",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    def json(self):
        if self.json_error:
            raise self.json_error
        return self.payload


class FakeClient:
    next_response = FakeResponse({})
    next_error: Exception | None = None
    calls = []

    def __init__(self, timeout):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url, params=None):
        self.calls.append((url, params, self.timeout))
        if self.next_error:
            raise self.next_error
        return self.next_response


@pytest.fixture(autouse=True)
def reset_fake_client():
    FakeClient.next_response = FakeResponse({})
    FakeClient.next_error = None
    FakeClient.calls = []


def test_get_json_retorna_payload_e_repassa_timeout(monkeypatch):
    monkeypatch.setattr("app.core.http_client.httpx.Client", FakeClient)
    FakeClient.next_response = FakeResponse({"ok": True})

    payload = get_json(
        "https://example.test/api",
        params={"uf": "SC"},
        timeout_seconds=12.5,
        service_name="Servico",
    )

    assert payload == {"ok": True}
    assert FakeClient.calls == [("https://example.test/api", {"uf": "SC"}, 12.5)]


def test_get_json_normaliza_timeout(monkeypatch):
    monkeypatch.setattr("app.core.http_client.httpx.Client", FakeClient)
    FakeClient.next_error = httpx.TimeoutException("timeout")

    with pytest.raises(ExternalServiceError, match="tempo limite"):
        get_json("https://example.test/api", service_name="Servico")


def test_get_json_normaliza_http_status(monkeypatch):
    monkeypatch.setattr("app.core.http_client.httpx.Client", FakeClient)
    FakeClient.next_response = FakeResponse(status_code=503)

    with pytest.raises(ExternalServiceError) as exc_info:
        get_json("https://example.test/api", service_name="Servico")

    assert exc_info.value.status_code == 503
    assert "HTTP 503" in str(exc_info.value)


def test_get_json_normaliza_json_invalido(monkeypatch):
    monkeypatch.setattr("app.core.http_client.httpx.Client", FakeClient)
    FakeClient.next_response = FakeResponse(json_error=ValueError("json invalido"))

    with pytest.raises(ExternalServiceError, match="JSON invalida"):
        get_json("https://example.test/api", service_name="Servico")


def test_ibpt_busca_todos_ncm_uf_usa_cliente_padronizado(monkeypatch):
    calls = []

    def fake_get_json(url, *, params, timeout_seconds, service_name):
        calls.append((url, params, timeout_seconds, service_name))
        return {"ncm": [{"codigo": "01012100"}]}

    monkeypatch.setattr("app.services.NCM.ibpt_sync_service.get_json", fake_get_json)

    registros = IBPTSyncService()._buscar_todos_ncm_uf("SC")

    assert registros == [{"codigo": "01012100"}]
    assert calls[0][1] == {"uf": "SC"}
    assert calls[0][2] == 60.0
    assert calls[0][3] == "IBPT"


def test_ibpt_busca_ncm_especifico_retorna_lista_quando_codigo_presente(monkeypatch):
    monkeypatch.setattr(
        "app.services.NCM.ibpt_sync_service.get_json",
        lambda *args, **kwargs: {"codigo": "01012100", "descricao": "Teste"},
    )

    registros = IBPTSyncService()._buscar_ncm_especifico("01012100", "SC")

    assert registros == [{"codigo": "01012100", "descricao": "Teste"}]
