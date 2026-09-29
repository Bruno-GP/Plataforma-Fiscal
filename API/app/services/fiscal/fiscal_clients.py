from decimal import Decimal
from typing import Optional


def construir_filtros_clientes_nfe(
  emitente_cnpj: str,
  periodo_ano: Optional[int] = None,
  periodo_mes: Optional[int] = None,
) -> tuple[str, list[object]]:
  filtros = [
    "regexp_replace(UPPER(COALESCE(n.emitente_cnpj, '')), '[^0-9A-Z]', '', 'g') = %s",
    "LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('5','6','7')",
  ]
  parametros: list[object] = [emitente_cnpj]

  if periodo_ano:
    filtros.append("EXTRACT(YEAR FROM n.data_emissao) = %s")
    parametros.append(periodo_ano)

  if periodo_mes:
    filtros.append("EXTRACT(MONTH FROM n.data_emissao) = %s")
    parametros.append(periodo_mes)

  return " AND ".join(filtros), parametros


def construir_filtros_clientes_sped(
  emitente_cnpj: str,
  periodo_ano: Optional[int] = None,
  periodo_mes: Optional[int] = None,
) -> tuple[str, list[object]]:
  filtros = [
    "regexp_replace(UPPER(d.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s",
    "d.tipo_operacao = 'saida'",
  ]
  parametros: list[object] = [emitente_cnpj]

  if periodo_ano:
    filtros.append("EXTRACT(YEAR FROM d.data_emissao) = %s")
    parametros.append(periodo_ano)

  if periodo_mes:
    filtros.append("EXTRACT(MONTH FROM d.data_emissao) = %s")
    parametros.append(periodo_mes)

  return " AND ".join(filtros), parametros


def construir_params_ranking_clientes(
  total_vendido: Decimal,
  parametros_filtro: list[object],
  limite: Optional[int],
) -> list[object]:
  total_base = total_vendido or Decimal("0.00")
  return [total_base, total_base, *parametros_filtro, limite]


def construir_item_cliente_analise(
  cliente: str,
  valor_total: Decimal,
  quantidade_documentos: int,
  ticket_medio: Decimal,
  percentual_participacao: Decimal,
) -> dict:
  return {
    "cliente": cliente,
    "valor_total": valor_total or Decimal("0.00"),
    "quantidade_documentos": quantidade_documentos or 0,
    "ticket_medio": ticket_medio or Decimal("0.00"),
    "percentual_participacao": percentual_participacao or Decimal("0.00"),
  }


def construir_ranking_clientes(rows) -> list[dict]:
  return [
    construir_item_cliente_analise(
      cliente,
      valor_total,
      quantidade_documentos,
      ticket_medio,
      percentual_participacao,
    )
    for cliente, valor_total, quantidade_documentos, ticket_medio, percentual_participacao in rows
  ]


def construir_resposta_analise_clientes(
  emitente_cnpj: str,
  periodo_ano: Optional[int],
  periodo_mes: Optional[int],
  total_vendido: Decimal,
  total_clientes: int,
  top_clientes_valor: list[dict],
  top_clientes_quantidade: list[dict],
) -> dict:
  return {
    "emitente_cnpj": emitente_cnpj,
    "periodo_ano": periodo_ano,
    "periodo_mes": periodo_mes,
    "total_vendido": total_vendido or Decimal("0.00"),
    "total_clientes": int(total_clientes or 0),
    "top_clientes_valor": top_clientes_valor,
    "top_clientes_quantidade": top_clientes_quantidade,
  }
