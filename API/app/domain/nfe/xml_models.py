from dataclasses import dataclass
from defusedxml.ElementTree import Element

@dataclass
class XmlNFe:
  caminho: str
  xml: Element
  emitente_cnpj: str
  emitente_nome: str
