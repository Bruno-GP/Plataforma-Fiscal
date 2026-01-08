from typing import List
from datetime import datetime, date
from decimal import Decimal

from app.domain.xml_models import XmlNFe

NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}


# =========================
# ITEM DA NOTA
# =========================
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
class NotaExtraida:
    def __init__(
        self,
        chave: str,
        numero_nf: int,
        emitente_cnpj: str,
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
class NFeExtractor:
    def extrair(self, xmls: List[XmlNFe]) -> List[NotaExtraida]:
        notas: List[NotaExtraida] = []

        for xml_nfe in xmls:
            root = xml_nfe.xml
            inf = root.find(".//nfe:infNFe", NS)
            if inf is None:
                continue

            # ===== Identificação =====
            chave = inf.attrib.get("Id", "").replace("NFe", "")
            ide = inf.find("nfe:ide", NS)
            if ide is None:
                continue

            numero_nf = int(ide.findtext("nfe:nNF", "0", NS))
            natureza_operacao = ide.findtext("nfe:natOp", "", NS)

            dh_emi = ide.findtext("nfe:dhEmi", "", NS)
            if not dh_emi:
                continue

            data_emissao = datetime.fromisoformat(
                dh_emi.replace("Z", "")
            ).date()

            # ===== Emitente =====
            emit = inf.find("nfe:emit", NS)
            if emit is None:
                continue

            emitente_cnpj = emit.findtext("nfe:CNPJ", "", NS)

            # ===== Destinatário =====
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

            # ===== Totais =====
            tot = inf.find("nfe:total/nfe:ICMSTot", NS)
            if tot is None:
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