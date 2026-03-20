from typing import List
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from functools import lru_cache
import json

import re
import logging
import unicodedata

from app.domain.nfe.xml_models import XmlNFe

NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

logger = logging.getLogger("NFeExtractor")

"""Normaliza os formatos de data de emissão existentes em NF-e/NFC-e."""
def _parse_data_emissao(dh_emi: str, d_emi: str) -> date:
    if dh_emi:
        valor = dh_emi.strip()
        if valor.endswith("Z"):
            valor = valor[:-1] + "+00:00"
        if re.search(r"[+-]\d{4}$", valor):
            valor = f"{valor[:-2]}:{valor[-2:]}"
        return datetime.fromisoformat(valor).date()

    valor = d_emi.strip()
    try:
        return date.fromisoformat(valor)
    except ValueError:
        if len(valor) == 8 and valor.isdigit():
            return datetime.strptime(valor, "%Y%m%d").date()
        raise

# =========================
# ITEM DA NOTA
# =========================

"""Representa um item de produto/serviço extraído de uma nota fiscal."""
class ItemNota:
    def __init__(
        self,
        numero_item: int,
        codigo_produto: str,
        descricao: str,
        ncm: str,
        cfop: str,
        unidade: str,
        quantidade: Decimal,
        valor_unitario: Decimal,
        valor_total: Decimal
    ):
        self.numero_item = numero_item
        self.codigo_produto = codigo_produto
        self.descricao = descricao
        self.ncm = ncm
        self.cfop = cfop
        self.unidade = unidade
        self.quantidade = quantidade
        self.valor_unitario = valor_unitario
        self.valor_total = valor_total


# =========================
# NOTA EXTRAÍDA (CONTRATO ÚNICO)
# =========================

"""Contrato interno padronizado para consumo dos serviços de NFe."""
class NotaExtraida:
    def __init__(
        self,
        chave: str,
        numero_nf: int,
        emitente_cnpj: str,
        modelo: str,
        data_emissao: date,
        natureza_operacao: str,

        destinatario_documento: str,
        destinatario_nome: str,
        destinatario_cidade: str,
        destinatario_uf: str,

        valor_total_nf: Decimal,
        valor_icms: Decimal,
        valor_ipi: Decimal,
        valor_pis: Decimal,
        valor_cofins: Decimal,
        valor_produtos: Decimal,
        valor_desconto: Decimal,
        valor_frete: Decimal,

        itens: List[ItemNota]
    ):
        self.chave = chave
        self.numero_nf = numero_nf
        self.emitente_cnpj = emitente_cnpj
        self.modelo = modelo
        self.data_emissao = data_emissao
        self.natureza_operacao = natureza_operacao

        self.destinatario_documento = destinatario_documento
        self.destinatario_nome = destinatario_nome
        self.destinatario_cidade = destinatario_cidade
        self.destinatario_uf = destinatario_uf

        self.valor_total_nf = valor_total_nf
        self.valor_icms = valor_icms
        self.valor_ipi = valor_ipi
        self.valor_pis = valor_pis
        self.valor_cofins = valor_cofins
        self.valor_produtos = valor_produtos
        self.valor_desconto = valor_desconto
        self.valor_frete = valor_frete

        self.itens = itens


# =========================
# EXTRACTOR
# =========================

"""Converte XMLs já carregados em objetos de domínio usados no processamento."""

def _encontrar_texto_xml(root, nome_tag: str) -> str:
    elemento = next(
        (element for element in root.iter() if element.tag.split("}")[-1] == nome_tag),
        None,
    )
    if elemento is None or elemento.text is None:
        return ""
    return elemento.text.strip()

def _encontrar_elemento(root, nome_tag: str):
    return next(
        (element for element in root.iter() if element.tag.split("}")[-1] == nome_tag),
        None,
    )

def _extrair_descricao_servico(discriminacao: str) -> str:
    if not discriminacao:
        return "Serviço NFSe"

    match = re.search(r"Descricao\s*=\s*([^\]]+)", discriminacao, flags=re.IGNORECASE)
    if match:
        descricao = " ".join(match.group(1).strip().split())
        descricao = re.sub(r"^\d+\s+", "", descricao)

        partes = re.split(
            r"\s+-\s+|\s+(?=Relat[oó]rio\b)|\s+(?=Relatorio\b)|\s+(?=Pedido\b)|\s+(?=Banco\b)|\s+(?=Agencia\b)|\s+(?=Operacao\b)|\s+(?=Conta\b)|\s+(?=Qtde\b)|\s+(?=Valor\b)",
            descricao,
            maxsplit=1,
            flags=re.IGNORECASE,
        )
        descricao = partes[0].strip(" -")
        
        descricao_normalizada = _normalizar_chave_municipio(descricao)
        if descricao_normalizada.startswith("MAO DE OBRA"):
            return "Mão de Obra"

        return descricao or "Serviço NFSe"

    descricao = discriminacao.strip()
    descricao_normalizada = _normalizar_chave_municipio(descricao)
    if descricao_normalizada.startswith("MAO DE OBRA"):
        return "Mão de Obra"

    return descricao or "Serviço NFSe"

def _normalizar_chave_municipio(valor: str) -> str:
    texto = " ".join((valor or "").strip().upper().split())
    if not texto:
        return ""
    sem_acentos = unicodedata.normalize("NFD", texto)
    return "".join(ch for ch in sem_acentos if unicodedata.category(ch) != "Mn")

@lru_cache(maxsize=1)
def _carregar_municipios() -> tuple[dict[str, str], dict[str, str]]:
    caminho_municipios = Path(__file__).resolve().parent.parent.parent / "services" / "Municipios" / "LL-municipios.json"
    try:
        with caminho_municipios.open(encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (OSError, json.JSONDecodeError):
        return {}, {}

    municipios_por_codigo: dict[str, str] = {}
    municipios_por_nome: dict[str, str] = {}

    features = dados.get("features", []) if isinstance(dados, dict) else []
    for item in features if isinstance(features, list) else []:
        propriedades = item.get("properties", {}) if isinstance(item, dict) else {}
        codigo = "".join(ch for ch in str(propriedades.get("id", "")) if ch.isdigit())
        nome = str(propriedades.get("name", "")).strip()
        nome_normalizado = _normalizar_chave_municipio(nome)
        if codigo and nome:
            municipios_por_codigo[codigo] = nome
            municipios_por_nome[nome_normalizado] = nome

    return municipios_por_codigo, municipios_por_nome


def _resolver_nome_municipio(codigo_ou_nome: str) -> str:
    valor = (codigo_ou_nome or "").strip()
    if not valor:
        return ""
    
    municipios_por_codigo, municipios_por_nome = _carregar_municipios()

    codigo = "".join(ch for ch in valor if ch.isdigit())
    if len(codigo) >= 6:
        return municipios_por_codigo.get(codigo, valor)

    nome_normalizado = _normalizar_chave_municipio(valor)
    return municipios_por_nome.get(nome_normalizado, valor)


def _encontrar_textos_por_tag(root, nome_tag: str) -> list[str]:
    if root is None:
        return []

    textos: list[str] = []
    for element in root.iter():
        if element.tag.split("}")[-1] != nome_tag:
            continue
        if element.text and element.text.strip():
            textos.append(element.text.strip())
    return textos


def _extrair_nome_tomador(tomador) -> str:
    if tomador is None:
        return ""

    for valor in _encontrar_textos_por_tag(tomador, "RazaoSocial"):
        if valor:
            return valor
    return ""


def _extrair_nfse(xml_nfe: XmlNFe) -> NotaExtraida | None:
    root = xml_nfe.xml
    numero_nf = int(_encontrar_texto_xml(root, "Numero") or "0")
    data_emissao_str = _encontrar_texto_xml(root, "DataEmissao")
    if not data_emissao_str:
        return None

    data_emissao = datetime.fromisoformat(data_emissao_str).date()

    valor_total_servicos = Decimal(_encontrar_texto_xml(root, "ValorServicos") or "0")
    valor_total_nf = Decimal(_encontrar_texto_xml(root, "ValorLiquidoNfse") or "0")
    valor_iss_retido = Decimal(_encontrar_texto_xml(root, "ValorIssRetido") or "0")
    outras_retencoes = Decimal(_encontrar_texto_xml(root, "OutrasRetencoes") or "0")
    valor_impostos_servico = valor_iss_retido + outras_retencoes
    valor_desconto = Decimal(_encontrar_texto_xml(root, "DescontoIncondicionado") or "0")

    tomador = _encontrar_elemento(root, "TomadorServico")

    destinatario_nome = _extrair_nome_tomador(tomador)
    destinatario_cidade_codigo = _encontrar_texto_xml(tomador, "CodigoMunicipio") if tomador is not None else ""
    destinatario_cidade = _resolver_nome_municipio(destinatario_cidade_codigo)
    destinatario_uf = (
        _encontrar_texto_xml(tomador, "Uf")
        or _encontrar_texto_xml(tomador, "UF")
        if tomador is not None
        else ""
    )

    tomador_doc = ""
    if tomador is not None:
        tomador_doc = (
            _encontrar_texto_xml(tomador, "Cnpj")
            or _encontrar_texto_xml(tomador, "CNPJ")
            or _encontrar_texto_xml(tomador, "Cpf")
            or _encontrar_texto_xml(tomador, "CPF")
        )

    descricao_servico = _extrair_descricao_servico(_encontrar_texto_xml(root, "Discriminacao"))

    return NotaExtraida(
        chave=str(numero_nf),
        numero_nf=numero_nf,
        emitente_cnpj=xml_nfe.emitente_cnpj,
        modelo="NFSE",
        data_emissao=data_emissao,
        natureza_operacao="SERVICO",
        destinatario_documento=tomador_doc,
        destinatario_nome=destinatario_nome,
        destinatario_cidade=destinatario_cidade,
        destinatario_uf=destinatario_uf,
        valor_total_nf=valor_total_nf,
        valor_icms=valor_impostos_servico,
        valor_ipi=Decimal("0"),
        valor_pis=Decimal("0"),
        valor_cofins=Decimal("0"),
        valor_produtos=valor_total_nf,
        valor_desconto=valor_desconto,
        valor_frete=Decimal("0"),
        itens=[
            ItemNota(
                numero_item=1,
                codigo_produto=_encontrar_texto_xml(root, "ItemListaServico"),
                descricao=descricao_servico,
                ncm="00000000",
                cfop="5933",
                unidade="UN",
                quantidade=Decimal("1"),
                valor_unitario=valor_total_nf,
                valor_total=valor_total_nf,
            )
        ],
    )

class NFeExtractor:
    def extrair(self, xmls: List[XmlNFe]) -> List[NotaExtraida]:
        notas: List[NotaExtraida] = []

        for xml_nfe in xmls:
            root = xml_nfe.xml
            inf = root.find(".//nfe:infNFe", NS)
            if inf is None:
                nota_nfse = _extrair_nfse(xml_nfe)
                if nota_nfse is not None:
                    notas.append(nota_nfse)
                continue

            # ===== Identificação =====
            
            # Bloco `ide` concentra número, modelo e datas oficiais do documento.
            chave = inf.attrib.get("Id", "").replace("NFe", "")
            ide = inf.find("nfe:ide", NS)
            if ide is None:
                continue

            numero_nf = int(ide.findtext("nfe:nNF", "0", NS))
            natureza_operacao = ide.findtext("nfe:natOp", "", NS)
            modelo = ide.findtext("nfe:mod", "", NS)

            dh_emi = ide.findtext("nfe:dhEmi", "", NS)
            d_emi = ide.findtext("nfe:dEmi", "", NS)
            if not dh_emi and not d_emi:
                # Documento sem data de emissão é considerado inválido no pipeline.
                continue

            data_emissao = _parse_data_emissao(dh_emi, d_emi)

            # ===== Emitente =====
            emit = inf.find("nfe:emit", NS)
            if emit is None:
                continue

            emitente_cnpj = emit.findtext("nfe:CNPJ", "", NS)

            # ===== Destinatário =====
            
            # Para NFC-e (modelo 65), destinatário pode vir vazio no XML.
            dest = inf.find("nfe:dest", NS)

            if dest is not None:
                destinatario_nome = dest.findtext("nfe:xNome", "", NS)
                destinatario_doc = (
                    dest.findtext("nfe:CNPJ", "", NS) or
                    dest.findtext("nfe:CPF", "", NS)
                )

                ender = dest.find("nfe:enderDest", NS)
                destinatario_cidade = (
                    _resolver_nome_municipio(ender.findtext("nfe:xMun", "", NS))
                    if ender is not None
                    else ""
                )
                destinatario_uf = ender.findtext("nfe:UF", "", NS) if ender is not None else ""
            else:
                destinatario_nome = ""
                destinatario_doc = ""
                destinatario_cidade = ""
                destinatario_uf = ""
                print("[AVISO] XML sem destinatário identificado")
                
            if modelo == "65" and not destinatario_nome:
                destinatario_nome = "Consumidor Final"

            # ===== Totais =====
            tot = inf.find("nfe:total/nfe:ICMSTot", NS)
            if tot is None:
                # Totais ausentes impedem KPI e consolidação financeira.
                continue

            def d(tag):
                return Decimal(tot.findtext(tag, "0", NS))

            # ===== Itens =====
            itens: List[ItemNota] = []

            for det in inf.findall("nfe:det", NS):
                prod = det.find("nfe:prod", NS)
                if prod is None:
                    continue

                itens.append(
                    ItemNota(
                        numero_item=int(det.attrib.get("nItem", "0")),
                        codigo_produto=prod.findtext("nfe:cProd", "", NS),
                        descricao=prod.findtext("nfe:xProd", "", NS),
                        ncm=prod.findtext("nfe:NCM", "", NS),
                        cfop=prod.findtext("nfe:CFOP", "", NS),
                        unidade=prod.findtext("nfe:uCom", "", NS),
                        quantidade=Decimal(prod.findtext("nfe:qCom", "0", NS)),
                        valor_unitario=Decimal(prod.findtext("nfe:vUnCom", "0", NS)),
                        valor_total=Decimal(prod.findtext("nfe:vProd", "0", NS))
                    )
                )

            notas.append(
                NotaExtraida(
                    chave=chave,
                    numero_nf=numero_nf,
                    emitente_cnpj=emitente_cnpj,
                    modelo=modelo,
                    data_emissao=data_emissao,
                    natureza_operacao=natureza_operacao,

                    destinatario_documento=destinatario_doc,
                    destinatario_nome=destinatario_nome,
                    destinatario_cidade=destinatario_cidade,
                    destinatario_uf=destinatario_uf,

                    valor_total_nf=d("nfe:vNF"),
                    valor_icms=d("nfe:vICMS"),
                    valor_ipi=d("nfe:vIPI"),
                    valor_pis=d("nfe:vPIS"),
                    valor_cofins=d("nfe:vCOFINS"),
                    valor_produtos=d("nfe:vProd"),
                    valor_desconto=d("nfe:vDesc"),
                    valor_frete=d("nfe:vFrete"),

                    itens=itens
                )
            )

        return notas