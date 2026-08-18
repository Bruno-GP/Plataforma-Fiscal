import os
from typing import List

from defusedxml import ElementTree as ET

from app.domain.nfe.xml_models import XmlNFe

NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
AUTORIZADOS_NFE = {"100", "150"}


def _local_name(tag: str) -> str:
    return (tag or "").split("}")[-1]


def _eh_xml_evento(root: ET.Element) -> bool:
    nomes_evento = {
        "procEventoNFe",
        "evento",
        "envEvento",
        "retEvento",
        "procCCeNFe",
    }
    if _local_name(root.tag) in nomes_evento:
        return True

    return root.find(".//nfe:infEvento", NS) is not None


def _eh_xml_nfse(root: ET.Element) -> bool:
    nomes_nfse = {"CompNfse", "Nfse", "NFS-e", "GerarNfseResposta", "ConsultarNfseResposta"}
    if _local_name(root.tag) in nomes_nfse:
        return True

    return root.find(".//InfNfse") is not None or root.find(".//CompNfse") is not None


def classificar_xml_processavel(root: ET.Element) -> tuple[bool, str]:
    if _eh_xml_evento(root):
        return False, "XML de evento nao e processavel como documento fiscal."

    inf_nfe = root.find(".//nfe:infNFe", NS)
    if inf_nfe is not None:
        cstat = (root.findtext(".//nfe:protNFe/nfe:infProt/nfe:cStat", default="", namespaces=NS) or "").strip()
        if cstat not in AUTORIZADOS_NFE:
            return False, "NFe/NFCe sem protocolo autorizado."
        return True, "NFe/NFCe autorizada."

    if _eh_xml_nfse(root):
        return True, "NFSe identificada."

    return False, "XML nao corresponde a um documento fiscal autorizado suportado."


def extrair_emitente_xml(root: ET.Element) -> tuple[str | None, str | None]:
    emit = root.find(".//nfe:emit", NS)
    if emit is not None:
        cnpj = emit.findtext("nfe:CNPJ", default="", namespaces=NS).strip()
        nome = emit.findtext("nfe:xNome", default="", namespaces=NS).strip()
        return (cnpj or None, nome or None)

    cnpj_nfse = _buscar_texto_por_tags(
        root,
        [
            "PrestadorServico/IdentificacaoPrestador/Cnpj",
            "PrestadorServico/Cnpj",
            "CpfCnpj/Cnpj",
            "Cnpj",
        ],
    )
    nome_nfse = _buscar_texto_por_tags(
        root,
        ["PrestadorServico/RazaoSocial", "PrestadorServico/NomeFantasia", "RazaoSocial"],
    )
    return (cnpj_nfse, nome_nfse)


def _buscar_texto_por_tags(root: ET.Element, caminhos: list[str]) -> str | None:
    for caminho in caminhos:
        candidato = root.find(f".//{caminho}")
        if candidato is not None and candidato.text:
            valor = candidato.text.strip()
            if valor:
                return valor
    return None


class XmlReader:
    def ler_pasta(self, pasta: str) -> List[XmlNFe]:
        xmls: List[XmlNFe] = []

        for arquivo in os.listdir(pasta):
            if not arquivo.lower().endswith(".xml"):
                continue

            caminho = os.path.join(pasta, arquivo)

            try:
                tree = ET.parse(caminho)
                root = tree.getroot()

                processavel, _ = classificar_xml_processavel(root)
                if not processavel:
                    continue

                cnpj, nome = extrair_emitente_xml(root)
                if not cnpj or not nome:
                    continue

                xmls.append(
                    XmlNFe(
                        caminho=caminho,
                        xml=root,
                        emitente_cnpj=cnpj,
                        emitente_nome=nome,
                    )
                )

            except Exception:
                continue

        return xmls

    def _eh_nfe_modelo_55(self, root: ET.Element) -> bool:
        """
        Valida se o XML e uma NFe modelo 55.
        Compativel com nfeProc e NFe.
        """
        ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

        mod = root.find(".//nfe:infNFe/nfe:ide/nfe:mod", ns)
        if mod is None:
            return False

        return mod.text == "55"
