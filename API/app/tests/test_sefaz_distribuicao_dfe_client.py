import base64
import gzip

import pytest


NS = 'xmlns="http://www.portalfiscal.inf.br/nfe"'


def _doc_zip(schema: str, nsu: str, xml_interno: str) -> str:
    comprimido = gzip.compress(xml_interno.encode("utf-8"))
    return base64.b64encode(comprimido).decode("ascii")


def test_decodificar_doc_zip_roundtrip():
    from app.services.sefaz.distribuicao_dfe_client import _decodificar_doc_zip

    original = b"<resNFe>conteudo</resNFe>"
    codificado = base64.b64encode(gzip.compress(original)).decode("ascii")

    assert _decodificar_doc_zip(codificado) == original


def test_decodificar_doc_zip_invalido_falha():
    from app.services.sefaz.distribuicao_dfe_client import SefazRespostaInvalidaError, _decodificar_doc_zip

    with pytest.raises(SefazRespostaInvalidaError, match="docZip"):
        _decodificar_doc_zip("nao-e-base64-valido-!!!")


def test_parse_resposta_com_documentos():
    from app.services.sefaz.distribuicao_dfe_client import _parse_resposta_distribuicao

    doc_zip_1 = _doc_zip("resNFe", "000000000000001", "<resNFe>a</resNFe>")
    doc_zip_2 = _doc_zip("resEvento", "000000000000002", "<resEvento>b</resEvento>")

    xml_resposta = f"""<retDistDFeInt {NS} versao="1.35">
        <tpAmb>1</tpAmb>
        <cStat>138</cStat>
        <xMotivo>Documento(s) localizado(s)</xMotivo>
        <ultNSU>000000000000002</ultNSU>
        <maxNSU>000000000000010</maxNSU>
        <loteDistDFeInt>
            <docZip NSU="000000000000001" schema="resNFe_v1.01.xsd">{doc_zip_1}</docZip>
            <docZip NSU="000000000000002" schema="resEvento_v1.00.xsd">{doc_zip_2}</docZip>
        </loteDistDFeInt>
    </retDistDFeInt>""".encode("utf-8")

    resposta = _parse_resposta_distribuicao(xml_resposta)

    assert resposta.cstat == 138
    assert resposta.ultimo_nsu == "000000000000002"
    assert resposta.max_nsu == "000000000000010"
    assert len(resposta.documentos) == 2
    assert resposta.documentos[0].schema == "resNFe"
    assert resposta.documentos[0].xml_bytes == b"<resNFe>a</resNFe>"
    assert resposta.documentos[1].schema == "resEvento"


def test_parse_resposta_sem_documentos_cstat_137():
    from app.services.sefaz.distribuicao_dfe_client import _parse_resposta_distribuicao

    xml_resposta = f"""<retDistDFeInt {NS} versao="1.35">
        <tpAmb>1</tpAmb>
        <cStat>137</cStat>
        <xMotivo>Nenhum documento localizado</xMotivo>
        <ultNSU>000000000000005</ultNSU>
        <maxNSU>000000000000005</maxNSU>
    </retDistDFeInt>""".encode("utf-8")

    resposta = _parse_resposta_distribuicao(xml_resposta)

    assert resposta.cstat == 137
    assert resposta.documentos == []


def test_parse_resposta_sem_cstat_falha():
    from app.services.sefaz.distribuicao_dfe_client import SefazRespostaInvalidaError, _parse_resposta_distribuicao

    with pytest.raises(SefazRespostaInvalidaError, match="cStat"):
        _parse_resposta_distribuicao(f'<retDistDFeInt {NS}></retDistDFeInt>'.encode("utf-8"))


def test_parse_resposta_xml_invalido_falha():
    from app.services.sefaz.distribuicao_dfe_client import SefazRespostaInvalidaError, _parse_resposta_distribuicao

    with pytest.raises(SefazRespostaInvalidaError):
        _parse_resposta_distribuicao(b"<nao-fecha>")


def test_consultar_sucesso_delega_para_transmissor(monkeypatch):
    from app.services.sefaz.distribuicao_dfe_client import DistribuicaoDFeClient

    doc_zip_1 = _doc_zip("resNFe", "000000000000001", "<resNFe>a</resNFe>")
    xml_resposta = f"""<retDistDFeInt {NS} versao="1.35">
        <tpAmb>1</tpAmb>
        <cStat>138</cStat>
        <ultNSU>000000000000001</ultNSU>
        <maxNSU>000000000000010</maxNSU>
        <loteDistDFeInt>
            <docZip NSU="000000000000001" schema="resNFe_v1.01.xsd">{doc_zip_1}</docZip>
        </loteDistDFeInt>
    </retDistDFeInt>""".encode("utf-8")

    class FakeRetorno:
        content = f"<soapEnvelope><soapBody>{xml_resposta.decode('utf-8')}</soapBody></soapEnvelope>".encode(
            "utf-8"
        )

    class FakeRespostaSoap:
        retorno = FakeRetorno()

    class FakeTransmissor:
        def consultar_distribuicao(self, cnpj_cpf, ultimo_nsu):
            assert cnpj_cpf == "12345678000190"
            assert ultimo_nsu == "000000000000000"
            return FakeRespostaSoap()

    cliente = DistribuicaoDFeClient(b"pfx", "senha", "12345678000190", ambiente=1)
    monkeypatch.setattr(cliente, "_montar_transmissor", lambda: FakeTransmissor())

    resposta = cliente.consultar("000000000000000")

    assert resposta.cstat == 138
    assert len(resposta.documentos) == 1


def test_consultar_erro_de_transporte_vira_sefaz_indisponivel(monkeypatch):
    from app.services.sefaz.distribuicao_dfe_client import DistribuicaoDFeClient, SefazIndisponivelError

    class FakeTransmissorComErro:
        def consultar_distribuicao(self, cnpj_cpf, ultimo_nsu):
            raise TimeoutError("timeout na conexao com o Ambiente Nacional")

    cliente = DistribuicaoDFeClient(b"pfx", "senha", "12345678000190", ambiente=1)
    monkeypatch.setattr(cliente, "_montar_transmissor", lambda: FakeTransmissorComErro())

    with pytest.raises(SefazIndisponivelError, match="Falha ao consultar"):
        cliente.consultar("000000000000000")
