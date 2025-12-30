import os
import xml.etree.ElementTree as ET
from typing import List
from app.domain.xml_models import XmlNFe

NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

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

                emit = root.find(".//nfe:emit", NS)
                if emit is None:
                    print(f"[XML IGNORADO] Sem <emit>: {arquivo}")
                    continue

                cnpj = emit.findtext("nfe:CNPJ", default="", namespaces=NS)
                if not cnpj:
                    print(f"[XML IGNORADO] Sem CNPJ: {arquivo}")
                    continue

                xmls.append(
                    XmlNFe(
                        caminho=caminho,
                        xml=root,
                        emitente_cnpj=cnpj
                    )
                )

            except Exception as e:
                print(f"[ERRO XML] {arquivo}: {e}")

        print(f"[INFO] XMLs válidos encontrados: {len(xmls)}")
        return xmls

    def _eh_nfe_modelo_55(self, root: ET.Element) -> bool:
      """
      Valida se o XML é uma NFe modelo 55.
      Compatível com nfeProc e NFe.
      """
      ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

      # Caso comum: nfeProc -> NFe -> infNFe -> ide -> mod
      mod = root.find(".//nfe:infNFe/nfe:ide/nfe:mod", ns)

      if mod is None:
          return False

      return mod.text == "55"