from dataclasses import dataclass
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.core.security import AuthenticatedUser, get_current_user
from app.core.rate_limit import ibpt_sync_limiter
from app.main import app
from app.models.nfe.schemas import ProcessarNFeRequest
from app.services.nfe.process_nfe import ProcessarNFeService


@dataclass
class _NotaFake:
    data_emissao: datetime
    emitente_cnpj: str


@pytest.fixture
def scoped_client(test_user: AuthenticatedUser):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: test_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset_ibpt_limiter():
    ibpt_sync_limiter._last_call_at.clear()
    yield
    ibpt_sync_limiter._last_call_at.clear()


def test_nfe_processar_rejeita_escopo_de_outra_empresa(scoped_client):
    response = scoped_client.post(
        "/api/nfe/processar?cnpj_empresa_origem=99999999000199",
        json={"origem": "teste", "pasta_xml": "lote"},
    )

    assert response.status_code == 403


def test_sped_processar_rejeita_escopo_de_outra_empresa(scoped_client):
    response = scoped_client.post(
        "/api/sped/processar?cnpj_empresa_origem=99999999000199",
        json={"arquivo_sped": "arquivo.txt"},
    )

    assert response.status_code == 403


def test_nfe_processar_sem_root_dir_configurado(client, monkeypatch):
    monkeypatch.setattr("app.api.nfe.routes.get_processamento_batch_root_dir", lambda: None)
    monkeypatch.setattr("app.api.nfe.routes.validar_empresa_xml", lambda cnpj: None)

    response = client.post(
        "/api/nfe/processar?cnpj_empresa_origem=12345678000190",
        json={"origem": "teste", "pasta_xml": "lote"},
    )

    assert response.status_code == 400
    assert "desabilitado" in response.json()["detail"]


def test_nfe_processar_rejeita_path_traversal(client, monkeypatch, tmp_path):
    monkeypatch.setattr("app.api.nfe.routes.get_processamento_batch_root_dir", lambda: str(tmp_path))
    monkeypatch.setattr("app.api.nfe.routes.validar_empresa_xml", lambda cnpj: None)

    response = client.post(
        "/api/nfe/processar?cnpj_empresa_origem=12345678000190",
        json={"origem": "teste", "pasta_xml": "../fora-da-raiz"},
    )

    assert response.status_code == 400
    assert "diretorio permitido" in response.json()["detail"]


def test_sped_processar_rejeita_path_traversal(client, monkeypatch, tmp_path):
    monkeypatch.setattr("app.api.sped.routes.get_processamento_batch_root_dir", lambda: str(tmp_path))
    monkeypatch.setattr("app.api.sped.routes.validar_empresa_sped", lambda cnpj: None)

    response = client.post(
        "/api/sped/processar?cnpj_empresa_origem=12345678000190",
        json={"arquivo_sped": "../../etc/passwd"},
    )

    assert response.status_code == 400
    assert "diretorio permitido" in response.json()["detail"]


def test_processar_nfe_service_rejeita_cnpj_divergente(fixtures_dir, monkeypatch):
    monkeypatch.setattr(
        "app.services.nfe.process_nfe.XmlReader.ler_pasta",
        lambda self, pasta: ["dummy"],
    )
    monkeypatch.setattr(
        "app.services.nfe.process_nfe.NFeExtractor.extrair",
        lambda self, xmls: [_NotaFake(data_emissao=datetime(2026, 1, 1), emitente_cnpj="12345678000190")],
    )

    request = ProcessarNFeRequest(origem="teste", pasta_xml=str(fixtures_dir), periodo=None)
    response = ProcessarNFeService().executar(request, cnpj_esperado="99999999000199")

    assert response.status == "erro"
    assert any("cnpj_empresa_origem" in erro["mensagem"] for erro in response.erros)


def test_ibpt_sincronizar_aplica_cooldown(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.ncm.routes.IBPTSyncService.sincronizar",
        lambda self, uf, todas_ufs, ncm: [],
    )
    monkeypatch.setattr("app.api.ncm.routes.get_ibpt_sync_min_interval_seconds", lambda: 300)

    primeira = client.post("/api/ncm/ibpt/sincronizar", json={"uf": "SC"})
    segunda = client.post("/api/ncm/ibpt/sincronizar", json={"uf": "SC"})

    assert primeira.status_code == 200
    assert segunda.status_code == 429
