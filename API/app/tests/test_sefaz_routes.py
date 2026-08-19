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
                "processado_fiscal_em": None,
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
                "processado_fiscal_em": None,
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
            "processado_fiscal_em": None,
            "xml_armazenado": b"<xml>teste</xml>",
        }


class FakeSyncLogRepository:
    ultimo_sucesso_com_documentos = None

    def obter_ultimo_sucesso_com_documentos(self, empresa_id):
        return self.ultimo_sucesso_com_documentos

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

    monkeypatch.setattr(routes, "SyncLogRepository", lambda: FakeSyncLogRepository())
    monkeypatch.setattr(
        routes.celery_app,
        "send_task",
        lambda task_name, args, queue: chamadas.append((task_name, tuple(args), queue)),
    )

    response = client.post("/api/sefaz/sync")

    assert response.status_code == 202
    assert chamadas == [("sefaz_sync_empresa_task", (1, "12345678000190"), "sefaz")]


def test_sync_bloqueia_por_uma_hora_apos_sucesso_com_documentos(client, monkeypatch):
    chamadas = []

    class FakeRepo(FakeSyncLogRepository):
        ultimo_sucesso_com_documentos = {
            "id": 1,
            "empresa_id": 1,
            "finalizado_em": datetime(2026, 8, 19, 12, 30, tzinfo=timezone.utc),
            "documentos_novos": 4,
        }

    monkeypatch.setattr(routes, "SyncLogRepository", lambda: FakeRepo())
    monkeypatch.setattr(routes, "_utc_now", lambda: datetime(2026, 8, 19, 13, 0, tzinfo=timezone.utc))
    monkeypatch.setattr(
        routes.celery_app,
        "send_task",
        lambda task_name, args, queue: chamadas.append((task_name, tuple(args), queue)),
    )

    response = client.post("/api/sefaz/sync")

    assert response.status_code == 429
    assert response.headers["retry-after"] == "1800"
    assert chamadas == []


def test_sync_status_retorna_cooldown(client, monkeypatch):
    class FakeRepo(FakeSyncLogRepository):
        ultimo_sucesso_com_documentos = {
            "id": 1,
            "empresa_id": 1,
            "finalizado_em": datetime(2026, 8, 19, 12, 30, tzinfo=timezone.utc),
            "documentos_novos": 4,
        }

    monkeypatch.setattr(routes, "SyncLogRepository", lambda: FakeRepo())
    monkeypatch.setattr(routes, "_utc_now", lambda: datetime(2026, 8, 19, 13, 0, tzinfo=timezone.utc))

    response = client.get("/api/sefaz/sync-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["disponivel"] is False
    assert payload["segundos_restantes"] == 1800
    assert payload["documentos_novos_ultima_sync"] == 4


def test_listar_documentos(client, monkeypatch):
    fake_repo = FakeDocumentosRepository()
    monkeypatch.setattr(routes, "DocumentosRepository", lambda: fake_repo)

    response = client.get("/api/sefaz/documentos?limit=10&offset=0&manifestacao_pendente=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["resultados"][0]["manifestacao_status"] == "pendente"
    assert fake_repo.calls[0][0] == "listar"


def test_listar_documentos_expoe_processado_fiscal_em(client, monkeypatch):
    class FakeRepo:
        def listar(self, **kwargs):
            return 1, [
                {
                    "id": 20,
                    "chave_acesso": "35123456789012345678901234567890123456789099",
                    "tipo_documento": "nfeProc",
                    "direcao": "emitida",
                    "cnpj_emitente": "12345678000190",
                    "cnpj_destinatario": None,
                    "nsu": "000000000000020",
                    "data_emissao": date(2026, 8, 5),
                    "valor_total": Decimal("50.00"),
                    "situacao": "autorizada",
                    "manifestacao_status": None,
                    "criado_em": datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
                    "atualizado_em": datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
                    "processado_fiscal_em": datetime(2026, 8, 5, 13, 0, tzinfo=timezone.utc),
                }
            ]

    monkeypatch.setattr(routes, "DocumentosRepository", lambda: FakeRepo())

    response = client.get("/api/sefaz/documentos")

    assert response.status_code == 200
    resultado = response.json()["resultados"][0]
    assert resultado["processado_fiscal_em"] is not None


def test_listar_documentos_processado_fiscal_em_ausente_vira_none(client, monkeypatch):
    fake_repo = FakeDocumentosRepository()
    monkeypatch.setattr(routes, "DocumentosRepository", lambda: fake_repo)

    response = client.get("/api/sefaz/documentos")

    assert response.status_code == 200
    resultado = response.json()["resultados"][0]
    assert resultado["processado_fiscal_em"] is None


def test_listar_documentos_converte_data_emissao_datetime_para_date(client, monkeypatch):
    class FakeRepo:
        def listar(self, **kwargs):
            return 1, [
                {
                    "id": 21,
                    "chave_acesso": "35123456789012345678901234567890123456789100",
                    "tipo_documento": "nfeProc",
                    "direcao": "emitida",
                    "cnpj_emitente": "12345678000190",
                    "cnpj_destinatario": None,
                    "nsu": "000000000000021",
                    "data_emissao": datetime(2026, 5, 10, 9, 30, tzinfo=timezone.utc),
                    "valor_total": Decimal("50.00"),
                    "situacao": "autorizada",
                    "manifestacao_status": None,
                    "criado_em": datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
                    "atualizado_em": datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
                    "processado_fiscal_em": None,
                }
            ]

    monkeypatch.setattr(routes, "DocumentosRepository", lambda: FakeRepo())

    response = client.get("/api/sefaz/documentos")

    assert response.status_code == 200
    assert response.json()["resultados"][0]["data_emissao"] == "2026-05-10"


def test_listar_documentos_com_ano_calcula_intervalo(client, monkeypatch):
    fake_repo = FakeDocumentosRepository()
    monkeypatch.setattr(routes, "DocumentosRepository", lambda: fake_repo)

    response = client.get("/api/sefaz/documentos", params={"ano": 2026})

    assert response.status_code == 200
    _, kwargs = fake_repo.calls[0]
    assert kwargs["data_inicio"] == date(2026, 1, 1)
    assert kwargs["data_fim"] == date(2026, 12, 31)


def test_listar_documentos_ano_com_data_inicio_falha_400(client, monkeypatch):
    fake_repo = FakeDocumentosRepository()
    monkeypatch.setattr(routes, "DocumentosRepository", lambda: fake_repo)

    response = client.get(
        "/api/sefaz/documentos",
        params={"ano": 2026, "data_inicio": "2026-01-01"},
    )

    assert response.status_code == 400
    assert fake_repo.calls == []


def test_listar_documentos_ano_fora_do_intervalo_falha_422(client, monkeypatch):
    fake_repo = FakeDocumentosRepository()
    monkeypatch.setattr(routes, "DocumentosRepository", lambda: fake_repo)

    response = client.get("/api/sefaz/documentos", params={"ano": 1999})

    assert response.status_code == 422


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
