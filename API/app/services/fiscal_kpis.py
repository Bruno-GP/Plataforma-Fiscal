from decimal import Decimal
from typing import Optional

from app.api.shared.analytics import obter_periodo_anterior, resumir_vendas_por_kpis
from app.models.nfe.schemas import (
  DashboardVendasResponse,
  DashboardVendasResumo,
  KPIComparativoQuantidade,
  KPIComparativoValor,
  KPIsComparativo,
  NFeKPI,
  NFeKPIConsulta,
  SerieMensalVendasItem,
)


def normalizar_top_cidades(top_cidades: list[dict] | None) -> list[dict]:
  if not top_cidades:
    return []

  cidades_normalizadas: list[dict] = []
  for item in top_cidades:
    if not isinstance(item, dict):
      continue

    cidade = (item.get("cidade") or item.get("municipio") or "").strip()
    if not cidade:
      cidade = "Cidade não identificada"

    cidades_normalizadas.append({
      **item,
      "cidade": cidade,
    })

  return cidades_normalizadas


def calcular_variacao_percentual(
  atual: Decimal,
  anterior: Decimal,
) -> Optional[Decimal]:
  if anterior == 0:
    if atual == 0:
      return Decimal("0.00")
    return None
  return ((atual - anterior) / anterior * Decimal("100")).quantize(Decimal("0.01"))


def resolver_periodo_anterior_kpi(
  periodo_ano: int,
  periodo_mes: int,
  periodo_anterior_ano: Optional[int] = None,
  periodo_anterior_mes: Optional[int] = None,
) -> tuple[int, int]:
  if periodo_anterior_ano is not None and periodo_anterior_mes is not None:
    return periodo_anterior_ano, periodo_anterior_mes

  if periodo_mes == 1:
    return periodo_ano - 1, 12

  return periodo_ano, periodo_mes - 1


def criar_kpi_anterior_vazio(kpi_atual: NFeKPI) -> NFeKPI:
  return NFeKPI(
    emitente_cnpj=kpi_atual.emitente_cnpj,
    id=0,
    processamento_id=0,
    total_vendas=0,
    quantidade_notas=0,
    ticket_medio=0,
    maior_nota=0,
    menor_nota=0,
    total_icms=0,
    total_ipi=0,
    total_pis=0,
    total_cofins=0,
    top_clientes=[],
    top_produtos=[],
    top_cidades=[],
  )


def construir_comparativo_valor(atual, anterior) -> KPIComparativoValor:
  atual_decimal = Decimal(atual)
  anterior_decimal = Decimal(anterior)
  return KPIComparativoValor(
    atual=atual_decimal,
    anterior=anterior_decimal,
    variacao_percentual=calcular_variacao_percentual(
      atual_decimal,
      anterior_decimal,
    ),
  )


def construir_comparativo_quantidade(
  atual: int,
  anterior: int,
) -> KPIComparativoQuantidade:
  return KPIComparativoQuantidade(
    atual=atual,
    anterior=anterior,
    variacao_percentual=calcular_variacao_percentual(
      Decimal(atual),
      Decimal(anterior),
    ),
  )


def construir_comparativo_kpis(
  kpi_atual: NFeKPI,
  kpi_anterior: Optional[NFeKPI],
) -> KPIsComparativo:
  anterior = kpi_anterior or criar_kpi_anterior_vazio(kpi_atual)

  return KPIsComparativo(
    total_vendas=construir_comparativo_valor(
      kpi_atual.total_vendas,
      anterior.total_vendas,
    ),
    quantidade_notas=construir_comparativo_quantidade(
      kpi_atual.quantidade_notas,
      anterior.quantidade_notas,
    ),
    ticket_medio=construir_comparativo_valor(
      kpi_atual.ticket_medio,
      anterior.ticket_medio,
    ),
    maior_nota=construir_comparativo_valor(
      kpi_atual.maior_nota,
      anterior.maior_nota,
    ),
    menor_nota=construir_comparativo_valor(
      kpi_atual.menor_nota,
      anterior.menor_nota,
    ),
    total_icms=construir_comparativo_valor(
      kpi_atual.total_icms,
      anterior.total_icms,
    ),
    total_ipi=construir_comparativo_valor(
      kpi_atual.total_ipi,
      anterior.total_ipi,
    ),
    total_pis=construir_comparativo_valor(
      kpi_atual.total_pis,
      anterior.total_pis,
    ),
    total_cofins=construir_comparativo_valor(
      kpi_atual.total_cofins,
      anterior.total_cofins,
    ),
  )


def construir_nfe_kpi_de_row(row) -> NFeKPI:
  return NFeKPI(
    emitente_cnpj=row[0],
    id=row[1],
    processamento_id=row[2],
    total_vendas=row[3] or 0,
    quantidade_notas=row[4] or 0,
    ticket_medio=row[5] or 0,
    maior_nota=row[6] or 0,
    menor_nota=row[7] or 0,
    total_icms=row[8] or 0,
    total_ipi=row[9] or 0,
    total_pis=row[10] or 0,
    total_cofins=row[11] or 0,
    top_clientes=row[12] or [],
    top_produtos=row[13] or [],
    top_cidades=normalizar_top_cidades(row[14]),
  )


def construir_nfe_kpi_consulta_de_row(row) -> NFeKPIConsulta:
  return NFeKPIConsulta(
    periodo_ano=row[0],
    periodo_mes=row[1],
    emitente_cnpj=row[2],
    kpis=NFeKPI(
      emitente_cnpj=row[2],
      id=row[3],
      processamento_id=row[4],
      total_vendas=row[5] or 0,
      quantidade_notas=row[6] or 0,
      ticket_medio=row[7] or 0,
      maior_nota=row[8] or 0,
      menor_nota=row[9] or 0,
      total_icms=row[10] or 0,
      total_ipi=row[11] or 0,
      total_pis=row[12] or 0,
      total_cofins=row[13] or 0,
      top_clientes=row[14] or [],
      top_produtos=row[15] or [],
      top_cidades=normalizar_top_cidades(row[16]),
    ),
  )


def construir_sped_kpi_consulta(
  row,
  top_clientes: list[dict],
  top_produtos: list[dict],
  top_cidades: list[dict],
) -> NFeKPIConsulta:
  (
    kpi_id,
    processamento_id,
    cnpj_emitente,
    ano,
    mes,
    total_vendas,
    total_docs,
    ticket_medio,
    maior_nota,
    menor_nota,
    total_icms,
    total_ipi,
    total_pis,
    total_cofins,
  ) = row

  return NFeKPIConsulta(
    periodo_ano=ano,
    periodo_mes=mes,
    emitente_cnpj=cnpj_emitente,
    kpis=NFeKPI(
      id=kpi_id,
      processamento_id=processamento_id,
      emitente_cnpj=cnpj_emitente,
      total_vendas=total_vendas or Decimal("0.00"),
      quantidade_notas=total_docs or 0,
      ticket_medio=ticket_medio or Decimal("0.00"),
      maior_nota=maior_nota or Decimal("0.00"),
      menor_nota=menor_nota or Decimal("0.00"),
      total_icms=total_icms or Decimal("0.00"),
      total_ipi=total_ipi or Decimal("0.00"),
      total_pis=total_pis or Decimal("0.00"),
      total_cofins=total_cofins or Decimal("0.00"),
      top_clientes=top_clientes,
      top_produtos=top_produtos,
      top_cidades=top_cidades,
    ),
  )


def obter_anos_disponiveis_kpis(resultados: list[NFeKPIConsulta]) -> list[int]:
  return sorted(
    {item.periodo_ano for item in resultados if item.periodo_ano},
    reverse=True,
  )


def resolver_ano_referencia_dashboard(
  periodo_ano: Optional[int],
  anos_disponiveis: list[int],
) -> Optional[int]:
  return periodo_ano or (anos_disponiveis[0] if anos_disponiveis else None)


def selecionar_resultados_dashboard(
  resultados_ano_atual: list[NFeKPIConsulta],
  resultados_ano_anterior: list[NFeKPIConsulta],
  ano_referencia: int,
  periodo_mes: Optional[int],
) -> tuple[list[NFeKPIConsulta], list[NFeKPIConsulta], int, Optional[int]]:
  ano_anterior, mes_anterior = obter_periodo_anterior(ano_referencia, periodo_mes)

  if periodo_mes is None:
    return resultados_ano_atual, resultados_ano_anterior, ano_anterior, mes_anterior

  resultados_filtrados = [
    item for item in resultados_ano_atual if item.periodo_mes == periodo_mes
  ]
  resultados_anteriores = (
    [item for item in resultados_ano_atual if item.periodo_mes == mes_anterior]
    if ano_anterior == ano_referencia
    else [item for item in resultados_ano_anterior if item.periodo_mes == mes_anterior]
  )
  return resultados_filtrados, resultados_anteriores, ano_anterior, mes_anterior


def construir_periodos_dashboard(
  ano_referencia: int,
  periodo_mes: Optional[int],
  ano_anterior: int,
  mes_anterior: Optional[int],
  resultados_ano_atual: list[NFeKPIConsulta],
) -> set[tuple[int, Optional[int]]]:
  return {
    (ano_referencia, periodo_mes),
    (ano_anterior, mes_anterior),
    *{
      (ano_referencia, item.periodo_mes)
      for item in resultados_ano_atual
      if item.periodo_mes
    },
  }


def construir_resumo_dashboard(
  resultados: list[NFeKPIConsulta],
  periodo: tuple[int, Optional[int]],
  totais_vendidos: dict[tuple[int, Optional[int]], Decimal],
  totais_tributos: dict[tuple[int, Optional[int]], dict[str, Decimal]],
  limite: int,
) -> DashboardVendasResumo:
  return resumir_vendas_por_kpis(
    resultados,
    DashboardVendasResumo,
    limite,
  ).model_copy(update={
    "total_vendido": totais_vendidos.get(periodo, Decimal("0.00")),
    **totais_tributos.get(
      periodo,
      {
        "total_impostos_complementares": Decimal("0.00"),
        "total_tributos_reforma": Decimal("0.00"),
      },
    ),
  })


def construir_serie_mensal_dashboard(
  ano_referencia: int,
  resultados_ano_atual: list[NFeKPIConsulta],
  totais_vendidos: dict[tuple[int, Optional[int]], Decimal],
  totais_tributos: dict[tuple[int, Optional[int]], dict[str, Decimal]],
) -> list[SerieMensalVendasItem]:
  return [
    SerieMensalVendasItem(
      periodo_ano=ano_referencia,
      periodo_mes=item.periodo_mes or 0,
      total_vendido=totais_vendidos.get(
        (ano_referencia, item.periodo_mes),
        Decimal(str(item.kpis.total_vendas or 0)),
      ),
      quantidade_notas=int(item.kpis.quantidade_notas or 0),
      total_impostos=(
        Decimal(str(item.kpis.total_icms or 0))
        + Decimal(str(item.kpis.total_ipi or 0))
        + Decimal(str(item.kpis.total_pis or 0))
        + Decimal(str(item.kpis.total_cofins or 0))
      ),
      total_impostos_complementares=totais_tributos.get(
        (ano_referencia, item.periodo_mes),
        {},
      ).get("total_impostos_complementares", Decimal("0.00")),
      total_tributos_reforma=totais_tributos.get(
        (ano_referencia, item.periodo_mes),
        {},
      ).get("total_tributos_reforma", Decimal("0.00")),
    )
    for item in sorted(resultados_ano_atual, key=lambda resultado: resultado.periodo_mes or 0)
    if item.periodo_mes
  ]


def construir_dashboard_vendas_response(
  emitente_cnpj: str,
  ano_referencia: int,
  periodo_mes: Optional[int],
  anos_disponiveis: list[int],
  resumo_atual: DashboardVendasResumo,
  resumo_anterior: DashboardVendasResumo,
  serie_mensal: list[SerieMensalVendasItem],
) -> DashboardVendasResponse:
  return DashboardVendasResponse(
    status="ok",
    emitente_cnpj=emitente_cnpj,
    periodo_ano=ano_referencia,
    periodo_mes=periodo_mes,
    anos_disponiveis=anos_disponiveis,
    resumo_atual=resumo_atual,
    resumo_anterior=resumo_anterior,
    serie_mensal=serie_mensal,
  )
