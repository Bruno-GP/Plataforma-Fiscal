from decimal import Decimal
from typing import Optional


def construir_top_cfops(resultado_dimensoes: list[dict]) -> list[dict]:
  return [
    {
      "cfop": item["codigo"],
      "descricao": item["descricao"],
      "valor_total": item["valor_total"],
      "participacao_percentual": item["participacao_percentual"],
    }
    for item in resultado_dimensoes
  ]


def construir_top_ncms(resultado_dimensoes: list[dict]) -> list[dict]:
  return [
    {
      "ncm": item["codigo"],
      "descricao": item["descricao"],
      "valor_total": item["valor_total"],
      "participacao_percentual": item["participacao_percentual"],
    }
    for item in resultado_dimensoes
  ]


def construir_resposta_fiscal_cfop(
  emitente_cnpj: str,
  periodo_ano: Optional[int],
  periodo_mes: Optional[int],
  resultado: dict,
  total_impostos_complementares: Decimal,
  total_tributos_reforma: Decimal,
) -> dict:
  return {
    "emitente_cnpj": emitente_cnpj,
    "periodo_ano": periodo_ano,
    "periodo_mes": periodo_mes,
    "total_movimentado": resultado["total_movimentado"],
    "total_impostos_complementares": total_impostos_complementares,
    "total_tributos_reforma": total_tributos_reforma,
    "quantidade_documentos": resultado["quantidade_documentos"],
    "quantidade_cfops": resultado["quantidade_dimensoes"],
    "top_categorias": resultado["top_categorias"],
    "top_cfops": construir_top_cfops(resultado["top_dimensoes"]),
  }


def construir_resposta_fiscal_ncm(
  emitente_cnpj: str,
  periodo_ano: Optional[int],
  periodo_mes: Optional[int],
  resultado: dict,
  total_impostos_complementares: Decimal,
  total_tributos_reforma: Decimal,
) -> dict:
  return {
    "emitente_cnpj": emitente_cnpj,
    "periodo_ano": periodo_ano,
    "periodo_mes": periodo_mes,
    "total_movimentado": resultado["total_movimentado"],
    "total_impostos_complementares": total_impostos_complementares,
    "total_tributos_reforma": total_tributos_reforma,
    "quantidade_documentos": resultado["quantidade_documentos"],
    "quantidade_ncms": resultado["quantidade_dimensoes"],
    "top_ncms": construir_top_ncms(resultado["top_dimensoes"]),
  }
