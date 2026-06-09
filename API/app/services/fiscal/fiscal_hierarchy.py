from decimal import Decimal
from typing import Callable, Optional


def _normalizar_ncm_filtro(valor: str) -> str:
  return "".join(ch for ch in valor if ch.isdigit())


def _expressao_estado_nfe() -> str:
  return "COALESCE(NULLIF(TRIM(n.destinatario_uf), ''), NULLIF(TRIM(e.estado), ''), 'Sem UF')"


def _expressao_cidade_nfe() -> str:
  return "COALESCE(NULLIF(TRIM(n.destinatario_cidade), ''), NULLIF(TRIM(e.cidade), ''), 'Cidade nao identificada')"


def construir_filtros_hierarquia_nfe(
  emitente_cnpj: str,
  periodo_ano: Optional[int] = None,
  periodo_mes: Optional[int] = None,
  estado: Optional[str] = None,
  cidade: Optional[str] = None,
  ncm: Optional[str] = None,
  produto_codigo: Optional[str] = None,
) -> tuple[str, list[object]]:
  filtros = [
    "regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g') = %s",
    "LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('5','6','7')",
  ]
  parametros: list[object] = [emitente_cnpj]

  if periodo_ano is not None:
    filtros.append("EXTRACT(YEAR FROM n.data_emissao) = %s")
    parametros.append(periodo_ano)

  if periodo_mes is not None:
    filtros.append("EXTRACT(MONTH FROM n.data_emissao) = %s")
    parametros.append(periodo_mes)

  if estado and estado.strip():
    filtros.append(f"UPPER({_expressao_estado_nfe()}) = %s")
    parametros.append(estado.strip().upper())

  if cidade and cidade.strip():
    filtros.append(f"UPPER({_expressao_cidade_nfe()}) = %s")
    parametros.append(cidade.strip().upper())

  if ncm and ncm.strip():
    filtros.append("regexp_replace(COALESCE(i.ncm, ''), '\\D', '', 'g') = %s")
    parametros.append(_normalizar_ncm_filtro(ncm))

  if produto_codigo and produto_codigo.strip():
    filtros.append("COALESCE(NULLIF(TRIM(i.produto_codigo), ''), 'SEM-CODIGO') = %s")
    parametros.append(produto_codigo.strip())

  return " AND ".join(filtros), parametros


def construir_filtros_hierarquia_sped(
  emitente_cnpj: str,
  periodo_ano: Optional[int] = None,
  periodo_mes: Optional[int] = None,
  estado: Optional[str] = None,
  cidade: Optional[str] = None,
  ncm: Optional[str] = None,
  produto_codigo: Optional[str] = None,
) -> dict:
  filtros_documentos = [
    "regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s",
    "d.tipo_operacao = 'saida'",
  ]
  params_documentos: list[object] = [emitente_cnpj]
  filtros_base: list[str] = []
  params_base: list[object] = []
  filtros_kpis = ["regexp_replace(cnpj_emitente, '\\D', '', 'g') = %s"]
  params_kpis: list[object] = [emitente_cnpj]

  if periodo_ano is not None:
    filtros_documentos.append("EXTRACT(YEAR FROM d.data_emissao) = %s")
    params_documentos.append(periodo_ano)
    filtros_kpis.append("periodo_ano = %s")
    params_kpis.append(periodo_ano)

  if periodo_mes is not None:
    filtros_documentos.append("EXTRACT(MONTH FROM d.data_emissao) = %s")
    params_documentos.append(periodo_mes)
    filtros_kpis.append("periodo_mes = %s")
    params_kpis.append(periodo_mes)

  if estado and estado.strip():
    filtros_base.append("UPPER(estado) = %s")
    params_base.append(estado.strip().upper())

  if cidade and cidade.strip():
    filtros_base.append("UPPER(cidade) = %s")
    params_base.append(cidade.strip().upper())

  if ncm and ncm.strip():
    filtros_base.append("ncm = %s")
    params_base.append(_normalizar_ncm_filtro(ncm) or "00000000")

  if produto_codigo and produto_codigo.strip():
    filtros_base.append("produto_codigo = %s")
    params_base.append(produto_codigo.strip())

  return {
    "where_documentos": " AND ".join(filtros_documentos),
    "where_kpis": " AND ".join(filtros_kpis),
    "where_base": " AND ".join(filtros_base) if filtros_base else "1 = 1",
    "params_documentos": params_documentos,
    "params_kpis": params_kpis,
    "params_base": params_base,
    "params_cte": [*params_documentos, *params_documentos],
  }


def calcular_percentual_imposto(
  imposto_valor: Decimal,
  faturamento: Decimal,
) -> Decimal:
  return (imposto_valor / faturamento) * Decimal("100") if faturamento else Decimal("0.00")


def calcular_imposto_por_percentual(
  faturamento: Decimal,
  percentual: Decimal,
) -> Decimal:
  return (faturamento * percentual) / Decimal("100") if faturamento else Decimal("0.00")


def resolver_nivel_hierarquia(
  nivel_atual: Optional[str],
  estado: Optional[str],
  cidade: Optional[str],
  ncm: Optional[str],
) -> str:
  return nivel_atual or ("produto" if ncm else "ncm" if cidade else "cidade" if estado else "estado")


def normalizar_paginacao_hierarquia(
  limite: Optional[int],
  offset: int,
  limite_padrao: int = 100000,
) -> tuple[int, int]:
  return limite if limite is not None else limite_padrao, max(offset, 0)


def deve_montar_hierarquia_legado(
  nivel_atual: Optional[str],
  estado: Optional[str],
  cidade: Optional[str],
  ncm: Optional[str],
  produto_codigo: Optional[str],
  offset: int,
) -> bool:
  return (
    nivel_atual is None
    and not estado
    and not cidade
    and not ncm
    and not produto_codigo
    and offset == 0
  )


def construir_item_hierarquia_completa(
  estado: str,
  cidade: str,
  ncm: str,
  descricao_ncm: str,
  produto_codigo: str,
  produto: str,
  faturamento: Decimal,
  imposto_valor: Decimal,
  normalizar_cidade: Optional[Callable[[str], str]] = None,
  sem_item_detalhado: Optional[bool] = None,
) -> dict:
  faturamento_item = faturamento or Decimal("0.00")
  imposto_item = imposto_valor or Decimal("0.00")
  item = {
    "estado": estado,
    "cidade": normalizar_cidade(cidade) if normalizar_cidade else cidade,
    "uf": estado,
    "ncm": ncm,
    "descricao_ncm": descricao_ncm,
    "produto_codigo": produto_codigo,
    "produto": produto,
    "faturamento": faturamento_item,
    "imposto_valor": imposto_item,
    "imposto_percentual": calcular_percentual_imposto(imposto_item, faturamento_item),
  }
  if sem_item_detalhado is not None:
    item["sem_item_detalhado"] = sem_item_detalhado
  return item


def construir_item_estado(
  estado: str,
  faturamento: Decimal,
  imposto_valor: Decimal,
) -> dict:
  faturamento_item = faturamento or Decimal("0.00")
  imposto_item = imposto_valor or Decimal("0.00")
  return {
    "estado": estado,
    "faturamento": faturamento_item,
    "imposto_valor": imposto_item,
    "imposto_percentual": calcular_percentual_imposto(imposto_item, faturamento_item),
  }


def construir_item_cidade(
  cidade: str,
  uf: str,
  faturamento: Decimal,
  imposto_valor: Decimal,
  normalizar_cidade: Optional[Callable[[str], str]] = None,
) -> dict:
  faturamento_item = faturamento or Decimal("0.00")
  imposto_item = imposto_valor or Decimal("0.00")
  return {
    "cidade": normalizar_cidade(cidade) if normalizar_cidade else cidade,
    "uf": uf,
    "faturamento": faturamento_item,
    "imposto_valor": imposto_item,
    "imposto_percentual": calcular_percentual_imposto(imposto_item, faturamento_item),
  }


def construir_item_ncm(
  ncm: str,
  descricao: str,
  quantidade_produtos: int,
  faturamento: Decimal,
  imposto_valor: Decimal,
) -> dict:
  faturamento_item = faturamento or Decimal("0.00")
  imposto_item = imposto_valor or Decimal("0.00")
  return {
    "ncm": ncm,
    "descricao": descricao,
    "quantidade_produtos": quantidade_produtos or 0,
    "faturamento": faturamento_item,
    "imposto_valor": imposto_item,
    "imposto_percentual": calcular_percentual_imposto(imposto_item, faturamento_item),
  }


def construir_item_produto(
  produto_codigo: str,
  produto: str,
  faturamento: Decimal,
  imposto_valor: Decimal,
) -> dict:
  faturamento_item = faturamento or Decimal("0.00")
  imposto_item = imposto_valor or Decimal("0.00")
  return {
    "produto_codigo": produto_codigo,
    "produto": produto,
    "faturamento": faturamento_item,
    "imposto_valor": imposto_item,
    "imposto_percentual": calcular_percentual_imposto(imposto_item, faturamento_item),
  }


def construir_resposta_hierarquia_fiscal(
  emitente_cnpj: str,
  periodo_ano: Optional[int],
  periodo_mes: Optional[int],
  nivel_atual: str,
  offset: int,
  limite: int,
  total_registros_nivel: int,
  total_faturamento: Decimal,
  total_impostos: Decimal,
  total_tributos_reforma: Decimal,
  percentual_impostos_sobre_faturamento: Decimal,
  resumo_row: Optional[tuple],
  hierarquia: list[dict],
  itens_nivel_atual: list[dict],
  por_estado: list[dict],
  por_cidade: list[dict],
  por_ncm: list[dict],
  por_produto: list[dict],
) -> dict:
  return {
    "emitente_cnpj": emitente_cnpj,
    "periodo_ano": periodo_ano,
    "periodo_mes": periodo_mes,
    "nivel_atual": nivel_atual,
    "offset": offset,
    "limite": limite,
    "total_registros_nivel": total_registros_nivel,
    "possui_mais_registros": (offset + len(itens_nivel_atual)) < total_registros_nivel,
    "total_faturamento": total_faturamento or Decimal("0.00"),
    "total_impostos": total_impostos or Decimal("0.00"),
    "total_tributos_reforma": total_tributos_reforma,
    "percentual_impostos_sobre_faturamento": percentual_impostos_sobre_faturamento,
    "quantidade_documentos": resumo_row[2] if resumo_row else 0,
    "total_estados": resumo_row[3] if resumo_row else 0,
    "total_cidades": resumo_row[4] if resumo_row else 0,
    "total_ncms": resumo_row[5] if resumo_row else 0,
    "total_produtos": resumo_row[6] if resumo_row else 0,
    "hierarquia": hierarquia,
    "itens_nivel_atual": itens_nivel_atual,
    "por_estado": por_estado,
    "por_cidade": por_cidade,
    "por_ncm": por_ncm,
    "por_produto": por_produto,
  }
