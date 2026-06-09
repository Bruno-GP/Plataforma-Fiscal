from xml.etree import ElementTree as ET

import pytest

from app.domain.nfe.extractor import NFeExtractor
from app.domain.nfe.normalization import normalizar_nome_produto
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


@pytest.mark.parametrize(
    ("xprod", "descricao_esperada"),
    [
        (
            "#0#61044300#G2484 VESTIDO VISCOSE FIO TINTO C/ ELASTANO G 313",
            "VESTIDO VISCOSE FIO TINTO C/ ELASTANO G 313",
        ),
        (
            "#0#62044300#G2327 VESTIDO VISCOSE C/ POLIAMIDA 42",
            "VESTIDO VISCOSE C/ POLIAMIDA 42",
        ),
        (
            "#0#62044300#G2494/02 VESTIDO VISCOSE C/ ALGODAO E LINHO 44 296",
            "VESTIDO VISCOSE C/ ALGODAO E LINHO 44 296",
        ),
        (
            "G2695 CALCA RELAX 100% LINHO COS ALTO 40 02",
            "CALCA RELAX 100% LINHO COS ALTO 40 02",
        ),
        (
            "G2631 BERMUDA LINHO C/VISCOSE 40 2335",
            "BERMUDA LINHO C/VISCOSE 40 2335",
        ),
        (
            "G2717 VESTIDO MIDI POLIAMIDA C/ VISCOSE SHINE 38 0",
            "VESTIDO MIDI POLIAMIDA C/ VISCOSE SHINE 38 0",
        ),
        (
            "VESTIDO VISCOSE FIO TINTO C/ ELASTANO G 313",
            "VESTIDO VISCOSE FIO TINTO C/ ELASTANO G 313",
        ),
    ],
)
def test_normalizar_nome_produto_remove_prefixos_tecnicos(xprod, descricao_esperada):
    assert normalizar_nome_produto(xprod) == descricao_esperada


@pytest.mark.parametrize(
    ("xprod", "descricao_esperada"),
    [
        (
            "#0#61044300#G2484 VESTIDO VISCOSE FIO TINTO C/ ELASTANO G 313",
            "VESTIDO VISCOSE FIO TINTO C/ ELASTANO G 313",
        ),
        (
            "61044300 G2484 VESTIDO VISCOSE FIO TINTO C/ ELASTANO G 313",
            "VESTIDO VISCOSE FIO TINTO C/ ELASTANO G 313",
        ),
        (
            "VESTIDO VISCOSE FIO TINTO C/ ELASTANO G 313",
            "VESTIDO VISCOSE FIO TINTO C/ ELASTANO G 313",
        ),
    ],
)
def test_extractor_normaliza_xprod_com_prefixos_tecnicos(monkeypatch, xprod, descricao_esperada):
    monkeypatch.setattr(
        "app.domain.nfe.extractor._carregar_municipios",
        lambda: (
            {"3550308": ("Sao Paulo", "SP")},
            {"SAO PAULO": "Sao Paulo"},
            {"SAO PAULO": "SP"},
        ),
    )

    root = ET.fromstring(
        f"""
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
                  <xProd>{xprod}</xProd>
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
                caminho="nfe.xml",
                xml=root,
                emitente_cnpj="12345678000199",
                emitente_nome="Empresa Teste",
            )
        ]
    )

    assert len(notas) == 1
    assert notas[0].itens[0].descricao == descricao_esperada
