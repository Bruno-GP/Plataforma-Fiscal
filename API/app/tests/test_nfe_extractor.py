from xml.etree import ElementTree as ET

from app.domain.nfe.extractor import NFeExtractor
from app.domain.nfe.xml_models import XmlNFe


def test_nfce_sem_destinatario_usa_cidade_uf_do_emitente(monkeypatch):
    monkeypatch.setattr(
        "app.domain.nfe.extractor._carregar_municipios",
        lambda: (
            {"3550308": ("Sao Paulo", "SP")},
            {"SAO PAULO": "Sao Paulo"},
            {"SAO PAULO": "SP"},
        ),
    )

    root = ET.fromstring(
        """
        <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
          <NFe>
            <infNFe Id="NFe35260512345678000199650010000000011000000010">
              <ide>
                <cUF>35</cUF>
                <natOp>Venda</natOp>
                <mod>65</mod>
                <serie>1</serie>
                <nNF>1</nNF>
                <dhEmi>2026-05-20T10:00:00-03:00</dhEmi>
              </ide>
              <emit>
                <CNPJ>12345678000199</CNPJ>
                <xNome>Empresa Teste</xNome>
                <enderEmit>
                  <cMun>3550308</cMun>
                  <xMun>Sao Paulo</xMun>
                  <UF>SP</UF>
                </enderEmit>
              </emit>
              <det nItem="1">
                <prod>
                  <cProd>001</cProd>
                  <xProd>Produto Teste</xProd>
                  <NCM>12345678</NCM>
                  <CFOP>5102</CFOP>
                  <uCom>UN</uCom>
                  <qCom>1.0000</qCom>
                  <vUnCom>10.00</vUnCom>
                  <vProd>10.00</vProd>
                </prod>
              </det>
              <total>
                <ICMSTot>
                  <vProd>10.00</vProd>
                  <vDesc>0.00</vDesc>
                  <vFrete>0.00</vFrete>
                  <vICMS>0.00</vICMS>
                  <vIPI>0.00</vIPI>
                  <vPIS>0.00</vPIS>
                  <vCOFINS>0.00</vCOFINS>
                  <vNF>10.00</vNF>
                </ICMSTot>
              </total>
            </infNFe>
          </NFe>
        </nfeProc>
        """
    )

    notas = NFeExtractor().extrair(
        [
            XmlNFe(
                caminho="nfce.xml",
                xml=root,
                emitente_cnpj="12345678000199",
                emitente_nome="Empresa Teste",
            )
        ]
    )

    assert len(notas) == 1
    assert notas[0].modelo == "65"
    assert notas[0].destinatario_nome == "Consumidor Final"
    assert notas[0].destinatario_cidade == "Sao Paulo"
    assert notas[0].destinatario_uf == "SP"
