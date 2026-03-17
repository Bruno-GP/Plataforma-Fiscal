from typing import List
from datetime import datetime, date
from decimal import Decimal

import re
import logging

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


def _extrair_nfse(xml_nfe: XmlNFe) -> NotaExtraida | None:
    root = xml_nfe.xml
    numero_nf = int(_encontrar_texto_xml(root, "Numero") or "0")
    data_emissao_str = _encontrar_texto_xml(root, "DataEmissao")
    if not data_emissao_str:
        return None

    data_emissao = datetime.fromisoformat(data_emissao_str).date()

    valor_total_nf = Decimal(_encontrar_texto_xml(root, "ValorServicos") or "0")
    valor_iss = Decimal(_encontrar_texto_xml(root, "ValorIss") or "0")
    valor_desconto = Decimal(_encontrar_texto_xml(root, "DescontoIncondicionado") or "0")

    destinatario_nome = _encontrar_texto_xml(root, "RazaoSocial")
    destinatario_cidade = _encontrar_texto_xml(root, "CodigoMunicipio")
    destinatario_uf = _encontrar_texto_xml(root, "Uf")

    tomador_doc = ""
    for element in root.iter():
        tag = element.tag.split("}")[-1]
        if tag in {"Cnpj", "CPF", "CNPJ"} and element.text:
            tomador_doc = element.text.strip()

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
        valor_icms=Decimal("0"),
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
                descricao=_encontrar_texto_xml(root, "Discriminacao") or "Serviço NFSe",
                ncm="",
                cfop="",
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
                destinatario_cidade = ender.findtext("nfe:xMun", "", NS) if ender is not None else ""
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