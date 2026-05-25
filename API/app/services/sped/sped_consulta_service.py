from decimal import Decimal
from typing import Optional

import psycopg

from app.models.nfe.schemas import NFeKPI, NFeKPIConsulta
from app.services.fiscal_analysis import (
  FiscalDimensionConfig,
  analisar_fiscal_por_dimensao,
  obter_total_impostos_complementares_documentos,
  obter_total_tributos_reforma_documentos,
  obter_regiao_por_uf,
)
from app.services.fiscal_clients import (
  construir_filtros_clientes_sped,
  construir_params_ranking_clientes,
  construir_ranking_clientes,
  construir_resposta_analise_clientes,
)
from app.services.fiscal_hierarchy import (
  calcular_imposto_por_percentual,
  calcular_percentual_imposto,
  construir_filtros_hierarquia_sped,
  construir_item_cidade,
  construir_item_estado,
  construir_item_hierarquia_completa,
  construir_item_ncm,
  construir_item_produto,
  construir_resposta_hierarquia_fiscal,
  deve_montar_hierarquia_legado,
  normalizar_paginacao_hierarquia,
  resolver_nivel_hierarquia,
)
from app.services.fiscal_sales import (
  construir_filtros_vendas_sped,
  construir_params_com_limite,
  construir_ranking_cfops_vendas,
  construir_ranking_cidades_vendas,
  construir_ranking_regioes_vendas,
  construir_resposta_analise_vendas,
)
from app.services.nfe.empresa_service import normalizar_cnpj
from app.services.sped.postgres_config import carregar_config_postgres_sped

def _sped_ncm_expr(alias_produto: str = "pr") -> str:
  return f"COALESCE(NULLIF(regexp_replace(COALESCE({alias_produto}.ncm, ''), '\\D', '', 'g'), ''), '00000000')"

def _sped_produto_codigo_expr(alias_produto: str = "pr") -> str:
  return f"COALESCE(NULLIF(TRIM({alias_produto}.codigo), ''), 'SEM-CODIGO')"

SPED_CFOP_ANALYSIS_CONFIG = FiscalDimensionConfig(
  from_clause="""
    public.sped_documentos_fiscais d
    JOIN public.sped_documento_itens i ON i.documento_id = d.id
  """,
  company_filter_expr="regexp_replace(d.empresa_cnpj, '\\D', '', 'g')",
  date_expr="d.data_emissao",
  document_id_expr="d.id",
  amount_expr="i.valor_total",
  dimension_code_count_expr="regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g')",
  dimension_code_display_expr="TRIM(i.cfop)",
  dimension_description_expr="cf.descricao",
  category_description_expr="cf.descricao",
  sale_condition_expr=(
    "d.tipo_operacao = 'saida' "
    "AND LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('5','6','7')"
  ),
  reference_join_clause="""
    LEFT JOIN public.notas_cfops cf
      ON regexp_replace(COALESCE(cf.codigo, ''), '\\D', '', 'g')
         = regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g')
  """,
  unknown_description="CFOP sem descrião",
)

SPED_NCM_ANALYSIS_CONFIG = FiscalDimensionConfig(
  from_clause="""
    public.sped_documentos_fiscais d
    JOIN public.sped_documento_itens i ON i.documento_id = d.id
    LEFT JOIN public.sped_produtos pr ON pr.id = i.produto_id
  """,
  company_filter_expr="regexp_replace(d.empresa_cnpj, '\\D', '', 'g')",
  date_expr="d.data_emissao",
  document_id_expr="d.id",
  amount_expr="i.valor_total",
  dimension_code_count_expr=_sped_ncm_expr(),
  dimension_code_display_expr=_sped_ncm_expr(),
  dimension_description_expr="nc.descricao",
  category_description_expr="cf.descricao",
  sale_condition_expr=(
    "d.tipo_operacao = 'saida' "
    "AND LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('5','6','7')"
  ),
  reference_join_clause="""
    LEFT JOIN public.ncm_catalogo nc
      ON regexp_replace(COALESCE(nc.codigo, ''), '\\D', '', 'g')
         = COALESCE(NULLIF(regexp_replace(COALESCE(pr.ncm, ''), '\\D', '', 'g'), ''), '00000000')
    LEFT JOIN public.notas_cfops cf
      ON regexp_replace(COALESCE(cf.codigo, ''), '\\D', '', 'g')
         = regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g')
  """,
  unknown_code="00000000",
  unknown_description="NCM sem descrição",
)

def _parece_codigo_municipio(valor: object) -> bool:
  codigo = "".join(ch for ch in str(valor or "") if ch.isdigit())
  return len(codigo) in {6, 7}

def _normalizar_nome_cidade(valor: object) -> str:
  cidade = str(valor or "").strip()
  if not cidade:
    return "Cidade não identificada"

  cidade_upper = cidade.upper()
  if len(cidade_upper) == 2 and cidade_upper.isalpha():
    return "Cidade não identificada"
  
  if _parece_codigo_municipio(cidade):
    return "Cidade não identificada"

  for separador in ("/", "-"):
    if separador in cidade:
      partes = [p.strip() for p in cidade.split(separador) if p.strip()]
      if len(partes) >= 2:
        ultimo = partes[-1].upper()
        if len(ultimo) == 2 and ultimo.isalpha():
          return f"{partes[0]} - {ultimo}"

  return cidade

def _categoria_fiscal_case_sped() -> str:
  return """
    CASE
      WHEN d.tipo_operacao = 'saida'
        AND LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('5','6','7')
        THEN 'Venda'
      WHEN COALESCE(cf.descricao, '') ILIKE '%%devol%%' THEN 'Devolução'
      WHEN COALESCE(cf.descricao, '') ILIKE '%%bonific%%'
        OR COALESCE(cf.descricao, '') ILIKE '%%brinde%%'
        OR COALESCE(cf.descricao, '') ILIKE '%%doaç%%'
        OR COALESCE(cf.descricao, '') ILIKE '%%doac%%' THEN 'Bonificação'
      WHEN COALESCE(cf.descricao, '') ILIKE '%%remessa%%'
        OR COALESCE(cf.descricao, '') ILIKE '%%demonstra%%'
        OR COALESCE(cf.descricao, '') ILIKE '%%conserto%%'
        OR COALESCE(cf.descricao, '') ILIKE '%%comodato%%'
        OR COALESCE(cf.descricao, '') ILIKE '%%industrializa%%' THEN 'Remessa'
      WHEN COALESCE(cf.descricao, '') ILIKE '%%transfer%%' THEN 'Transferência'
      WHEN COALESCE(cf.descricao, '') ILIKE '%%substitui%%'
        OR COALESCE(cf.descricao, '') ILIKE '%%subst. trib%%'
        OR COALESCE(cf.descricao, '') ILIKE '%%st%%' THEN 'Substituição Tributária'
      ELSE 'Outras operações'
    END
  """

class SpedConsultaService:
  _required_kpis_columns = {
    "id",
    "processamento_id",
    "cnpj_emitente",
    "periodo_ano",
    "periodo_mes",
    "total_documentos",
    "total_itens",
    "valor_total_saidas",
    "valor_total_produtos",
    "valor_total_frete",
    "valor_total_descontos",
    "icms_valor_debitado",
    "ipi_valor",
    "pis_valor",
    "cofins_valor",
    "ticket_medio",
    "data_calculo",
  }

  def __init__(self) -> None:
    config = carregar_config_postgres_sped()
    self.conn_params = {
      "host": config["host"],
      "port": config["port"],
      "dbname": config["database"],
      "user": config["user"],
      "password": config["password"],
      "connect_timeout": 5,
    }

  def listar_kpis(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: int = 100,
    offset: int = 0,
  ) -> list[NFeKPIConsulta]:
    cnpj = normalizar_cnpj(emitente_cnpj)
    filtros = ["regexp_replace(cnpj_emitente, '\\D', '', 'g') = %s"]
    params: list[object] = [cnpj]

    if periodo_ano:
      filtros.append("periodo_ano = %s")
      params.append(periodo_ano)
    if periodo_mes:
      filtros.append("periodo_mes = %s")
      params.append(periodo_mes)

    where_clause = " AND ".join(filtros)

    sql_kpis = f"""
      SELECT id,
            processamento_id,
            cnpj_emitente,
            periodo_ano,
            periodo_mes,
            valor_total_saidas,
            total_documentos,
            ticket_medio,
            0::numeric AS maior_nota,
            0::numeric AS menor_nota,
            icms_valor_debitado,
            ipi_valor,
            pis_valor,
            cofins_valor
      FROM public.sped_kpis_fiscal
      WHERE {where_clause}
      ORDER BY periodo_ano DESC, periodo_mes DESC, id DESC
      LIMIT %s OFFSET %s;
    """

    params.extend([limite, offset])

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
          self._validar_tabela_kpis(cur)
          cur.execute(sql_kpis, params)
          rows = cur.fetchall()

          resultados: list[NFeKPIConsulta] = []
          for row in rows:
            kpi_id, processamento_id, cnpj_emitente, ano, mes, total_vendas, total_docs, ticket_medio, maior_nota, menor_nota, total_icms, total_ipi, total_pis, total_cofins = row
            top_clientes = self._top_clientes(cur, cnpj, ano, mes)
            top_cidades = self._top_cidades(cur, cnpj, ano, mes)
            top_produtos = self._top_produtos(cur, cnpj, ano, mes)

            resultados.append(
              NFeKPIConsulta(
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
              )

          return resultados

  def _validar_tabela_kpis(self, cur) -> None:
    cur.execute(
      """
      SELECT column_name
      FROM information_schema.columns
      WHERE table_schema = 'public'
        AND table_name = 'sped_kpis_fiscal'
      """
    )
    existing_columns = {str(row[0]) for row in cur.fetchall()}
    missing_columns = sorted(self._required_kpis_columns - existing_columns)
    if missing_columns:
      raise RuntimeError(
        "Tabela public.sped_kpis_fiscal incompleta ou ausente. Execute as migrations Alembic. "
        f"Colunas ausentes: {', '.join(missing_columns)}."
      )

  def _top_clientes(self, cur, cnpj: str, ano: int, mes: int) -> list[dict]:
    return self._safe_top_query(
      cur,
      """
      SELECT COALESCE(p.nome, 'Cliente não identificado') AS cliente,
      SUM(d.valor_total) AS valor_total
      FROM public.sped_documentos_fiscais d
      LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
      WHERE regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s
        AND d.tipo_operacao = 'saida'
        AND EXTRACT(YEAR FROM d.data_emissao) = %s
        AND EXTRACT(MONTH FROM d.data_emissao) = %s
      GROUP BY 1
      ORDER BY 2 DESC;
      """,
      (cnpj, ano, mes),
      "cliente",
    )

  def _top_cidades(self, cur, cnpj: str, ano: int, mes: int) -> list[dict]:
    sql_cidades_sped = """
      SELECT CONCAT(
        COALESCE(
          NULLIF(TRIM(p.municipio_nome), ''),
          NULLIF(TRIM(p.municipio), ''),
          'Cidade não identificada'
        ),
        CASE
          WHEN NULLIF(TRIM(p.uf), '') IS NOT NULL THEN CONCAT(' - ', UPPER(TRIM(p.uf)))
          ELSE ''
        END
      ) AS cidade,
      SUM(d.valor_total) AS valor_total
      FROM public.sped_documentos_fiscais d
      LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
      WHERE regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s
        AND d.tipo_operacao = 'saida'
        AND EXTRACT(YEAR FROM d.data_emissao) = %s
        AND EXTRACT(MONTH FROM d.data_emissao) = %s
      GROUP BY 1
      ORDER BY 2 DESC;
    """

    cidades = self._safe_top_query(cur, sql_cidades_sped, (cnpj, ano, mes), "cidade")
    
    cidades_agrupadas: dict[str, Decimal] = {}
    for item in cidades:
      if not isinstance(item, dict):
        continue

      cidade = _normalizar_nome_cidade(item.get("cidade"))
      valor_total = item.get("valor_total") or Decimal("0.00")
      cidades_agrupadas[cidade] = cidades_agrupadas.get(cidade, Decimal("0.00")) + Decimal(valor_total)

    return [
      {"cidade": cidade, "valor_total": valor_total}
      for cidade, valor_total in sorted(
        cidades_agrupadas.items(),
        key=lambda x: x[1],
        reverse=True,
      )
    ]

  def _top_produtos(self, cur, cnpj: str, ano: int, mes: int) -> list[dict]:
    return self._safe_top_query(
      cur,
      """
      SELECT COALESCE(pr.descricao, 'Produto não identificado') AS produto,
      SUM(i.valor_total) AS valor_total
      FROM public.sped_documentos_fiscais d
      JOIN public.sped_documento_itens i ON i.documento_id = d.id
      LEFT JOIN public.sped_produtos pr ON pr.id = i.produto_id
      WHERE regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s
        AND EXTRACT(YEAR FROM d.data_emissao) = %s
        AND EXTRACT(MONTH FROM d.data_emissao) = %s
      GROUP BY 1
      ORDER BY 2 DESC
      LIMIT 5;
      """,
      (cnpj, ano, mes),
      "produto",
    )

  def _safe_top_query(self, cur, sql: str, params: tuple[object, ...], label: str) -> list[dict]:
    try:
      cur.execute(sql, params)
      return [{label: nome, "valor_total": valor or Decimal("0.00")} for nome, valor in cur.fetchall()]
    except psycopg.errors.UndefinedTable:
      return []
    
  def listar_clientes(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: Optional[int] = None,
    offset: int = 0,
  ) -> dict:
    cnpj = normalizar_cnpj(emitente_cnpj)
    filtros = ["regexp_replace(d.empresa_cnpj, \'\\D\', \'\', \'g\') = %s", "d.tipo_operacao = 'saida'"]
    params: list[object] = [cnpj]

    if periodo_ano:
      filtros.append("EXTRACT(YEAR FROM d.data_emissao) = %s")
      params.append(periodo_ano)
    if periodo_mes:
      filtros.append("EXTRACT(MONTH FROM d.data_emissao) = %s")
      params.append(periodo_mes)

    where_clause = " AND ".join(filtros)

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        total_vendas = self._safe_scalar_query(
          cur,
          f"""
          SELECT COALESCE(SUM(d.valor_total), 0)
          FROM public.sped_documentos_fiscais d
          WHERE {where_clause}
          """,
          tuple(params),
        )

        ticket_medio = self._safe_scalar_query(
          cur,
          f"""
          SELECT COALESCE(AVG(d.valor_total), 0)
          FROM public.sped_documentos_fiscais d
          WHERE {where_clause}
          """,
          tuple(params),
        )

        sql_clientes = f"""
          SELECT
            COALESCE(NULLIF(TRIM(p.nome), ''), 'Cliente não identificado') AS cliente,
            COALESCE(SUM(d.valor_total), 0) AS valor_total
          FROM public.sped_documentos_fiscais d
          LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC, 1 ASC
        """
        query_params: list[object] = [*params]
        if limite is not None:
          sql_clientes += "\n LIMIT %s OFFSET %s"
          query_params.extend([limite, offset])

        cur.execute(sql_clientes, tuple(query_params))

        clientes_rows = cur.fetchall()

        total_clientes = self._safe_scalar_query(
          cur,
          f"""
          SELECT COUNT(*)
          FROM (
            SELECT 1
            FROM public.sped_documentos_fiscais d
            LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
            WHERE {where_clause}
            GROUP BY COALESCE(NULLIF(TRIM(p.nome), ''), 'Cliente não identificado')
          ) clientes
          """,
          tuple(params),
        )

    total_vendas_decimal = Decimal(total_vendas or 0)
    resultados = []
    for cliente, valor_total in clientes_rows:
      valor_total_decimal = Decimal(valor_total or 0)
      percentual = Decimal("0.00")
      if total_vendas_decimal > 0:
        percentual = (valor_total_decimal / total_vendas_decimal) * Decimal("100")

      resultados.append({
        "cliente": cliente,
        "valor_total": valor_total_decimal,
        "percentual": percentual,
      })

    return {
      "emitente_cnpj": cnpj,
      "periodo_ano": periodo_ano,
      "periodo_mes": periodo_mes,
      "total_clientes": int(total_clientes or 0),
      "total_vendas": total_vendas_decimal,
      "ticket_medio": Decimal(ticket_medio or 0),
      "resultados": resultados,
    }
    
  def analisar_compras(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: int = 5,
  ) -> dict:
    cnpj = normalizar_cnpj(emitente_cnpj)
    filtros = ["regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s", "d.tipo_operacao = 'entrada'"]
    params: list[object] = [cnpj]

    if periodo_ano:
      filtros.append("EXTRACT(YEAR FROM d.data_emissao) = %s")
      params.append(periodo_ano)
    if periodo_mes:
      filtros.append("EXTRACT(MONTH FROM d.data_emissao) = %s")
      params.append(periodo_mes)

    where_clause = " AND ".join(filtros)

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        total_comprado = self._safe_scalar_query(
          cur,
          f"""
          SELECT COALESCE(SUM(d.valor_total), 0)
          FROM public.sped_documentos_fiscais d
          WHERE {where_clause}
          """,
          tuple(params),
        )

        top_fornecedores_valor = self._safe_top_fornecedor_query(
          cur,
          f"""
          SELECT COALESCE(p.nome, 'Fornecedor não identificado') AS fornecedor,
                COALESCE(SUM(d.valor_total), 0) AS valor_total,
                COUNT(*) AS quantidade_documentos
          FROM public.sped_documentos_fiscais d
          LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC
          LIMIT %s
          """,
          tuple([*params, limite]),
        )

        top_fornecedores_quantidade = self._safe_top_fornecedor_query(
          cur,
          f"""
          SELECT COALESCE(p.nome, 'Fornecedor não identificado') AS fornecedor,
                COALESCE(SUM(d.valor_total), 0) AS valor_total,
                COUNT(*) AS quantidade_documentos
          FROM public.sped_documentos_fiscais d
          LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 3 DESC, 2 DESC
          LIMIT %s
          """,
          tuple([*params, limite]),
        )

        top_produtos_valor = self._safe_top_produto_query(
          cur,
          f"""
          SELECT COALESCE(pr.descricao, 'Produto não identificado') AS produto,
                COALESCE(SUM(i.valor_total), 0) AS valor_total,
                COALESCE(SUM(i.quantidade), 0) AS quantidade_total
          FROM public.sped_documentos_fiscais d
          JOIN public.sped_documento_itens i ON i.documento_id = d.id
          LEFT JOIN public.sped_produtos pr ON pr.id = i.produto_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC
          LIMIT %s
          """,
          tuple([*params, limite]),
        )

        top_produtos_quantidade = self._safe_top_produto_query(
          cur,
          f"""
          SELECT COALESCE(pr.descricao, 'Produto não identificado') AS produto,
                COALESCE(SUM(i.valor_total), 0) AS valor_total,
                COALESCE(SUM(i.quantidade), 0) AS quantidade_total
          FROM public.sped_documentos_fiscais d
          JOIN public.sped_documento_itens i ON i.documento_id = d.id
          LEFT JOIN public.sped_produtos pr ON pr.id = i.produto_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 3 DESC, 2 DESC
          LIMIT %s
          """,
          tuple([*params, limite]),
        )

        return {
          "emitente_cnpj": cnpj,
          "periodo_ano": periodo_ano,
          "periodo_mes": periodo_mes,
          "total_comprado": total_comprado,
          "total_impostos_complementares": obter_total_impostos_complementares_documentos(
            self.conn_params,
            "sped",
            cnpj,
            periodo_ano,
            periodo_mes,
            "entrada",
          ),
          "total_tributos_reforma": obter_total_tributos_reforma_documentos(
            self.conn_params,
            "sped",
            cnpj,
            periodo_ano,
            periodo_mes,
            "entrada",
          ),
          "top_fornecedores_valor": top_fornecedores_valor,
          "top_fornecedores_quantidade": top_fornecedores_quantidade,
          "top_produtos_valor": top_produtos_valor,
          "top_produtos_quantidade": top_produtos_quantidade,
        }
        
  def analisar_vendas(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: Optional[int] = None,
  ) -> dict:
    cnpj = normalizar_cnpj(emitente_cnpj)
    where_clause, params = construir_filtros_vendas_sped(
      cnpj,
      periodo_ano,
      periodo_mes,
    )

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        total_vendido = self._safe_scalar_query(
          cur,
          f"""
          SELECT COALESCE(SUM(d.valor_total), 0)
          FROM public.sped_documentos_fiscais d
          WHERE {where_clause}
          """,
          tuple(params),
        )

        top_clientes_valor = self._safe_top_cliente_query(
          cur,
          f"""
          SELECT COALESCE(p.nome, 'Cliente não identificado') AS cliente,
                COALESCE(SUM(d.valor_total), 0) AS valor_total,
                COUNT(*) AS quantidade_documentos
          FROM public.sped_documentos_fiscais d
          LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC, 1 ASC
          LIMIT %s
          """,
          tuple(construir_params_com_limite(params, limite)),
        )

        top_clientes_quantidade = self._safe_top_cliente_query(
          cur,
          f"""
          SELECT COALESCE(p.nome, 'Cliente não identificado') AS cliente,
                COALESCE(SUM(d.valor_total), 0) AS valor_total,
                COUNT(*) AS quantidade_documentos
          FROM public.sped_documentos_fiscais d
          LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 3 DESC, 2 DESC, 1 ASC
          LIMIT %s
          """,
          tuple(construir_params_com_limite(params, limite)),
        )

        top_produtos_valor = self._safe_top_produto_query(
          cur,
          f"""
          SELECT COALESCE(pr.descricao, 'Produto não identificado') AS produto,
                COALESCE(SUM(i.valor_total), 0) AS valor_total,
                COALESCE(SUM(i.quantidade), 0) AS quantidade_total
          FROM public.sped_documentos_fiscais d
          JOIN public.sped_documento_itens i ON i.documento_id = d.id
          LEFT JOIN public.sped_produtos pr ON pr.id = i.produto_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC, 1 ASC
          LIMIT %s
          """,
          tuple(construir_params_com_limite(params, limite)),
        )

        top_produtos_quantidade = self._safe_top_produto_query(
          cur,
          f"""
          SELECT COALESCE(pr.descricao, 'Produto não identificado') AS produto,
                COALESCE(SUM(i.valor_total), 0) AS valor_total,
                COALESCE(SUM(i.quantidade), 0) AS quantidade_total
          FROM public.sped_documentos_fiscais d
          JOIN public.sped_documento_itens i ON i.documento_id = d.id
          LEFT JOIN public.sped_produtos pr ON pr.id = i.produto_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 3 DESC, 2 DESC, 1 ASC
          LIMIT %s
          """,
          tuple(construir_params_com_limite(params, limite)),
        )

        cur.execute(
          f"""
          SELECT COALESCE(NULLIF(TRIM(i.cfop), ''), '0000') AS cfop,
                COALESCE(NULLIF(TRIM(cf.descricao), ''), 'CFOP sem descrição') AS descricao,
                COALESCE(SUM(i.valor_total), 0) AS valor_total
          FROM public.sped_documentos_fiscais d
          JOIN public.sped_documento_itens i ON i.documento_id = d.id
          LEFT JOIN public.notas_cfops cf
            ON regexp_replace(COALESCE(cf.codigo, ''), '\\D', '', 'g')
               = regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g')
          WHERE {where_clause}
          GROUP BY 1, 2
          ORDER BY 3 DESC, 1 ASC
          LIMIT %s
          """,
          tuple(construir_params_com_limite(params, limite)),
        )
        top_cfops_valor = construir_ranking_cfops_vendas(cur.fetchall(), total_vendido)

        cur.execute(
          f"""
          SELECT CONCAT(
                  COALESCE(
                    NULLIF(TRIM(p.municipio_nome), ''),
                    NULLIF(TRIM(p.municipio), ''),
                    'Cidade não identificada'
                  ),
                  CASE
                    WHEN NULLIF(TRIM(p.uf), '') IS NOT NULL THEN CONCAT(' - ', UPPER(TRIM(p.uf)))
                    ELSE ''
                  END
                ) AS cidade,
                COALESCE(NULLIF(TRIM(p.uf), ''), '') AS uf,
                COALESCE(SUM(d.valor_total), 0) AS valor_total,
                COUNT(*) AS quantidade_documentos
          FROM public.sped_documentos_fiscais d
          LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
          WHERE {where_clause}
          GROUP BY 1, 2
          ORDER BY 3 DESC, 1 ASC
          LIMIT %s
          """,
          tuple(construir_params_com_limite(params, limite)),
        )
        top_cidades_valor = construir_ranking_cidades_vendas(
          cur.fetchall(),
          normalizar_cidade=_normalizar_nome_cidade,
        )

        cur.execute(
          f"""
          SELECT COALESCE(NULLIF(TRIM(p.uf), ''), '') AS uf,
                COALESCE(SUM(d.valor_total), 0) AS valor_total,
                COUNT(*) AS quantidade_documentos
          FROM public.sped_documentos_fiscais d
          LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC, 1 ASC
          """,
          tuple(params),
        )
        top_regioes_valor = construir_ranking_regioes_vendas(
          cur.fetchall(),
          obter_regiao_por_uf,
          limite,
        )

        total_impostos_complementares = obter_total_impostos_complementares_documentos(
          self.conn_params,
          "sped",
          cnpj,
          periodo_ano,
          periodo_mes,
          "saida",
        )
        total_tributos_reforma = obter_total_tributos_reforma_documentos(
          self.conn_params,
          "sped",
          cnpj,
          periodo_ano,
          periodo_mes,
          "saida",
        )

        return construir_resposta_analise_vendas(
          cnpj,
          periodo_ano,
          periodo_mes,
          total_vendido,
          total_impostos_complementares,
          total_tributos_reforma,
          top_clientes_valor,
          top_clientes_quantidade,
          top_produtos_valor,
          top_produtos_quantidade,
          top_cfops_valor,
          top_regioes_valor,
          top_cidades_valor,
        )

  def analisar_fiscal_cfop(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: Optional[int] = None,
  ) -> dict:
    cnpj = normalizar_cnpj(emitente_cnpj)
    resultado = analisar_fiscal_por_dimensao(
      conn_params=self.conn_params,
      config=SPED_CFOP_ANALYSIS_CONFIG,
      emitente_cnpj=cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      limite=limite,
    )
    total_impostos_complementares = obter_total_impostos_complementares_documentos(
      conn_params=self.conn_params,
      origem_documento="sped",
      emitente_cnpj=cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
    )
    total_tributos_reforma = obter_total_tributos_reforma_documentos(
      conn_params=self.conn_params,
      origem_documento="sped",
      emitente_cnpj=cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
    )

    return {
      "emitente_cnpj": cnpj,
      "periodo_ano": periodo_ano,
      "periodo_mes": periodo_mes,
      "total_movimentado": resultado["total_movimentado"],
      "total_impostos_complementares": total_impostos_complementares,
      "total_tributos_reforma": total_tributos_reforma,
      "quantidade_documentos": resultado["quantidade_documentos"],
      "quantidade_cfops": resultado["quantidade_dimensoes"],
      "top_categorias": resultado["top_categorias"],
      "top_cfops": [
        {
          "cfop": item["codigo"],
          "descricao": item["descricao"],
          "valor_total": item["valor_total"],
          "participacao_percentual": item["participacao_percentual"],
        }
        for item in resultado["top_dimensoes"]
      ],
    }

  def analisar_fiscal_ncm(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: Optional[int] = None,
  ) -> dict:
    cnpj = normalizar_cnpj(emitente_cnpj)
    resultado = analisar_fiscal_por_dimensao(
      conn_params=self.conn_params,
      config=SPED_NCM_ANALYSIS_CONFIG,
      emitente_cnpj=cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      limite=limite,
    )
    total_impostos_complementares = obter_total_impostos_complementares_documentos(
      conn_params=self.conn_params,
      origem_documento="sped",
      emitente_cnpj=cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
    )
    total_tributos_reforma = obter_total_tributos_reforma_documentos(
      conn_params=self.conn_params,
      origem_documento="sped",
      emitente_cnpj=cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
    )

    return {
      "emitente_cnpj": cnpj,
      "periodo_ano": periodo_ano,
      "periodo_mes": periodo_mes,
      "total_movimentado": resultado["total_movimentado"],
      "total_impostos_complementares": total_impostos_complementares,
      "total_tributos_reforma": total_tributos_reforma,
      "quantidade_documentos": resultado["quantidade_documentos"],
      "quantidade_ncms": resultado["quantidade_dimensoes"],
      "top_ncms": [
        {
          "ncm": item["codigo"],
          "descricao": item["descricao"],
          "valor_total": item["valor_total"],
          "participacao_percentual": item["participacao_percentual"],
        }
        for item in resultado["top_dimensoes"]
      ],
    }

  def analisar_fiscal_hierarquia(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    nivel_atual: Optional[str] = None,
    estado: Optional[str] = None,
    cidade: Optional[str] = None,
    ncm: Optional[str] = None,
    produto_codigo: Optional[str] = None,
    limite: Optional[int] = None,
    offset: int = 0,
  ) -> dict:
    cnpj = normalizar_cnpj(emitente_cnpj)
    filtros_hierarquia = construir_filtros_hierarquia_sped(
      cnpj,
      periodo_ano,
      periodo_mes,
      estado,
      cidade,
      ncm,
      produto_codigo,
    )
    where_clause_documentos = filtros_hierarquia["where_documentos"]
    where_clause_kpis = filtros_hierarquia["where_kpis"]
    where_clause_base = filtros_hierarquia["where_base"]
    params_kpis = filtros_hierarquia["params_kpis"]
    params_base = filtros_hierarquia["params_base"]
    params_cte = filtros_hierarquia["params_cte"]
    limite_consulta, offset_consulta = normalizar_paginacao_hierarquia(limite, offset)
    modo_legado_hierarquia_completa = deve_montar_hierarquia_legado(
      nivel_atual,
      estado,
      cidade,
      ncm,
      produto_codigo,
      offset_consulta,
    )

    base_cte = f"""
      WITH tributos_item AS (
        SELECT
          sped_item_id,
          COALESCE(
            NULLIF(SUM(valor_tributo), 0),
            SUM(valor_debito) - SUM(valor_credito),
            0
          ) AS imposto_valor
        FROM public.itens_documentos_fiscais_tributos
        WHERE sped_item_id IS NOT NULL
        GROUP BY sped_item_id
      ),
      base AS (
        SELECT
          d.id AS documento_id,
          i.id AS item_id,
          COALESCE(NULLIF(TRIM(p.uf), ''), 'Sem UF') AS estado,
          COALESCE(
            NULLIF(TRIM(p.municipio_nome), ''),
            NULLIF(TRIM(p.municipio), ''),
            'Cidade nao identificada'
          ) AS cidade,
          {_sped_ncm_expr()} AS ncm,
          COALESCE(NULLIF(TRIM(nc.descricao), ''), 'NCM sem descricao') AS descricao_ncm,
          {_sped_produto_codigo_expr()} AS produto_codigo,
          COALESCE(NULLIF(TRIM(pr.descricao), ''), 'Produto sem descricao') AS produto_descricao,
          COALESCE(i.valor_total, 0) AS faturamento,
          COALESCE(tributos.imposto_valor, 0) AS imposto_valor,
          FALSE AS sem_item_detalhado
        FROM public.sped_documentos_fiscais d
        JOIN public.sped_documento_itens i
          ON i.documento_id = d.id
        LEFT JOIN tributos_item AS tributos
          ON tributos.sped_item_id = i.id
        LEFT JOIN public.sped_participantes p
          ON p.id = d.participante_id
        LEFT JOIN public.sped_produtos pr
          ON pr.id = i.produto_id
        LEFT JOIN public.ncm_catalogo nc
          ON regexp_replace(COALESCE(nc.codigo, ''), '\\D', '', 'g')
             = {_sped_ncm_expr()}
        WHERE {where_clause_documentos}

        UNION ALL

        SELECT
          d.id AS documento_id,
          NULL::integer AS item_id,
          COALESCE(NULLIF(TRIM(p.uf), ''), 'Sem UF') AS estado,
          COALESCE(
            NULLIF(TRIM(p.municipio_nome), ''),
            NULLIF(TRIM(p.municipio), ''),
            'Cidade nao identificada'
          ) AS cidade,
          '00000000' AS ncm,
          'NCM sem descricao' AS descricao_ncm,
          'SEM-CODIGO' AS produto_codigo,
          'Produto sem descricao' AS produto_descricao,
          COALESCE(d.valor_total, 0) AS faturamento,
          0::numeric AS imposto_valor,
          TRUE AS sem_item_detalhado
        FROM public.sped_documentos_fiscais d
        LEFT JOIN public.sped_participantes p
          ON p.id = d.participante_id
        WHERE {where_clause_documentos}
          AND NOT EXISTS (
            SELECT 1
            FROM public.sped_documento_itens i
            WHERE i.documento_id = d.id
          )
      )
    """

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(
          f"""
          SELECT
            COALESCE(SUM(icms_valor_debitado), 0) + COALESCE(SUM(ipi_valor), 0)
          FROM public.sped_kpis_fiscal
          WHERE {where_clause_kpis}
          """,
          tuple(params_kpis),
        )
        row_total_impostos = cur.fetchone()
        total_impostos_periodo = row_total_impostos[0] if row_total_impostos else Decimal("0.00")

        cur.execute("DROP TABLE IF EXISTS tmp_sped_fiscal_hierarquia_base")
        cur.execute(
          f"""
          CREATE TEMP TABLE tmp_sped_fiscal_hierarquia_base ON COMMIT DROP AS
          {base_cte}
          SELECT *
          FROM base
          """,
          tuple(params_cte),
        )
        cur.execute("ANALYZE tmp_sped_fiscal_hierarquia_base")

        cur.execute("DROP TABLE IF EXISTS tmp_sped_fiscal_hierarquia_base_filtrada")
        cur.execute(
          f"""
          CREATE TEMP TABLE tmp_sped_fiscal_hierarquia_base_filtrada ON COMMIT DROP AS
          SELECT *
          FROM tmp_sped_fiscal_hierarquia_base
          WHERE {where_clause_base}
          """,
          tuple(params_base),
        )
        cur.execute("ANALYZE tmp_sped_fiscal_hierarquia_base_filtrada")

        cur.execute(
          """
          SELECT
            COALESCE(SUM(faturamento), 0) AS total_faturamento,
            COALESCE(SUM(imposto_valor), 0) AS total_impostos_complementares,
            COUNT(DISTINCT documento_id) AS quantidade_documentos,
            COUNT(DISTINCT estado) AS total_estados,
            COUNT(DISTINCT CONCAT(cidade, '::', estado)) AS total_cidades,
            COUNT(DISTINCT CASE WHEN NOT sem_item_detalhado THEN ncm END) AS total_ncms,
            COUNT(DISTINCT CASE WHEN NOT sem_item_detalhado THEN CONCAT(produto_codigo, '::', produto_descricao) END) AS total_produtos
          FROM tmp_sped_fiscal_hierarquia_base_filtrada
          """,
        )
        resumo_row = cur.fetchone()

        total_faturamento = resumo_row[0] if resumo_row else Decimal("0.00")
        total_impostos_complementares = resumo_row[1] if resumo_row else Decimal("0.00")
        cur.execute(
          """
          SELECT COALESCE(SUM(faturamento), 0)
          FROM tmp_sped_fiscal_hierarquia_base
          """,
        )
        row_faturamento_periodo = cur.fetchone()
        total_faturamento_periodo = row_faturamento_periodo[0] if row_faturamento_periodo else Decimal("0.00")
        percentual_total = calcular_percentual_imposto(total_impostos_periodo, total_faturamento_periodo)
        usar_impostos_complementares = total_impostos_complementares > 0
        total_impostos = (
          total_impostos_complementares
          if usar_impostos_complementares
          else calcular_imposto_por_percentual(total_faturamento, percentual_total)
        )
        hierarquia = []
        if modo_legado_hierarquia_completa:
          cur.execute(
            """
            SELECT
              estado,
              cidade,
              ncm,
              descricao_ncm,
              produto_codigo,
              produto_descricao,
              sem_item_detalhado,
              COALESCE(SUM(faturamento), 0) AS faturamento,
              COALESCE(SUM(imposto_valor), 0) AS imposto_valor
            FROM tmp_sped_fiscal_hierarquia_base_filtrada
            GROUP BY 1, 2, 3, 4, 5, 6, 7
            ORDER BY 1 ASC, 2 ASC, 8 DESC, 5 ASC
            LIMIT %s
            """,
            (limite_consulta,),
          )
          for uf_item, cidade_item, ncm_item, descricao_item, codigo_item, produto_item, sem_item_detalhado, faturamento, imposto_complementar in cur.fetchall():
            faturamento_item = faturamento or Decimal("0.00")
            imposto_valor = imposto_complementar or Decimal("0.00")
            if not usar_impostos_complementares:
              imposto_valor = calcular_imposto_por_percentual(faturamento_item, percentual_total)
            hierarquia.append(
              construir_item_hierarquia_completa(
                uf_item,
                cidade_item,
                ncm_item,
                descricao_item,
                codigo_item,
                produto_item,
                faturamento_item,
                imposto_valor,
                normalizar_cidade=_normalizar_nome_cidade,
                sem_item_detalhado=sem_item_detalhado,
              )
            )
        nivel_resolvido = resolver_nivel_hierarquia(nivel_atual, estado, cidade, ncm)
        itens_nivel_atual: list[dict] = []
        por_estado: list[dict] = []
        por_cidade: list[dict] = []
        por_ncm: list[dict] = []
        por_produto: list[dict] = []
        total_registros_nivel = 0

        if nivel_resolvido == "estado":
          cur.execute("SELECT COUNT(DISTINCT estado) FROM tmp_sped_fiscal_hierarquia_base_filtrada")
          total_registros_nivel = (cur.fetchone() or [0])[0] or 0
          cur.execute(
            """
            SELECT
              estado,
              COALESCE(SUM(faturamento), 0) AS faturamento,
              COALESCE(SUM(imposto_valor), 0) AS imposto_valor
            FROM tmp_sped_fiscal_hierarquia_base_filtrada
            GROUP BY 1
            ORDER BY 2 DESC, 1 ASC
            LIMIT %s
            OFFSET %s
            """,
            (limite_consulta, offset_consulta),
          )
          for uf_item, faturamento, imposto_complementar in cur.fetchall():
            faturamento_item = faturamento or Decimal("0.00")
            imposto_valor = imposto_complementar or Decimal("0.00")
            if not usar_impostos_complementares:
              imposto_valor = calcular_imposto_por_percentual(faturamento_item, percentual_total)
            por_estado.append(construir_item_estado(uf_item, faturamento_item, imposto_valor))
          itens_nivel_atual = por_estado
        elif nivel_resolvido == "cidade":
          cur.execute("SELECT COUNT(DISTINCT CONCAT(cidade, '::', estado)) FROM tmp_sped_fiscal_hierarquia_base_filtrada")
          total_registros_nivel = (cur.fetchone() or [0])[0] or 0
          cur.execute(
            """
            SELECT
              cidade,
              estado,
              COALESCE(SUM(faturamento), 0) AS faturamento,
              COALESCE(SUM(imposto_valor), 0) AS imposto_valor
            FROM tmp_sped_fiscal_hierarquia_base_filtrada
            GROUP BY 1, 2
            ORDER BY 3 DESC, 1 ASC, 2 ASC
            LIMIT %s
            OFFSET %s
            """,
            (limite_consulta, offset_consulta),
          )
          for cidade_item, uf_item, faturamento, imposto_complementar in cur.fetchall():
            faturamento_item = faturamento or Decimal("0.00")
            imposto_valor = imposto_complementar or Decimal("0.00")
            if not usar_impostos_complementares:
              imposto_valor = calcular_imposto_por_percentual(faturamento_item, percentual_total)
            por_cidade.append(
              construir_item_cidade(
                cidade_item,
                uf_item,
                faturamento_item,
                imposto_valor,
                normalizar_cidade=_normalizar_nome_cidade,
              )
            )
          itens_nivel_atual = por_cidade
        elif nivel_resolvido == "ncm":
          cur.execute("SELECT COUNT(DISTINCT ncm) FROM tmp_sped_fiscal_hierarquia_base_filtrada WHERE NOT sem_item_detalhado")
          total_registros_nivel = (cur.fetchone() or [0])[0] or 0
          cur.execute(
            """
            SELECT
              ncm,
              descricao_ncm,
              COUNT(DISTINCT CONCAT(produto_codigo, '::', produto_descricao)) AS quantidade_produtos,
              COALESCE(SUM(faturamento), 0) AS faturamento,
              COALESCE(SUM(imposto_valor), 0) AS imposto_valor
            FROM tmp_sped_fiscal_hierarquia_base_filtrada
            WHERE NOT sem_item_detalhado
            GROUP BY 1, 2
            ORDER BY 4 DESC, 1 ASC
            LIMIT %s
            OFFSET %s
            """,
            (limite_consulta, offset_consulta),
          )
          for ncm_item, descricao_item, quantidade_produtos, faturamento, imposto_complementar in cur.fetchall():
            faturamento_item = faturamento or Decimal("0.00")
            imposto_valor = imposto_complementar or Decimal("0.00")
            if not usar_impostos_complementares:
              imposto_valor = calcular_imposto_por_percentual(faturamento_item, percentual_total)
            por_ncm.append(
              construir_item_ncm(
                ncm_item,
                descricao_item,
                quantidade_produtos,
                faturamento_item,
                imposto_valor,
              )
            )
          itens_nivel_atual = por_ncm
        else:
          cur.execute("SELECT COUNT(DISTINCT CONCAT(produto_codigo, '::', produto_descricao)) FROM tmp_sped_fiscal_hierarquia_base_filtrada WHERE NOT sem_item_detalhado")
          total_registros_nivel = (cur.fetchone() or [0])[0] or 0
          cur.execute(
            """
            SELECT
              produto_codigo,
              produto_descricao,
              COALESCE(SUM(faturamento), 0) AS faturamento,
              COALESCE(SUM(imposto_valor), 0) AS imposto_valor
            FROM tmp_sped_fiscal_hierarquia_base_filtrada
            WHERE NOT sem_item_detalhado
            GROUP BY 1, 2
            ORDER BY 3 DESC, 1 ASC, 2 ASC
            LIMIT %s
            OFFSET %s
            """,
            (limite_consulta, offset_consulta),
          )
          for codigo_item, produto_item, faturamento, imposto_complementar in cur.fetchall():
            faturamento_item = faturamento or Decimal("0.00")
            imposto_valor = imposto_complementar or Decimal("0.00")
            if not usar_impostos_complementares:
              imposto_valor = calcular_imposto_por_percentual(faturamento_item, percentual_total)
            por_produto.append(
              construir_item_produto(codigo_item, produto_item, faturamento_item, imposto_valor)
            )
          itens_nivel_atual = por_produto

    total_tributos_reforma = obter_total_tributos_reforma_documentos(
      self.conn_params,
      "sped",
      cnpj,
      periodo_ano,
      periodo_mes,
      "saida",
    )

    return construir_resposta_hierarquia_fiscal(
      cnpj,
      periodo_ano,
      periodo_mes,
      nivel_resolvido,
      offset_consulta,
      limite_consulta,
      total_registros_nivel,
      total_faturamento,
      total_impostos,
      total_tributos_reforma,
      percentual_total,
      resumo_row,
      hierarquia,
      itens_nivel_atual,
      por_estado,
      por_cidade,
      por_ncm,
      por_produto,
    )

  def analisar_clientes(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: Optional[int] = None,
  ) -> dict:
    cnpj = normalizar_cnpj(emitente_cnpj)
    where_clause, params = construir_filtros_clientes_sped(
      cnpj,
      periodo_ano,
      periodo_mes,
    )

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        total_vendido = self._safe_scalar_query(
          cur,
          f"""
          SELECT COALESCE(SUM(d.valor_total), 0)
          FROM public.sped_documentos_fiscais d
          WHERE {where_clause}
          """,
          tuple(params),
        )

        total_clientes = self._safe_scalar_query(
          cur,
          f"""
          SELECT COUNT(*)
          FROM (
            SELECT 1
            FROM public.sped_documentos_fiscais d
            LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
            WHERE {where_clause}
            GROUP BY COALESCE(NULLIF(TRIM(p.nome), ''), 'Cliente nÃ£o identificado')
          ) clientes
          """,
          tuple(params),
        )

        top_clientes_valor = self._safe_top_cliente_analise_query(
          cur,
          f"""
          SELECT
            cliente,
            valor_total,
            quantidade_documentos,
            ticket_medio,
            CASE
              WHEN %s = 0 THEN 0
              ELSE ROUND((valor_total * 100.0) / %s, 2)
            END AS percentual_participacao
          FROM (
            SELECT
              COALESCE(NULLIF(TRIM(p.nome), ''), 'Cliente nÃ£o identificado') AS cliente,
              COALESCE(SUM(d.valor_total), 0) AS valor_total,
              COUNT(*) AS quantidade_documentos,
              CASE
                WHEN COUNT(*) = 0 THEN 0
                ELSE COALESCE(SUM(d.valor_total), 0) / COUNT(*)
              END AS ticket_medio
            FROM public.sped_documentos_fiscais d
            LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
            WHERE {where_clause}
            GROUP BY 1
          ) base
          ORDER BY valor_total DESC, cliente ASC
          LIMIT %s
          """,
          tuple(construir_params_ranking_clientes(total_vendido, params, limite)),
        )

        top_clientes_quantidade = self._safe_top_cliente_analise_query(
          cur,
          f"""
          SELECT
            cliente,
            valor_total,
            quantidade_documentos,
            ticket_medio,
            CASE
              WHEN %s = 0 THEN 0
              ELSE ROUND((valor_total * 100.0) / %s, 2)
            END AS percentual_participacao
          FROM (
            SELECT
              COALESCE(NULLIF(TRIM(p.nome), ''), 'Cliente nÃ£o identificado') AS cliente,
              COALESCE(SUM(d.valor_total), 0) AS valor_total,
              COUNT(*) AS quantidade_documentos,
              CASE
                WHEN COUNT(*) = 0 THEN 0
                ELSE COALESCE(SUM(d.valor_total), 0) / COUNT(*)
              END AS ticket_medio
            FROM public.sped_documentos_fiscais d
            LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
            WHERE {where_clause}
            GROUP BY 1
          ) base
          ORDER BY quantidade_documentos DESC, valor_total DESC, cliente ASC
          LIMIT %s
          """,
          tuple(construir_params_ranking_clientes(total_vendido, params, limite)),
        )

        return construir_resposta_analise_clientes(
          cnpj,
          periodo_ano,
          periodo_mes,
          total_vendido,
          total_clientes,
          top_clientes_valor,
          top_clientes_quantidade,
        )

  def _safe_scalar_query(self, cur, sql: str, params: tuple[object, ...]) -> Decimal:
    try:
      cur.execute(sql, params)
      row = cur.fetchone()
      return row[0] if row else Decimal("0.00")
    except psycopg.errors.UndefinedTable:
      return Decimal("0.00")

  def _safe_top_fornecedor_query(self, cur, sql: str, params: tuple[object, ...]) -> list[dict]:
    try:
      cur.execute(sql, params)
      return [
        {
          "fornecedor": fornecedor,
          "valor_total": valor_total or Decimal("0.00"),
          "quantidade_documentos": quantidade_documentos or 0,
        }
        for fornecedor, valor_total, quantidade_documentos in cur.fetchall()
      ]
    except psycopg.errors.UndefinedTable:
      return []
    
  def _safe_top_cliente_query(self, cur, sql: str, params: tuple[object, ...]) -> list[dict]:
    try:
      cur.execute(sql, params)
      return [
        {
          "cliente": cliente,
          "valor_total": valor_total or Decimal("0.00"),
          "quantidade_documentos": quantidade_documentos or 0,
        }
        for cliente, valor_total, quantidade_documentos in cur.fetchall()
      ]
    except psycopg.errors.UndefinedTable:
      return []

  def _safe_top_produto_query(self, cur, sql: str, params: tuple[object, ...]) -> list[dict]:
    try:
      cur.execute(sql, params)
      return [
        {
          "produto": produto,
          "valor_total": valor_total or Decimal("0.00"),
          "quantidade_total": quantidade_total or Decimal("0.00"),
        }
        for produto, valor_total, quantidade_total in cur.fetchall()
      ]
    except psycopg.errors.UndefinedTable:
      return []

  def _safe_top_cliente_analise_query(self, cur, sql: str, params: tuple[object, ...]) -> list[dict]:
    try:
      cur.execute(sql, params)
      return construir_ranking_clientes(cur.fetchall())
    except psycopg.errors.UndefinedTable:
      return []
