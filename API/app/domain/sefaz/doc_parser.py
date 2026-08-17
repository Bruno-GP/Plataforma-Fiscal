from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from defusedxml import ElementTree as ET


NAMESPACE_NFE = "http://www.portalfiscal.inf.br/nfe"
NAMESPACE_MAP = {"nfe": NAMESPACE_NFE}


@dataclass(frozen=True)
class DocumentoParseado:
    chave_acesso: str
    tipo_documento: str
    cnpj_emitente: str
    cnpj_destinatario: str | None
    data_emissao: str | None
    valor_total: str | None
    situacao: str | None
    tipo_evento: str | None
    protocolo: str | None


class DocumentoParseInvalidoError(ValueError):
    pass


def _local_name(tag: str) -> str:
    return (tag or "").split("}")[-1]


def _normalizar_documento(valor: str | None) -> str | None:
    texto = "".join(ch for ch in (valor or "").strip().upper() if ch.isalnum())
    return texto or None


def _texto_primeiro(root: ET.Element, nomes: Iterable[str]) -> str | None:
    nomes_normalizados = {nome for nome in nomes}

    for elemento in root.iter():
        if _local_name(elemento.tag) not in nomes_normalizados:
            continue

        texto = (elemento.text or "").strip()
        if texto:
            return texto

    return None


def _texto_primeiro_por_caminhos(root: ET.Element, caminhos: Iterable[str]) -> str | None:
    for caminho in caminhos:
        candidato = root.find(caminho, NAMESPACE_MAP)
        if candidato is None:
            continue

        texto = (candidato.text or "").strip()
        if texto:
            return texto

    return None


def _texto_obrigatorio(root: ET.Element, nomes: Iterable[str], erro: str) -> str:
    valor = _texto_primeiro(root, nomes)
    if not valor:
        raise DocumentoParseInvalidoError(erro)
    return valor


def _parse_xml(xml_bytes: bytes) -> ET.Element:
    if not xml_bytes:
        raise DocumentoParseInvalidoError("XML SEFAZ vazio.")

    try:
        return ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise DocumentoParseInvalidoError("XML SEFAZ invalido.") from exc


def _extrair_chave_acesso(root: ET.Element) -> str:
    return _texto_obrigatorio(
        root,
        ["chNFe", "chaveAcesso", "chNf", "chNFCe"],
        "Chave de acesso nao encontrada no XML SEFAZ.",
    )


def _extrair_cnpj_emitente(root: ET.Element, tipo_documento: str) -> str:
    candidatos_por_tipo = {
        "resEvento": [
            ".//nfe:infEvento/nfe:CNPJDest",
            ".//nfe:infEvento/nfe:CPFDest",
            ".//nfe:CNPJDest",
            ".//nfe:CPFDest",
        ],
        "resNFe": [
            ".//nfe:CNPJ",
            ".//nfe:emit/nfe:CNPJ",
            ".//nfe:emit/nfe:CPF",
        ],
        "nfeProc": [
            ".//nfe:emit/nfe:CNPJ",
            ".//nfe:emit/nfe:CPF",
            ".//nfe:CNPJ",
            ".//nfe:CPF",
        ],
    }

    valor = _texto_primeiro_por_caminhos(root, candidatos_por_tipo.get(tipo_documento, []))
    if not valor:
        valor = _texto_primeiro(root, ["CNPJ", "CPF", "Cnpj", "Cpf", "CNPJDest", "CPFDest"])

    if not valor:
        raise DocumentoParseInvalidoError("CNPJ do emitente nao encontrado no XML SEFAZ.")

    normalizado = _normalizar_documento(valor)
    if not normalizado:
        raise DocumentoParseInvalidoError("CNPJ do emitente invalido no XML SEFAZ.")

    return normalizado


def _extrair_cnpj_destinatario(root: ET.Element) -> str | None:
    valor = _texto_primeiro_por_caminhos(
        root,
        [
            ".//nfe:CNPJDest",
            ".//nfe:CPFDest",
            ".//nfe:dest/nfe:CNPJ",
            ".//nfe:dest/nfe:CPF",
            ".//nfe:infEvento/nfe:CNPJDest",
            ".//nfe:infEvento/nfe:CPFDest",
        ],
    )
    if not valor:
        valor = _texto_primeiro(root, ["CNPJDest", "CPFDest"])
    if not valor:
        return None

    return _normalizar_documento(valor)


def _extrair_tipo_documento(root: ET.Element, tipo_documento: str) -> str:
    local = _local_name(root.tag)
    if local != tipo_documento:
        return tipo_documento
    return local


def _extrair_data_emissao(root: ET.Element, tipo_documento: str) -> str | None:
    candidatos = {
        "resNFe": ["dhEmi", "dEmi"],
        "resEvento": ["dhRegEvento", "dhEvento"],
        "nfeProc": ["dhEmi", "dEmi", "dhRecbto"],
    }.get(tipo_documento, ["dhEmi", "dEmi", "dhEvento"])
    return _texto_primeiro(root, candidatos)


def _extrair_valor_total(root: ET.Element, tipo_documento: str) -> str | None:
    candidatos = {
        "resNFe": ["vNF"],
        "resEvento": ["vNF", "vEvento", "vICMS"],
        "nfeProc": ["vNF"],
    }.get(tipo_documento, ["vNF"])
    return _texto_primeiro(root, candidatos)


def _extrair_situacao(root: ET.Element, tipo_documento: str) -> str | None:
    candidatos = {
        "resNFe": ["cSitNFe", "cStat"],
        "resEvento": ["cStat", "xMotivo"],
        "nfeProc": ["cStat", "xMotivo"],
    }.get(tipo_documento, ["cStat", "xMotivo"])
    return _texto_primeiro(root, candidatos)


def _extrair_tipo_evento(root: ET.Element, tipo_documento: str) -> str | None:
    if tipo_documento != "resEvento":
        return None

    return _texto_primeiro(root, ["tpEvento", "xEvento"])


def _extrair_protocolo(root: ET.Element, tipo_documento: str) -> str | None:
    candidatos = {
        "resEvento": ["nProt"],
        "nfeProc": ["nProt"],
    }.get(tipo_documento, ["nProt"])
    return _texto_primeiro(root, candidatos)


def parse_documento(tipo_documento: str, xml_bytes: bytes) -> DocumentoParseado:
    if tipo_documento not in {"resNFe", "resEvento", "nfeProc"}:
        raise DocumentoParseInvalidoError(f"Tipo de documento SEFAZ nao suportado: {tipo_documento!r}.")

    root = _parse_xml(xml_bytes)
    chave_acesso = _extrair_chave_acesso(root)
    cnpj_emitente = _extrair_cnpj_emitente(root, tipo_documento)
    cnpj_destinatario = _extrair_cnpj_destinatario(root)

    return DocumentoParseado(
        chave_acesso=chave_acesso,
        tipo_documento=_extrair_tipo_documento(root, tipo_documento),
        cnpj_emitente=cnpj_emitente,
        cnpj_destinatario=cnpj_destinatario,
        data_emissao=_extrair_data_emissao(root, tipo_documento),
        valor_total=_extrair_valor_total(root, tipo_documento),
        situacao=_extrair_situacao(root, tipo_documento),
        tipo_evento=_extrair_tipo_evento(root, tipo_documento),
        protocolo=_extrair_protocolo(root, tipo_documento),
    )


def calcular_direcao(cnpj_emitente: str, cnpj_empresa: str) -> str:
    emitente = _normalizar_documento(cnpj_emitente) or ""
    empresa = _normalizar_documento(cnpj_empresa) or ""
    return "emitida" if emitente == empresa else "recebida"
