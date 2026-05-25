from decimal import Decimal
from typing import Optional


def construir_filtros_compras_nfe(
  emitente_cnpj: str,
  periodo_ano: Optional[int] = None,
  periodo_mes: Optional[int] = None,
) -> tuple[str, list[object]]:
  filtros = [
    (
      "("
      "regexp_replace(COALESCE(n.destinatario_documento, ''), '\\D', '', 'g') = %s "
      "OR regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g') = %s"
      ")"
    ),
    "LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('1','2','3')",
  ]
  parametros: list[object] = [emitente_cnpj, emitente_cnpj]

  if periodo_ano:
    filtros.append("EXTRACT(YEAR FROM n.data_emissao) = %s")
    parametros.append(periodo_ano)

  if periodo_mes:
    filtros.append("EXTRACT(MONTH FROM n.data_emissao) = %s")
    parametros.append(periodo_mes)

  return " AND ".join(filtros), parametros


def construir_filtros_compras_sped(
  emitente_cnpj: str,
  periodo_ano: Optional[int] = None,
  periodo_mes: Optional[int] = None,
) -> tuple[str, list[object]]:
  filtros = [
    "regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s",
    "d.tipo_operacao = 'entrada'",
  ]
  parametros: list[object] = [emitente_cnpj]

  if periodo_ano:
    filtros.append("EXTRACT(YEAR FROM d.data_emissao) = %s")
    parametros.append(periodo_ano)
  if periodo_mes:
    filtros.append("EXTRACT(MONTH FROM d.data_emissao) = %s")
    parametros.append(periodo_mes)

  return " AND ".join(filtros), parametros


def construir_params_com_limite_compras(parametros: list[object], limite: Optional[int]) -> list[object]:
  return [*parametros, limite]


def construir_item_fornecedor_compras(
  fornecedor: str,
  valor_total: Decimal,
  quantidade_documentos: int,
) -> dict:
  return {
    "fornecedor": fornecedor,
    "valor_total": valor_total or Decimal("0.00"),
    "quantidade_documentos": quantidade_documentos or 0,
  }


def construir_ranking_fornecedores_compras(rows) -> list[dict]:
  return [
    construir_item_fornecedor_compras(fornecedor, valor_total, quantidade_documentos)
    for fornecedor, valor_total, quantidade_documentos in rows
  ]


def construir_item_produto_compras(
  produto: str,
  valor_total: Decimal,
  quantidade_total: Decimal,
) -> dict:
  return {
    "produto": produto,
    "valor_total": valor_total or Decimal("0.00"),
    "quantidade_total": quantidade_total or Decimal("0.00"),
  }


def construir_ranking_produtos_compras(rows) -> list[dict]:
  return [
    construir_item_produto_compras(produto, valor_total, quantidade_total)
    for produto, valor_total, quantidade_total in rows
  ]


def construir_resposta_analise_compras(
  emitente_cnpj: str,
  periodo_ano: Optional[int],
  periodo_mes: Optional[int],
  total_comprado: Decimal,
  total_impostos_complementares: Decimal,
  total_tributos_reforma: Decimal,
  top_fornecedores_valor: list[dict],
  top_fornecedores_quantidade: list[dict],
  top_produtos_valor: list[dict],
  top_produtos_quantidade: list[dict],
) -> dict:
  return {
    "emitente_cnpj": emitente_cnpj,
    "periodo_ano": periodo_ano,
    "periodo_mes": periodo_mes,
    "total_comprado": total_comprado or Decimal("0.00"),
    "total_impostos_complementares": total_impostos_complementares,
    "total_tributos_reforma": total_tributos_reforma,
    "top_fornecedores_valor": top_fornecedores_valor,
    "top_fornecedores_quantidade": top_fornecedores_quantidade,
    "top_produtos_valor": top_produtos_valor,
    "top_produtos_quantidade": top_produtos_quantidade,
  }
