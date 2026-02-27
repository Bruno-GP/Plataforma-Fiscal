from dataclasses import dataclass
from typing import List, Dict, Tuple
from collections import defaultdict

from app.models.nfe.schemas import NFeNota
from app.domain.nfe.extractor import NotaExtraida, ItemNota

"""Estrutura agregada usada pelo serviço para retorno e métricas de processamento."""
class ConsolidacaoNFe:
    def __init__(self, notas: List[NotaExtraida]):
        self.notas = notas
        self.notas_processadas = len(notas)
        self.itens_processados = sum(len(n.itens) for n in notas)
        
        # Resultado agregado por produto/NCM/CFOP para análises de mix e volume.
        self.itens_consolidados = self._consolidar_itens()

    def _consolidar_itens(self):
        """
        Consolida itens por:
        - código do produto
        - NCM
        - CFOP
        """
        consolidados = defaultdict(lambda: {
            "descricao": "",
            "ncm": "",
            "cfop": "",
            "quantidade": 0,
            "valor_total": 0
        })

        for nota in self.notas:
            for item in nota.itens:
                key = (
                    item.codigo_produto,
                    item.ncm,
                    item.cfop
                )

                consolidados[key]["descricao"] = item.descricao
                consolidados[key]["ncm"] = item.ncm
                consolidados[key]["cfop"] = item.cfop
                consolidados[key]["quantidade"] += float(item.quantidade)
                consolidados[key]["valor_total"] += float(item.valor_total)

        return [
            {
                "codigo_produto": k[0],
                "descricao": v["descricao"],
                "ncm": v["ncm"],
                "cfop": v["cfop"],
                "quantidade": round(v["quantidade"], 2),
                "valor_total": round(v["valor_total"], 2)
            }
            for k, v in consolidados.items()
        ]

class NFeConsolidator:
    """ Consolida e deduplica notas extraídas. Prepara dados para KPIs e persistência (Sheets/SQL). """
    """Remove duplicidades e devolve objeto pronto para persistência/relatórios."""

    def consolidar(self, notas: List[NotaExtraida]) -> ConsolidacaoNFe:
        mapa: Dict[Tuple, NFeNota] = {}
        duplicadas = 0

        for nota in notas:
            chave = self._chave_dedupe(nota)
            
            # Dedupe conservador: mantém a primeira ocorrência encontrada.
            if chave in mapa:
                duplicadas += 1
                continue

            mapa[chave] = nota

        notas_final = list(mapa.values())
        itens_total = sum(len(n.itens) for n in notas_final)

        return ConsolidacaoNFe(notas_final)

    def _chave_dedupe(self, nota: NFeNota) -> Tuple:
        """
        Chave de deduplicação (MVP).
        Quando adicionarmos chave_nfe, isso vira a chave oficial.
        """
        return (
            nota.numero_nf,
            str(nota.data_emissao) if nota.data_emissao else "",
            nota.destinatario_documento,
            str(nota.valor_total_nf)
        )
