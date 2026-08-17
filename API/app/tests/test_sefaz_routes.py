from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.api.sefaz import routes
from app.services.sefaz.certificado_service import CertificadoInvalidoError
from app.services.sefaz.manifestacao_destinatario_service import (
    DocumentoNaoPertenceEmpresaError,
    ManifestacaoInvalidaError,
)


class FakeCertificadoService:
    def __init__(self):
        self.calls = []

    def cadastrar(self, empresa_id, arquivo_pfx, senha, cnpj_esperado):
        self.calls.append(("cadastrar", empresa_id, arquivo_pfx, senha, cnpj_esperado))
        return SimpleNamespace(
            ativo=True,
            cnpj_titular=cnpj_esperado,
            data_validade=date(2026, 12, 31),
            dias_restantes=120,
        )

    def status(self, empresa_id):
        self.calls.append(("status", empresa_id))
        return SimpleNamespace(
            ativo=True,
            cnpj_titular="12345678000190",
            data_validade=date(2026, 12, 31),
            dias_restantes=120,
        )


class FakeDocumentosRepository:
    def __init__(self):
        self.calls = []

    def listar(self, **kwargs):
        self.calls.append(("listar", kwargs))
        return 2, [
            {
                "id": 10,
                "chave_acesso": "35123456789012345678901234567890123456789012",
                "tipo_documento": "nfeProc",
                "direcao": "recebida",
                "cnpj_emitente": "12345678000190",
                "cnpj_destinatario": "98765432000199",
                "nsu": "000000000000010",
                "data_emissao": date(2026, 8, 1),
                "valor_total": Decimal("123.45"),
                "situacao": "autorizada",
                "manifestacao_status": "pendente",
                "criado_em": datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
                "atualizado_em": datetime(2026, 8, 1, 13, 0, tzinfo=timezone.utc),
            },
            {
                "id": 11,
                "chave_acesso": "35123456789012345678901234567890123456789013",
                "tipo_documento": "nfeProc",
                "direcao": "enviada",
                "cnpj_emitente": "12345678000190",
                "cnpj_destinatario": "98765432000199",
                "nsu": "000000000000011",
                "data_emissao": date(2026, 8, 2),
                "valor_total": Decimal("99.99"),
                "situacao": "autorizada",
                "manifestacao_status": None,
                "criado_em": datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc),
                "atualizado_em": datetime(2026, 8, 2, 13, 0, tzinfo=timezone.utc),
            },
        ]

    def obter_por_id(self, empresa_id, documento_id):
        self.calls.append(("obter_por_id", empresa_id, documento_id))
        if documento_id == 404:
            return None
        return {
            "id": documento_id,
            "chave_acesso": "35123456789012345678901234567890123456789012",
            "tipo_documento": "nfeProc",
            "direcao": "recebida",
            "cnpj_emitente": "12345678000190",
            "cnpj_destinatario": "98765432000199",
            "nsu": "000000000000010",
            "data_emissao": date(2026, 8, 1),
            "valor_total": Decimal("123.45"),
            "situacao": "autorizada",
            "manifestacao_status": "pendente",
            "criado_em": datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
            "atualizado_em": datetime(2026, 8, 1, 13, 0, tzinfo=timezone.utc),
            "xml_armazenado": b"<xml>teste</xml>",
        }


class FakeSyncLogRepository:
    def listar(self, empresa_id, *, limit=50, offset=0):
        return 1, [
            {
                "id": 1,
                "empresa_id": empresa_id,
                "iniciado_em": datetime(2026, 8, 17, 2, 0, tzinfo=timezone.utc),
                "finalizado_em": datetime(2026, 8, 17, 2, 5, tzinfo=timezone.utc),
                "documentos_novos": 3,
                "nsu_inicial": "000000000000000",
                "nsu_final": "000000000000123",
                "status": "sucesso",
                "erro_detalhe": None,
            }
        ]


class FakeManifestacaoService:
    def __init__(self):
        self.calls = []

    def manifestar(self, empresa_id, documento_id, tipo_manifestacao):
        self.calls.append((empresa_id, documento_id, tipo_manifestacao))
        if documento_id == 404:
            raise DocumentoNaoPertenceEmpresaError("Documento nao encontrado.")
        if tipo_manifestacao == "inválida":
            raise ManifestacaoInvalidaError("Tipo invalido.")
        return {"documento_id": documento_id, "manifestacao_status": tipo_manifestacao}


def test_cadastrar_certificado_retorna_status(client, monkeypatch):
    fake_service = FakeCertificadoService()
    monkeypatch.setattr(routes, "CertificadoService", lambda: fake_service)

    response = client.post(
        "/api/sefaz/certificados",
        files={"arquivo": ("certificado.pfx", b"conteudo", "application/x-pkcs12")},
        data={"senha": "1234"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ativo"] is True
    assert payload["cnpj_titular"] == "12345678000190"
    assert fake_service.calls[0][0] == "cadastrar"


def test_cadastrar_certificado_rejeita_extensao_invalida(client):
    response = client.post(
        "/api/sefaz/certificados",
        files={"arquivo": ("certificado.txt", b"conteudo", "text/plain")},
        data={"senha": "1234"},
    )

    assert response.status_code == 400


def test_status_certificado(client, monkeypatch):
    fake_service = FakeCertificadoService()
    monkeypatch.setattr(routes, "CertificadoService", lambda: fake_service)

    response = client.get("/api/sefaz/certificados/status")

    assert response.status_code == 200
    assert response.json()["ativo"] is True


def test_sync_dispara_task(client, monkeypatch):
    chamadas = []

    monkeypatch.setattr(
        routes.celery_app,
        "send_task",
        lambda task_name, args, queue: chamadas.append((task_name, tuple(args), queue)),
    )

    response = client.post("/api/sefaz/sync")

    assert response.status_code == 202
    assert chamadas == [("sefaz_sync_empresa_task", (1, "12345678000190"), "sefaz")]


def test_listar_documentos(client, monkeypatch):
    fake_repo = FakeDocumentosRepository()
    monkeypatch.setattr(routes, "DocumentosRepository", lambda: fake_repo)

    response = client.get("/api/sefaz/documentos?limit=10&offset=0&manifestacao_pendente=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["resultados"][0]["manifestacao_status"] == "pendente"
    assert fake_repo.calls[0][0] == "listar"


def test_obter_documento_traz_xml_em_base64(client, monkeypatch):
    fake_repo = FakeDocumentosRepository()
    monkeypatch.setattr(routes, "DocumentosRepository", lambda: fake_repo)

    response = client.get("/api/sefaz/documentos/10")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == 10
    assert payload["xml_armazenado_base64"] == "PHhtbD50ZXN0ZTwveG1sPg=="


def test_obter_documento_nao_encontrado(client, monkeypatch):
    fake_repo = FakeDocumentosRepository()
    monkeypatch.setattr(routes, "DocumentosRepository", lambda: fake_repo)

    response = client.get("/api/sefaz/documentos/404")

    assert response.status_code == 404


def test_manifestar_documento(client, monkeypatch):
    fake_service = FakeManifestacaoService()
    monkeypatch.setattr(routes, "ManifestacaoDestinatarioService", lambda: fake_service)

    response = client.post(
        "/api/sefaz/documentos/10/manifestacao",
        json={"tipo_manifestacao": "confirmada"},
    )

    assert response.status_code == 200
    assert response.json()["manifestacao_status"] == "confirmada"
    assert fake_service.calls[0] == (1, 10, "confirmada")


def test_manifestar_documento_invalido_retorna_400(client, monkeypatch):
    class BrokenService(FakeManifestacaoService):
        def manifestar(self, empresa_id, documento_id, tipo_manifestacao):
            raise ManifestacaoInvalidaError("Tipo invalido.")

    monkeypatch.setattr(routes, "ManifestacaoDestinatarioService", lambda: BrokenService())

    response = client.post(
        "/api/sefaz/documentos/10/manifestacao",
        json={"tipo_manifestacao": "confirmada"},
    )

    assert response.status_code == 400


def test_listar_sync_log(client, monkeypatch):
    fake_repo = FakeSyncLogRepository()
    monkeypatch.setattr(routes, "SyncLogRepository", lambda: fake_repo)

    response = client.get("/api/sefaz/sync-log")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["resultados"][0]["status"] == "sucesso"
