from datetime import datetime, timedelta, timezone

import pytest


class FakeDocumentosRepository:
    def __init__(self, documentos: dict[int, dict]):
        self.documentos = documentos
        self.atualizados: list[tuple[int, str]] = []

    def obter_por_id(self, empresa_id, documento_id):
        doc = self.documentos.get(documento_id)
        if doc is None or doc.get("empresa_id") != empresa_id:
            return None
        return doc

    def atualizar_manifestacao(self, documento_id, manifestacao_status):
        self.atualizados.append((documento_id, manifestacao_status))

    def listar(self, *, empresa_id, manifestacao_pendente=None, limit=50, offset=0, **_ignorados):
        pendentes = [
            doc
            for doc in self.documentos.values()
            if doc["empresa_id"] == empresa_id and doc.get("manifestacao_status") == "pendente"
        ]
        return len(pendentes), pendentes


def test_manifestar_documento_recebido_atualiza_status():
    from app.services.sefaz.manifestacao_destinatario_service import ManifestacaoDestinatarioService

    repo = FakeDocumentosRepository({10: {"id": 10, "empresa_id": 1, "direcao": "recebida"}})
    servico = ManifestacaoDestinatarioService(documentos_repository=repo)

    resultado = servico.manifestar(empresa_id=1, documento_id=10, tipo_manifestacao="ciencia")

    assert resultado == {"documento_id": 10, "manifestacao_status": "ciencia"}
    assert repo.atualizados == [(10, "ciencia")]


def test_manifestar_tipo_invalido_recusa():
    from app.services.sefaz.manifestacao_destinatario_service import (
        ManifestacaoDestinatarioService,
        ManifestacaoInvalidaError,
    )

    repo = FakeDocumentosRepository({10: {"id": 10, "empresa_id": 1, "direcao": "recebida"}})
    servico = ManifestacaoDestinatarioService(documentos_repository=repo)

    with pytest.raises(ManifestacaoInvalidaError):
        servico.manifestar(empresa_id=1, documento_id=10, tipo_manifestacao="tipo-invalido")


def test_manifestar_documento_emitido_recusa():
    from app.services.sefaz.manifestacao_destinatario_service import (
        ManifestacaoDestinatarioService,
        ManifestacaoInvalidaError,
    )

    repo = FakeDocumentosRepository({10: {"id": 10, "empresa_id": 1, "direcao": "emitida"}})
    servico = ManifestacaoDestinatarioService(documentos_repository=repo)

    with pytest.raises(ManifestacaoInvalidaError, match="recebidos"):
        servico.manifestar(empresa_id=1, documento_id=10, tipo_manifestacao="ciencia")


def test_manifestar_documento_inexistente_ou_de_outra_empresa_recusa():
    from app.services.sefaz.manifestacao_destinatario_service import (
        DocumentoNaoPertenceEmpresaError,
        ManifestacaoDestinatarioService,
    )

    repo = FakeDocumentosRepository({10: {"id": 10, "empresa_id": 2, "direcao": "recebida"}})
    servico = ManifestacaoDestinatarioService(documentos_repository=repo)

    with pytest.raises(DocumentoNaoPertenceEmpresaError):
        servico.manifestar(empresa_id=1, documento_id=10, tipo_manifestacao="ciencia")


def test_listar_pendentes_proximas_do_prazo_filtra_por_dias_restantes():
    from app.services.sefaz.manifestacao_destinatario_service import (
        ManifestacaoDestinatarioService,
        PRAZO_MANIFESTACAO_DIAS,
    )

    hoje = datetime.now(timezone.utc)
    documentos = {
        1: {
            "id": 1,
            "empresa_id": 1,
            "manifestacao_status": "pendente",
            "data_emissao": hoje - timedelta(days=PRAZO_MANIFESTACAO_DIAS - 1),
        },
        2: {
            "id": 2,
            "empresa_id": 1,
            "manifestacao_status": "pendente",
            "data_emissao": hoje - timedelta(days=1),
        },
    }
    repo = FakeDocumentosRepository(documentos)
    servico = ManifestacaoDestinatarioService(documentos_repository=repo)

    alerta = servico.listar_pendentes_proximas_do_prazo(empresa_id=1, dias_restantes_max=3)

    assert len(alerta) == 1
    assert alerta[0]["id"] == 1


def test_montar_texto_alerta_prazo_vencido():
    from app.services.sefaz.manifestacao_destinatario_service import montar_texto_alerta_prazo

    texto = montar_texto_alerta_prazo("35260812345678000190550010000000011234567890", dias_restantes=0)
    assert "vencido" in texto


def test_montar_texto_alerta_prazo_nao_vencido():
    from app.services.sefaz.manifestacao_destinatario_service import montar_texto_alerta_prazo

    texto = montar_texto_alerta_prazo("35260812345678000190550010000000011234567890", dias_restantes=2)
    assert "2 dias" in texto
