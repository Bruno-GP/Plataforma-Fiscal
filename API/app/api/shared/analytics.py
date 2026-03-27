from decimal import Decimal


def obter_periodo_anterior(periodo_ano: int, periodo_mes: int | None) -> tuple[int, int | None]:
    if periodo_mes is None:
        return periodo_ano - 1, None
    if periodo_mes > 1:
        return periodo_ano, periodo_mes - 1
    return periodo_ano - 1, 12


def agrupar_ranking_por_chave(itens: list[dict], chave: str, limite: int = 5) -> list[dict]:
    agrupado: dict[str, Decimal] = {}
    for item in itens:
        nome = str(item.get(chave) or "").strip() or f"{chave.title()} não identificado"
        valor_total = Decimal(str(item.get("valor_total") or 0))
        agrupado[nome] = agrupado.get(nome, Decimal("0.00")) + valor_total

    return [
        {chave: nome, "valor_total": valor_total}
        for nome, valor_total in sorted(
            agrupado.items(),
            key=lambda entry: entry[1],
            reverse=True,
        )[:limite]
    ]


def resumir_vendas_por_kpis(resultados: list, dashboard_type, limite: int = 5):
    total_vendido = Decimal("0.00")
    quantidade_notas = 0
    total_impostos = Decimal("0.00")
    top_clientes: list[dict] = []
    top_produtos: list[dict] = []
    top_cidades: list[dict] = []

    for item in resultados:
        kpis = item.kpis
        total_vendido += Decimal(str(kpis.total_vendas or 0))
        quantidade_notas += int(kpis.quantidade_notas or 0)
        total_impostos += (
            Decimal(str(kpis.total_icms or 0))
            + Decimal(str(kpis.total_ipi or 0))
            + Decimal(str(kpis.total_pis or 0))
            + Decimal(str(kpis.total_cofins or 0))
        )
        top_clientes.extend(kpis.top_clientes or [])
        top_produtos.extend(kpis.top_produtos or [])
        top_cidades.extend(kpis.top_cidades or [])

    ticket_medio = total_vendido / quantidade_notas if quantidade_notas else Decimal("0.00")

    return dashboard_type(
        total_vendido=total_vendido,
        quantidade_notas=quantidade_notas,
        total_impostos=total_impostos,
        ticket_medio=ticket_medio,
        top_clientes=agrupar_ranking_por_chave(top_clientes, "cliente", limite),
        top_produtos=agrupar_ranking_por_chave(top_produtos, "produto", limite),
        top_cidades=agrupar_ranking_por_chave(top_cidades, "cidade", limite),
    )
