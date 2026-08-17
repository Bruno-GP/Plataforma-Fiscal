"""Unico modulo do dominio sefaz que importa nfelib/erpbrasil (ADR 0001).

O restante do dominio depende apenas do contrato desta classe
(`RespostaDistribuicao` e `DocumentoBruto`), nunca das libs diretamente.
"""

from __future__ import annotations

import base64
import gzip
from dataclasses import dataclass

from defusedxml import ElementTree as ET

AMBIENTE_PRODUCAO = 1
AMBIENTE_HOMOLOGACAO = 2

NFE_NAMESPACE = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

_SCHEMA_PREFIXO_PARA_TIPO = {
    "resNFe": "resNFe",
    "resEvento": "resEvento",
    "procNFe": "nfeProc",
}


class SefazIndisponivelError(ConnectionError):
    """Falha de rede/SOAP ao consultar o Ambiente Nacional."""


class SefazRespostaInvalidaError(RuntimeError):
    pass


@dataclass(frozen=True)
class DocumentoBruto:
    schema: str
    nsu: str
    xml_bytes: bytes


@dataclass(frozen=True)
class RespostaDistribuicao:
    cstat: int
    ultimo_nsu: str
    max_nsu: str
    documentos: list[DocumentoBruto]


def _decodificar_doc_zip(doc_zip_base64: str) -> bytes:
    try:
        return gzip.decompress(base64.b64decode(doc_zip_base64))
    except (OSError, ValueError) as exc:
        raise SefazRespostaInvalidaError(f"docZip invalido: {exc}") from exc


def _texto(raiz: ET.Element, caminho: str) -> str | None:
    elemento = raiz.find(caminho, NFE_NAMESPACE)
    if elemento is None or elemento.text is None:
        return None

    valor = elemento.text.strip()
    return valor or None


def _schema_para_tipo_documento(schema_attr: str) -> str:
    prefixo = schema_attr.split("_", 1)[0] if schema_attr else ""
    return _SCHEMA_PREFIXO_PARA_TIPO.get(prefixo, prefixo)


def _parse_resposta_distribuicao(xml_resposta: bytes) -> RespostaDistribuicao:
    try:
        raiz = ET.fromstring(xml_resposta)
    except ET.ParseError as exc:
        raise SefazRespostaInvalidaError(f"Resposta distDFeInt nao e XML valido: {exc}") from exc

    cstat_texto = _texto(raiz, "nfe:cStat")
    if not cstat_texto:
        raise SefazRespostaInvalidaError("Resposta distDFeInt sem cStat.")

    documentos: list[DocumentoBruto] = []
    for doc_zip in raiz.findall("nfe:loteDistDFeInt/nfe:docZip", NFE_NAMESPACE):
        schema_attr = doc_zip.get("schema", "")
        documentos.append(
            DocumentoBruto(
                schema=_schema_para_tipo_documento(schema_attr),
                nsu=doc_zip.get("NSU", ""),
                xml_bytes=_decodificar_doc_zip(doc_zip.text or ""),
            )
        )

    return RespostaDistribuicao(
        cstat=int(cstat_texto),
        ultimo_nsu=_texto(raiz, "nfe:ultNSU") or "000000000000000",
        max_nsu=_texto(raiz, "nfe:maxNSU") or "000000000000000",
        documentos=documentos,
    )


class DistribuicaoDFeClient:
    """Consulta `distDFeInt` para uma empresa.

    O certificado .pfx/.p12 já chega em memória, descriptografado pelo service.
    """

    def __init__(
        self,
        certificado_pfx: bytes,
        senha: str,
        cnpj: str,
        ambiente: int,
        uf_autor: str = "AN",
    ) -> None:
        self.certificado_pfx = certificado_pfx
        self.senha = senha
        self.cnpj = cnpj
        self.ambiente = ambiente
        self.uf_autor = uf_autor

    def _montar_transmissor(self):
        # Import lazily to keep the rest of the module testable without the fiscal libs.
        from erpbrasil.assinatura.assinatura import Assinatura
        from erpbrasil.edoc.nfe import NFe as NFeTransmissor
        from erpbrasil.transmissao import TransmissaoSOAP
        import requests

        certificado = Assinatura(self.certificado_pfx, self.senha)
        sessao = requests.Session()
        transmissao = TransmissaoSOAP(certificado, sessao)
        return NFeTransmissor(transmissao=transmissao, ambiente=self.ambiente, uf=self.uf_autor)

    def consultar(self, ultimo_nsu: str) -> RespostaDistribuicao:
        transmissor = self._montar_transmissor()
        try:
            resposta_soap = transmissor.consulta_distribuicao(cnpj=self.cnpj, ult_nsu=ultimo_nsu)
        except Exception as exc:
            raise SefazIndisponivelError(f"Falha ao consultar distDFeInt: {exc}") from exc

        return _parse_resposta_distribuicao(resposta_soap.content)
