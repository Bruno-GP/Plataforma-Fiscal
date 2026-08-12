from decimal import Decimal
from typing import Optional

from app.api.shared.analytics import obter_periodo_anterior, resumir_vendas_por_kpis
from app.models.nfe.schemas import NFeKPIConsulta
from app.models.sped.schemas import (
  DashboardVendasResponse,
  DashboardVendasResumo,
  SerieMensalVendasItem,
)
from app.services.fiscal.fiscal_analysis import (
  FiscalDimensionConfig,
  analisar_fiscal_por_dimensao,
  obter_total_impostos_complementares_documentos,
  obter_total_tributos_reforma_documentos,
  obter_regiao_por_uf,
)
from app.services.fiscal.fiscal_clients import (
  construir_filtros_clientes_sped,
  construir_resposta_analise_clientes,
)
from app.services.fiscal.fiscal_dimensions import (
  construir_resposta_fiscal_cfop,
  construir_resposta_fiscal_ncm,
)
from app.services.fiscal.fiscal_hierarchy import (
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
from app.services.fiscal.fiscal_kpis import construir_sped_kpi_consulta
from app.services.fiscal.fiscal_purchases import (
  construir_filtros_compras_sped,
  construir_resposta_analise_compras,
)
from app.services.fiscal.fiscal_sales import (
  construir_filtros_vendas_sped,
  construir_ranking_cidades_vendas,
  construir_ranking_regioes_vendas,
  construir_resposta_analise_vendas,
)
from app.services.nfe.empresa_service import normalizar_cnpj
from app.domain.nfe.normalization import normalizar_nome_produto
from app.services.sped.postgres_config import carregar_config_postgres_sped
from app.repositories.sped.sped_repository import SpedRepository

def _sped_ncm_expr(alias_produto: str = "pr") -> str:
  return f"COALESCE(NULLIF(regexp_replace(COALESCE({alias_produto}.ncm, ''), '\\D', '', 'g'), ''), '00000000')"

def _sped_produto_codigo_expr(alias_produto: str = "pr") -> str:
  return f"COALESCE(NULLIF(TRIM({alias_produto}.codigo), ''), 'SEM-CODIGO')"

SPED_CFOP_ANALYSIS_CONFIG = FiscalDimensionConfig(
  from_clause="""
    public.sped_documentos_fiscais d
    JOIN public.sped_documento_itens i ON i.documento_id = d.id
  """,
  company_filter_expr="regexp_replace(UPPER(d.empresa_cnpj), '[^0-9A-Z]', '', 'g')",
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
  company_filter_expr="regexp_replace(UPPER(d.empresa_cnpj), '[^0-9A-Z]', '', 'g')",
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
      **({"sslmode": config["sslmode"]} if config.get("sslmode") else {}),
    }
    self.repository = SpedRepository(self.conn_params)

  def listar_kpis(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: int = 100,
    offset: int = 0,
  ) -> list[NFeKPIConsulta]:
    cnpj = normalizar_cnpj(emitente_cnpj)
    rows = self.repository.listar_kpis(
      cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      limite=limite,
      offset=offset,
    )

    resultados: list[NFeKPIConsulta] = []
    for row in rows:
      ano = row[3]
      mes = row[4]
      top_clientes = self._top_clientes(None, cnpj, ano, mes)
      top_cidades = self._top_cidades(None, cnpj, ano, mes)
      top_produtos = self._top_produtos(None, cnpj, ano, mes)
      resultados.append(
        construir_sped_kpi_consulta(row, top_clientes, top_produtos, top_cidades)
      )

    return resultados

  def _validar_tabela_kpis(self, cur) -> None:
    self.repository.validar_tabela_kpis()

  def _top_clientes(self, cur, cnpj: str, ano: int, mes: int) -> list[dict]:
    return self.repository.top_clientes(cnpj, ano, mes)

  def _top_cidades(self, cur, cnpj: str, ano: int, mes: int) -> list[dict]:
    cidades = self.repository.top_cidades(cnpj, ano, mes)
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
    return self.repository.top_produtos(cnpj, ano, mes)

  def _safe_top_query(self, cur, sql: str, params: tuple[object, ...], label: str) -> list[dict]:
    return self.repository._safe_top_query(sql, params, label)
    
  def listar_clientes(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: Optional[int] = None,
    offset: int = 0,
  ) -> dict:
    cnpj = normalizar_cnpj(emitente_cnpj)
    where_clause, params = construir_filtros_clientes_sped(
      cnpj,
      periodo_ano,
      periodo_mes,
    )
    resultado = self.repository.listar_clientes(where_clause, params, limite=limite, offset=offset)

    total_vendas_decimal = Decimal(resultado["total_vendas"] or 0)
    resultados = []
    for cliente, valor_total in resultado["clientes_rows"]:
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
      "total_clientes": int(resultado["total_clientes"] or 0),
      "total_vendas": total_vendas_decimal,
      "ticket_medio": Decimal(resultado["ticket_medio"] or 0),
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
    where_clause, params = construir_filtros_compras_sped(
      cnpj,
      periodo_ano,
      periodo_mes,
    )
    resultado = self.repository.analisar_compras(where_clause, params, limite=limite)

    total_impostos_complementares = obter_total_impostos_complementares_documentos(
      self.conn_params,
      "sped",
      cnpj,
      periodo_ano,
      periodo_mes,
      "entrada",
    )
    total_tributos_reforma = obter_total_tributos_reforma_documentos(
      self.conn_params,
      "sped",
      cnpj,
      periodo_ano,
      periodo_mes,
      "entrada",
    )

    return construir_resposta_analise_compras(
      cnpj,
      periodo_ano,
      periodo_mes,
      resultado["total_comprado"],
      total_impostos_complementares,
      total_tributos_reforma,
      resultado["top_fornecedores_valor"],
      resultado["top_fornecedores_quantidade"],
      resultado["top_produtos_valor"],
      resultado["top_produtos_quantidade"],
    )
        
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
    resultado = self.repository.analisar_vendas(where_clause, params, limite=limite)

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

    top_regioes_valor = construir_ranking_regioes_vendas(
      resultado["top_regioes_rows"],
      obter_regiao_por_uf,
      limite,
    )
    top_cidades_valor = construir_ranking_cidades_vendas(
      resultado["top_cidades_rows"],
      normalizar_cidade=_normalizar_nome_cidade,
    )

    return construir_resposta_analise_vendas(
      cnpj,
      periodo_ano,
      periodo_mes,
      resultado["total_vendido"],
      total_impostos_complementares,
      total_tributos_reforma,
      resultado["top_clientes_valor"],
      resultado["top_clientes_quantidade"],
      resultado["top_produtos_valor"],
      resultado["top_produtos_quantidade"],
      resultado["top_cfops_valor"],
      top_regioes_valor,
      top_cidades_valor,
    )

  def consultar_dashboard_vendas(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: int = 5,
  ) -> DashboardVendasResponse:
    resultados_anos = self.listar_kpis(emitente_cnpj=emitente_cnpj, limite=120)
    anos_disponiveis = sorted(
      {item.periodo_ano for item in resultados_anos if item.periodo_ano},
      reverse=True,
    )
    ano_referencia = periodo_ano or (anos_disponiveis[0] if anos_disponiveis else None)

    if ano_referencia is None:
      raise ValueError("Nenhum periodo disponivel para o emitente informado.")

    resultados_ano_atual = self.listar_kpis(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=ano_referencia,
      limite=120,
    )
    resultados_ano_anterior = self.listar_kpis(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=ano_referencia - 1,
      limite=120,
    )

    if periodo_mes is not None:
      resultados_filtrados = [item for item in resultados_ano_atual if item.periodo_mes == periodo_mes]
      ano_anterior, mes_anterior = obter_periodo_anterior(ano_referencia, periodo_mes)
      resultados_anteriores = (
        [item for item in resultados_ano_atual if item.periodo_mes == mes_anterior]
        if ano_anterior == ano_referencia
        else [item for item in resultados_ano_anterior if item.periodo_mes == mes_anterior]
      )
    else:
      resultados_filtrados = resultados_ano_atual
      resultados_anteriores = resultados_ano_anterior

    serie_mensal = [
      SerieMensalVendasItem(
        periodo_ano=ano_referencia,
        periodo_mes=item.periodo_mes or 0,
        total_vendido=Decimal(str(item.kpis.total_vendas or 0)),
        quantidade_notas=int(item.kpis.quantidade_notas or 0),
        total_impostos=(
          Decimal(str(item.kpis.total_icms or 0))
          + Decimal(str(item.kpis.total_ipi or 0))
          + Decimal(str(item.kpis.total_pis or 0))
          + Decimal(str(item.kpis.total_cofins or 0))
        ),
        total_impostos_complementares=obter_total_impostos_complementares_documentos(
          self.conn_params,
          "sped",
          emitente_cnpj,
          ano_referencia,
          item.periodo_mes,
          "saida",
        ),
        total_tributos_reforma=obter_total_tributos_reforma_documentos(
          self.conn_params,
          "sped",
          emitente_cnpj,
          ano_referencia,
          item.periodo_mes,
          "saida",
        ),
      )
      for item in sorted(resultados_ano_atual, key=lambda resultado: resultado.periodo_mes or 0)
      if item.periodo_mes
    ]

    return DashboardVendasResponse(
      status="ok",
      emitente_cnpj=emitente_cnpj,
      periodo_ano=ano_referencia,
      periodo_mes=periodo_mes,
      anos_disponiveis=anos_disponiveis,
      resumo_atual=resumir_vendas_por_kpis(resultados_filtrados, DashboardVendasResumo, limite).model_copy(update={
        "total_impostos_complementares": obter_total_impostos_complementares_documentos(
          self.conn_params,
          "sped",
          emitente_cnpj,
          ano_referencia,
          periodo_mes,
          "saida",
        ),
        "total_tributos_reforma": obter_total_tributos_reforma_documentos(
          self.conn_params,
          "sped",
          emitente_cnpj,
          ano_referencia,
          periodo_mes,
          "saida",
        ),
      }),
      resumo_anterior=resumir_vendas_por_kpis(resultados_anteriores, DashboardVendasResumo, limite).model_copy(update={
        "total_impostos_complementares": obter_total_impostos_complementares_documentos(
          self.conn_params,
          "sped",
          emitente_cnpj,
          *obter_periodo_anterior(ano_referencia, periodo_mes),
          "saida",
        ),
        "total_tributos_reforma": obter_total_tributos_reforma_documentos(
          self.conn_params,
          "sped",
          emitente_cnpj,
          *obter_periodo_anterior(ano_referencia, periodo_mes),
          "saida",
        ),
      }),
      serie_mensal=serie_mensal,
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

    return construir_resposta_fiscal_cfop(
      cnpj,
      periodo_ano,
      periodo_mes,
      resultado,
      total_impostos_complementares,
      total_tributos_reforma,
    )

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

    return construir_resposta_fiscal_ncm(
      cnpj,
      periodo_ano,
      periodo_mes,
      resultado,
      total_impostos_complementares,
      total_tributos_reforma,
    )

  def _montar_dados_hierarquia_fiscal(
    self,
    resultado: dict,
    nivel_resolvido: str,
    usar_impostos_complementares: bool,
    percentual_total: Decimal,
    modo_legado_hierarquia_completa: bool,
  ) -> tuple[Decimal, Decimal, Decimal, Optional[tuple], list[dict], int, list[dict], list[dict], list[dict], list[dict], list[dict]]:
    resumo_row = resultado["resumo_row"]
    total_faturamento = resumo_row[0] if resumo_row else Decimal("0.00")
    total_impostos_complementares = resumo_row[1] if resumo_row else Decimal("0.00")
    total_impostos = (
      total_impostos_complementares
      if usar_impostos_complementares
      else calcular_imposto_por_percentual(total_faturamento, percentual_total)
    )

    hierarquia = []
    if modo_legado_hierarquia_completa:
      for uf_item, cidade_item, ncm_item, descricao_item, codigo_item, produto_item, sem_item_detalhado, faturamento, imposto_complementar in resultado["hierarquia_rows"]:
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
            normalizar_nome_produto(produto_item),
            faturamento_item,
            imposto_valor,
            normalizar_cidade=_normalizar_nome_cidade,
            sem_item_detalhado=sem_item_detalhado,
          )
        )

    itens_nivel_atual: list[dict] = []
    por_estado: list[dict] = []
    por_cidade: list[dict] = []
    por_ncm: list[dict] = []
    por_produto: list[dict] = []
    total_registros_nivel = resultado["total_registros_nivel"]

    if nivel_resolvido == "estado":
      for uf_item, faturamento, imposto_complementar in resultado["itens_nivel_rows"]:
        faturamento_item = faturamento or Decimal("0.00")
        imposto_valor = imposto_complementar or Decimal("0.00")
        if not usar_impostos_complementares:
          imposto_valor = calcular_imposto_por_percentual(faturamento_item, percentual_total)
        por_estado.append(construir_item_estado(uf_item, faturamento_item, imposto_valor))
      itens_nivel_atual = por_estado
    elif nivel_resolvido == "cidade":
      for cidade_item, uf_item, faturamento, imposto_complementar in resultado["itens_nivel_rows"]:
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
      for ncm_item, descricao_item, quantidade_produtos, faturamento, imposto_complementar in resultado["itens_nivel_rows"]:
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
      for codigo_item, produto_item, faturamento, imposto_complementar in resultado["itens_nivel_rows"]:
        faturamento_item = faturamento or Decimal("0.00")
        imposto_valor = imposto_complementar or Decimal("0.00")
        if not usar_impostos_complementares:
          imposto_valor = calcular_imposto_por_percentual(faturamento_item, percentual_total)
        por_produto.append(
          construir_item_produto(
            codigo_item,
            normalizar_nome_produto(produto_item),
            faturamento_item,
            imposto_valor,
          )
        )
      itens_nivel_atual = por_produto

    return (
      total_faturamento,
      total_impostos_complementares,
      total_impostos,
      resumo_row,
      hierarquia,
      total_registros_nivel,
      itens_nivel_atual,
      por_estado,
      por_cidade,
      por_ncm,
      por_produto,
    )

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
    nivel_resolvido = resolver_nivel_hierarquia(nivel_atual, estado, cidade, ncm)
    resultado = self.repository.analisar_fiscal_hierarquia(
      where_clause_documentos=where_clause_documentos,
      where_clause_kpis=where_clause_kpis,
      where_clause_base=where_clause_base,
      params_kpis=params_kpis,
      params_cte=params_cte,
      params_base=params_base,
      nivel_resolvido=nivel_resolvido,
      limite_consulta=limite_consulta,
      offset_consulta=offset_consulta,
      modo_legado_hierarquia_completa=modo_legado_hierarquia_completa,
    )

    total_impostos_periodo = resultado["total_impostos_periodo"]
    total_faturamento_periodo = resultado["total_faturamento_periodo"]
    percentual_total = calcular_percentual_imposto(total_impostos_periodo, total_faturamento_periodo)
    resumo_row = resultado["resumo_row"]
    total_impostos_complementares = resumo_row[1] if resumo_row else Decimal("0.00")
    usar_impostos_complementares = total_impostos_complementares > 0
    (
      total_faturamento,
      total_impostos_complementares,
      total_impostos,
      resumo_row,
      hierarquia,
      total_registros_nivel,
      itens_nivel_atual,
      por_estado,
      por_cidade,
      por_ncm,
      por_produto,
    ) = self._montar_dados_hierarquia_fiscal(
      resultado,
      nivel_resolvido,
      usar_impostos_complementares,
      percentual_total,
      modo_legado_hierarquia_completa,
    )

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
    resultado = self.repository.analisar_clientes(where_clause, params, limite=limite)
    return construir_resposta_analise_clientes(
      cnpj,
      periodo_ano,
      periodo_mes,
      resultado["total_vendido"],
      resultado["total_clientes"],
      resultado["top_clientes_valor"],
      resultado["top_clientes_quantidade"],
    )


  def _safe_scalar_query(self, cur, sql: str, params: tuple[object, ...]) -> Decimal:
    return self.repository._safe_scalar_query(sql, params)

  def _safe_top_fornecedor_query(self, cur, sql: str, params: tuple[object, ...]) -> list[dict]:
    return self.repository._safe_top_fornecedor_query(sql, params)
    
  def _safe_top_cliente_query(self, cur, sql: str, params: tuple[object, ...]) -> list[dict]:
    return self.repository._safe_top_cliente_query(sql, params)

  def _safe_top_produto_query(self, cur, sql: str, params: tuple[object, ...]) -> list[dict]:
    return self.repository._safe_top_produto_query(sql, params)

  def _safe_top_cliente_analise_query(self, cur, sql: str, params: tuple[object, ...]) -> list[dict]:
    return self.repository._safe_top_cliente_analise_query(sql, params)
