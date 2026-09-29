import pytest

from app.domain.sefaz.doc_parser import (
    DocumentoParseInvalidoError,
    calcular_direcao,
    parse_documento,
)


def test_parse_documento_resnfe_extraindo_campos_principais():
    xml_bytes = b"""
    <resNFe xmlns="http://www.portalfiscal.inf.br/nfe">
        <chNFe>35260812345678000190550010000012341000012345</chNFe>
        <CNPJ>11223344000155</CNPJ>
        <CNPJDest>12345678000190</CNPJDest>
        <dEmi>20260817</dEmi>
        <vNF>321.45</vNF>
        <cSitNFe>100</cSitNFe>
    </resNFe>
    """

    documento = parse_documento("resNFe", xml_bytes)

    assert documento.chave_acesso == "35260812345678000190550010000012341000012345"
    assert documento.tipo_documento == "resNFe"
    assert documento.cnpj_emitente == "11223344000155"
    assert documento.cnpj_destinatario == "12345678000190"
    assert documento.data_emissao == "20260817"
    assert documento.valor_total == "321.45"
    assert documento.situacao == "100"
    assert documento.tipo_evento is None
    assert documento.protocolo is None


def test_parse_documento_resevento_extraindo_evento_e_protocolo():
    xml_bytes = b"""
    <resEvento xmlns="http://www.portalfiscal.inf.br/nfe">
        <chNFe>35260812345678000190550010000012341000012345</chNFe>
        <CNPJDest>12345678000190</CNPJDest>
        <tpEvento>110111</tpEvento>
        <nProt>135791357913579</nProt>
        <dhRegEvento>2026-08-17T12:34:56-03:00</dhRegEvento>
        <cStat>135</cStat>
    </resEvento>
    """

    documento = parse_documento("resEvento", xml_bytes)

    assert documento.chave_acesso == "35260812345678000190550010000012341000012345"
    assert documento.tipo_documento == "resEvento"
    assert documento.cnpj_emitente == "12345678000190"
    assert documento.cnpj_destinatario == "12345678000190"
    assert documento.data_emissao == "2026-08-17T12:34:56-03:00"
    assert documento.valor_total is None
    assert documento.situacao == "135"
    assert documento.tipo_evento == "110111"
    assert documento.protocolo == "135791357913579"


def test_parse_documento_nfeproc_extraindo_protocolo_e_destinatario():
    xml_bytes = b"""
    <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
        <NFe>
            <infNFe>
                <chNFe>35260812345678000190550010000012341000012345</chNFe>
                <ide>
                    <dhEmi>2026-08-17T10:00:00-03:00</dhEmi>
                </ide>
                <emit>
                    <CNPJ>11223344000155</CNPJ>
                </emit>
                <dest>
                    <CNPJ>12345678000190</CNPJ>
                </dest>
                <total>
                    <ICMSTot>
                        <vNF>987.65</vNF>
                    </ICMSTot>
                </total>
            </infNFe>
        </NFe>
        <protNFe>
            <infProt>
                <cStat>100</cStat>
                <nProt>987654321098765</nProt>
            </infProt>
        </protNFe>
    </nfeProc>
    """

    documento = parse_documento("nfeProc", xml_bytes)

    assert documento.chave_acesso == "35260812345678000190550010000012341000012345"
    assert documento.tipo_documento == "nfeProc"
    assert documento.cnpj_emitente == "11223344000155"
    assert documento.cnpj_destinatario == "12345678000190"
    assert documento.data_emissao == "2026-08-17T10:00:00-03:00"
    assert documento.valor_total == "987.65"
    assert documento.situacao == "100"
    assert documento.tipo_evento is None
    assert documento.protocolo == "987654321098765"


def test_calcular_direcao_respeita_cnpj_normalizado():
    assert calcular_direcao("11.223.344/0001-55", "11223344000155") == "emitida"
    assert calcular_direcao("11.223.344/0001-55", "12345678000190") == "recebida"


def test_parse_documento_levanta_erro_quando_chave_faltar():
    xml_bytes = b"""
    <resNFe xmlns="http://www.portalfiscal.inf.br/nfe">
        <CNPJ>11223344000155</CNPJ>
    </resNFe>
    """

    with pytest.raises(DocumentoParseInvalidoError, match="Chave de acesso"):
        parse_documento("resNFe", xml_bytes)
