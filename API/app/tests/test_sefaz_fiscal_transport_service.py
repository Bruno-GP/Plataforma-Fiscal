from __future__ import annotations

from types import SimpleNamespace

from app.services.sefaz.sefaz_fiscal_transport_service import SefazFiscalTransportService


class FakeDocumentosRepository:
    def __init__(self):
        self.marcados: list[int] = []

    def marcar_processado_fiscal(self, documento_id: int) -> None:
        self.marcados.append(documento_id)


def _documento(**overrides):
    base = {
        "id": 1,
        "chave_acesso": "35123456789012345678901234567890123456789012",
        "direcao": "emitida",
        "xml_armazenado": b"<nfeProc>xml</nfeProc>",
        "processado_fiscal_em": None,
    }
    base.update(overrides)
    return base


def test_ignora_documento_recebida():
    repo = FakeDocumentosRepository()
    service = SefazFiscalTransportService(documentos_repository=repo)

    total = service.transportar_documentos(
        empresa_id=1,
        cnpj_empresa="12345678000190",
        documentos=[_documento(direcao="recebida")],
    )

    assert total == 0
    assert repo.marcados == []


def test_ignora_documento_sem_xml_armazenado():
    repo = FakeDocumentosRepository()
    service = SefazFiscalTransportService(documentos_repository=repo)

    total = service.transportar_documentos(
        empresa_id=1,
        cnpj_empresa="12345678000190",
        documentos=[_documento(xml_armazenado=None)],
    )

    assert total == 0
    assert repo.marcados == []


def test_ignora_documento_ja_processado():
    repo = FakeDocumentosRepository()
    service = SefazFiscalTransportService(documentos_repository=repo)

    total = service.transportar_documentos(
        empresa_id=1,
        cnpj_empresa="12345678000190",
        documentos=[_documento(processado_fiscal_em="2026-08-18T00:00:00Z")],
    )

    assert total == 0
    assert repo.marcados == []


def test_sucesso_marca_documentos_processados(monkeypatch):
    def fake_executar(self, cnpj_emitente, xmls_importados):
        assert cnpj_emitente == "12345678000190"
        assert xmls_importados == [
            (1, "35123456789012345678901234567890123456789012", b"<nfeProc>xml</nfeProc>")
        ]
        return SimpleNamespace(status="processado", erros=[]), [1]

    monkeypatch.setattr(
        "app.services.sefaz.sefaz_fiscal_transport_service.ProcessarNFeService.executar_xmls_importados",
        fake_executar,
    )

    repo = FakeDocumentosRepository()
    service = SefazFiscalTransportService(documentos_repository=repo)

    total = service.transportar_documentos(
        empresa_id=1,
        cnpj_empresa="12345678000190",
        documentos=[_documento()],
    )

    assert total == 1
    assert repo.marcados == [1]


def test_falha_no_processamento_nao_marca_e_nao_propaga(monkeypatch):
    def fake_executar(self, cnpj_emitente, xmls_importados):
        return SimpleNamespace(status="erro", erros=[{"mensagem": "XML invalido"}]), []

    monkeypatch.setattr(
        "app.services.sefaz.sefaz_fiscal_transport_service.ProcessarNFeService.executar_xmls_importados",
        fake_executar,
    )

    repo = FakeDocumentosRepository()
    service = SefazFiscalTransportService(documentos_repository=repo)

    total = service.transportar_documentos(
        empresa_id=1,
        cnpj_empresa="12345678000190",
        documentos=[_documento()],
    )

    assert total == 0
    assert repo.marcados == []


def test_xml_armazenado_como_memoryview_e_convertido_para_bytes(monkeypatch):
    capturado = {}

    def fake_executar(self, cnpj_emitente, xmls_importados):
        capturado["xmls"] = xmls_importados
        return SimpleNamespace(status="processado", erros=[]), [1]

    monkeypatch.setattr(
        "app.services.sefaz.sefaz_fiscal_transport_service.ProcessarNFeService.executar_xmls_importados",
        fake_executar,
    )

    repo = FakeDocumentosRepository()
    service = SefazFiscalTransportService(documentos_repository=repo)

    service.transportar_documentos(
        empresa_id=1,
        cnpj_empresa="12345678000190",
        documentos=[_documento(xml_armazenado=memoryview(b"<nfeProc>xml</nfeProc>"))],
    )

    assert capturado["xmls"][0][2] == b"<nfeProc>xml</nfeProc>"
    assert isinstance(capturado["xmls"][0][2], bytes)
