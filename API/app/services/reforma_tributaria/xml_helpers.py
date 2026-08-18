from __future__ import annotations

from defusedxml import ElementTree as ET


def parse_xml_importado(conteudo_xml):
  try:
    if isinstance(conteudo_xml, memoryview):
      conteudo_xml = conteudo_xml.tobytes()
    return ET.fromstring(conteudo_xml)
  except ET.ParseError:
    return None


def nome_local(elemento) -> str:
  return elemento.tag.split("}")[-1] if elemento is not None else ""


def encontrar_elemento_local(root, nome_tag: str):
  if root is None:
    return None
  return next((elemento for elemento in root.iter() if nome_local(elemento) == nome_tag), None)


def encontrar_filho_local(root, nome_tag: str):
  if root is None:
    return None
  return next((elemento for elemento in list(root) if nome_local(elemento) == nome_tag), None)


def encontrar_filhos_local(root, nome_tag: str) -> list:
  if root is None:
    return []
  return [elemento for elemento in list(root) if nome_local(elemento) == nome_tag]


def texto_filho_local(root, nome_tag: str) -> str:
  elemento = encontrar_filho_local(root, nome_tag)
  if elemento is None or elemento.text is None:
    return ""
  return elemento.text.strip()


def normalizar_numero_nf(numero_nf: str) -> str:
  valor = (numero_nf or "").strip()
  if not valor:
    return ""
  if valor.isdigit():
    return str(int(valor))
  return valor.lstrip("0") or valor
