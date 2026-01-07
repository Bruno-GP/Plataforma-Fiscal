from decimal import Decimal
from typing import List, Dict
from collections import defaultdict

from app.domain.extractor import NotaExtraida
from app.models.schemas import KPIsRelatorio


class KPICalculator:
    def calcular(self, notas: List[NotaExtraida]) -> KPIsRelatorio:
        if not notas:
            return KPIsRelatorio()

        quantidade_notas = len(notas)
        total_vendas = sum(n.valor_total_nf for n in notas)

        valores = [n.valor_total_nf for n in notas]

        ticket_medio = (
            total_vendas / quantidade_notas
            if quantidade_notas > 0 else Decimal("0.00")
        )

        maior_nota = max(valores)
        menor_nota = min(valores)

        # 🔹 IMPOSTOS
        total_icms = sum(n.valor_icms for n in notas)
        total_ipi = sum(n.valor_ipi for n in notas)
        total_pis = sum(n.valor_pis for n in notas)
        total_cofins = sum(n.valor_cofins for n in notas)

        # 🔹 TOP CLIENTES
        clientes = defaultdict(Decimal)
        for nota in notas:
            nome_bruto = nota.destinatario_nome.strip()

            if "/" in nome_bruto:
                cliente = nome_bruto.split("/", 1)[1].strip()
            else:
                cliente = nome_bruto or "CLIENTE NÃO IDENTIFICADO"

            clientes[cliente] += nota.valor_total_nf
            
        def calcular_percentual(valor: Decimal) -> Decimal:
            if total_vendas == 0:
                return Decimal("0.00")
            return (valor / total_vendas) * Decimal("100")

        top_clientes = [
            {
                "cliente": k,
                "valor_total": v,
                "percentual": calcular_percentual(v),
            }
            for k, v in sorted(
                clientes.items(),
                key=lambda item: item[1],
                reverse=True
            )[:5]
        ]

        # 🔹 TOP PRODUTOS (via itens)
        produtos = defaultdict(Decimal)
        for n in notas:
            for item in n.itens:
                produtos[item.descricao] += item.valor_total

        top_produtos = [
            {
                "produto": k,
                "valor_total": v,
                "percentual": calcular_percentual(v),
            }
            for k, v in sorted(
                produtos.items(),
                key=lambda item: item[1],
                reverse=True
            )[:5]
        ]

        # 🔹 TOP CIDADES
        cidades = defaultdict(Decimal)
        for n in notas:
            cidades[n.destinatario_cidade] += n.valor_total_nf

        top_cidades = [
            {
                "cidade": k,
                "valor_total": v,
                "percentual": calcular_percentual(v),
            }
            for k, v in sorted(
                cidades.items(),
                key=lambda item: item[1],
                reverse=True
            )[:5]
        ]

        return KPIsRelatorio(
            total_vendas=total_vendas,
            quantidade_notas=quantidade_notas,
            ticket_medio=ticket_medio,
            maior_nota=maior_nota,
            menor_nota=menor_nota,

            total_icms=total_icms,
            total_ipi=total_ipi,
            total_pis=total_pis,
            total_cofins=total_cofins,

            top_clientes=top_clientes,
            top_produtos=top_produtos,
            top_cidades=top_cidades
        )