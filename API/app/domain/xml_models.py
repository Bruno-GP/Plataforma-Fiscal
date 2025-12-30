from dataclasses import dataclass
from xml.etree.ElementTree import Element

@dataclass
class XmlNFe:
  caminho: str
  xml: Element
  emitente_cnpj: str
