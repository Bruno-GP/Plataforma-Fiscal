from decimal import Decimal
from typing import Callable, Optional


def construir_filtros_vendas_sped(
  emitente_cnpj: str,
  periodo_ano: Optional[int] = None,
  periodo_mes: Optional[int] = None,
) -> tuple[str, list[object]]:
  filtros = [
    "regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s",
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


def construir_params_com_limite(parametros: list[object], limite: Optional[int]) -> list[object]:
  return [*parametros, limite]


def construir_item_cliente_vendas(
  cliente: str,
  valor_total: Decimal,
  quantidade_documentos: int,
) -> dict:
  return {
    "cliente": cliente,
    "valor_total": valor_total or Decimal("0.00"),
    "quantidade_documentos": quantidade_documentos or 0,
  }


def construir_ranking_clientes_vendas(rows) -> list[dict]:
  return [
    construir_item_cliente_vendas(cliente, valor_total, quantidade_documentos)
    for cliente, valor_total, quantidade_documentos in rows
  ]


def construir_item_produto_vendas(
  produto: str,
  valor_total: Decimal,
  quantidade_total: Decimal,
) -> dict:
  return {
    "produto": produto,
    "valor_total": valor_total or Decimal("0.00"),
    "quantidade_total": quantidade_total or Decimal("0.00"),
  }


def construir_ranking_produtos_vendas(rows) -> list[dict]:
  return [
    construir_item_produto_vendas(produto, valor_total, quantidade_total)
    for produto, valor_total, quantidade_total in rows
  ]


def construir_item_cfop_vendas(
  cfop: str,
  descricao: str,
  valor_total: Decimal,
  total_vendido: Decimal,
) -> dict:
  valor_item = valor_total or Decimal("0.00")
  return {
    "cfop": cfop,
    "descricao": descricao,
    "valor_total": valor_item,
    "participacao_percentual": (
      (valor_item / total_vendido) * Decimal("100")
      if total_vendido
      else Decimal("0.00")
    ),
  }


def construir_ranking_cfops_vendas(rows, total_vendido: Decimal) -> list[dict]:
  return [
    construir_item_cfop_vendas(cfop, descricao, valor_total, total_vendido)
    for cfop, descricao, valor_total in rows
  ]


def construir_item_cidade_vendas(
  cidade: str,
  uf: str,
  valor_total: Decimal,
  quantidade_documentos: int,
  normalizar_cidade: Optional[Callable[[str], str]] = None,
) -> dict:
  return {
    "cidade": normalizar_cidade(cidade) if normalizar_cidade else cidade,
    "uf": uf,
    "valor_total": valor_total or Decimal("0.00"),
    "quantidade_documentos": quantidade_documentos or 0,
  }


def construir_ranking_cidades_vendas(
  rows,
  normalizar_cidade: Optional[Callable[[str], str]] = None,
) -> list[dict]:
  return [
    construir_item_cidade_vendas(
      cidade,
      uf,
      valor_total,
      quantidade_documentos,
      normalizar_cidade=normalizar_cidade,
    )
    for cidade, uf, valor_total, quantidade_documentos in rows
  ]


def construir_ranking_regioes_vendas(
  rows,
  obter_regiao_por_uf: Callable[[str], Optional[str]],
  limite: Optional[int],
) -> list[dict]:
  regioes: dict[str, dict[str, Decimal | int | str]] = {}
  for uf, valor_total, quantidade_documentos in rows:
    regiao = obter_regiao_por_uf(uf)
    if not regiao:
      continue

    acumulado = regioes.setdefault(
      regiao,
      {
        "regiao": regiao,
        "valor_total": Decimal("0.00"),
        "quantidade_documentos": 0,
      },
    )
    acumulado["valor_total"] = Decimal(str(acumulado["valor_total"])) + (valor_total or Decimal("0.00"))
    acumulado["quantidade_documentos"] = int(acumulado["quantidade_documentos"]) + (quantidade_documentos or 0)

  return sorted(
    regioes.values(),
    key=lambda item: Decimal(str(item["valor_total"])),
    reverse=True,
  )[:limite]


def construir_resposta_analise_vendas(
  emitente_cnpj: str,
  periodo_ano: Optional[int],
  periodo_mes: Optional[int],
  total_vendido: Decimal,
  total_impostos_complementares: Decimal,
  total_tributos_reforma: Decimal,
  top_clientes_valor: list[dict],
  top_clientes_quantidade: list[dict],
  top_produtos_valor: list[dict],
  top_produtos_quantidade: list[dict],
  top_cfops_valor: list[dict],
  top_regioes_valor: list[dict],
  top_cidades_valor: list[dict],
) -> dict:
  return {
    "emitente_cnpj": emitente_cnpj,
    "periodo_ano": periodo_ano,
    "periodo_mes": periodo_mes,
    "total_vendido": total_vendido or Decimal("0.00"),
    "total_impostos_complementares": total_impostos_complementares,
    "total_tributos_reforma": total_tributos_reforma,
    "top_clientes_valor": top_clientes_valor,
    "top_clientes_quantidade": top_clientes_quantidade,
    "top_produtos_valor": top_produtos_valor,
    "top_produtos_quantidade": top_produtos_quantidade,
    "top_cfops_valor": top_cfops_valor,
    "top_regioes_valor": top_regioes_valor,
    "top_cidades_valor": top_cidades_valor,
  }
