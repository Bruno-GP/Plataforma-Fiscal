import logging
from typing import List, Optional
from decimal import Decimal
import psycopg
from fastapi import HTTPException, status

from app.core.cache import ttl_cache
from app.models.nfe.schemas import (
  DashboardVendasResponse,
  KPIsComparativo,
  NFeKPI,
  NFeKPIConsulta,
)
from app.repositories.nfe.consulta_repository import NFeConsultaRepository
from app.services.nfe.empresa_service import normalizar_cnpj
from app.services.fiscal_analysis import (
  FiscalDimensionConfig,
  analisar_fiscal_por_dimensao,
  obter_total_impostos_complementares_documentos,
  obter_totais_tributos_documentos_por_periodo,
  obter_total_tributos_reforma_documentos,
  obter_regiao_por_uf,
)
from app.services.fiscal_clients import (
  construir_filtros_clientes_nfe,
  construir_ranking_clientes,
  construir_resposta_analise_clientes,
)
from app.services.fiscal_dimensions import (
  construir_resposta_fiscal_cfop,
  construir_resposta_fiscal_ncm,
)
from app.services.fiscal_hierarchy import (
  calcular_percentual_imposto,
  construir_filtros_hierarquia_nfe,
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
from app.services.fiscal_kpis import (
  construir_comparativo_kpis,
  construir_dashboard_vendas_response,
  construir_nfe_kpi_consulta_de_row,
  construir_nfe_kpi_de_row,
  construir_periodos_dashboard,
  construir_resumo_dashboard,
  construir_serie_mensal_dashboard,
  obter_anos_disponiveis_kpis,
  resolver_ano_referencia_dashboard,
  resolver_periodo_anterior_kpi,
  selecionar_resultados_dashboard,
)
from app.services.fiscal_purchases import (
  construir_filtros_compras_nfe,
  construir_params_com_limite_compras,
  construir_ranking_fornecedores_compras,
  construir_ranking_produtos_compras,
  construir_resposta_analise_compras,
)
from app.services.fiscal_sales import (
  CFOPS_FATURAMENTO_VENDA,
  construir_params_com_limite,
  construir_ranking_cfops_vendas,
  construir_ranking_cidades_vendas,
  construir_ranking_clientes_vendas,
  construir_ranking_produtos_vendas,
  construir_ranking_regioes_vendas,
  construir_resposta_analise_vendas,
  obter_cfops_faturamento_venda,
)
from app.services.nfe.postres_config import carregar_config_postgres

logger = logging.getLogger("NFeConsultaService")

NFE_CFOP_ANALYSIS_CONFIG = FiscalDimensionConfig(
  from_clause="""
    public.notas AS n
    JOIN public.notas_itens AS i
      ON i.nota_id = n.id
  """,
  company_filter_expr="regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g')",
  date_expr="n.data_emissao",
  document_id_expr="n.id",
  amount_expr="i.valor_total",
  dimension_code_count_expr="regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g')",
  dimension_code_display_expr="regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g')",
  dimension_description_expr="c.descricao",
  category_description_expr="c.descricao",
  category_fallback_description_expr="n.natureza_operacao",
  sale_condition_expr="LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('5','6','7')",
  reference_join_clause="""
    LEFT JOIN public.notas_cfops AS c
      ON regexp_replace(COALESCE(c.codigo, ''), '\\D', '', 'g')
         = regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g')
  """,
  unknown_description="CFOP sem descrião",
)

NFE_NCM_ANALYSIS_CONFIG = FiscalDimensionConfig(
  from_clause="""
    public.notas AS n
    JOIN public.notas_itens AS i
      ON i.nota_id = n.id
  """,
  company_filter_expr="regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g')",
  date_expr="n.data_emissao",
  document_id_expr="n.id",
  amount_expr="i.valor_total",
  dimension_code_count_expr="regexp_replace(COALESCE(i.ncm, ''), '\\D', '', 'g')",
  dimension_code_display_expr="regexp_replace(COALESCE(i.ncm, ''), '\\D', '', 'g')",
  dimension_description_expr="nc.descricao",
  category_description_expr="n.natureza_operacao",
  sale_condition_expr="LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('5','6','7')",
  reference_join_clause="""
    LEFT JOIN public.ncm_catalogo nc
      ON regexp_replace(COALESCE(nc.codigo, ''), '\\D', '', 'g')
         = regexp_replace(COALESCE(i.ncm, ''), '\\D', '', 'g')
  """,
  unknown_code="00000000",
  unknown_description="NCM sem descrição",
)

class NFeConsultaService:
  def __init__(self):
    logger.debug("Inicializando NFeConsultaService")

    config = carregar_config_postgres()
    #logger.debug(f"Config PostgreSQL carregada: {config}")

    self.conn_params = {
      "host": config["host"],
      "port": config["port"],
      "dbname": config["database"],
      "user": config["user"],
      "password": config["password"],
      "connect_timeout": 5,
    }
    self.consulta_repository = NFeConsultaRepository(self.conn_params)

  def _consulta_repository(self) -> NFeConsultaRepository:
    repository = getattr(self, "consulta_repository", None)
    if repository is None:
      repository = NFeConsultaRepository(self.conn_params)
      self.consulta_repository = repository

    return repository
    
  def _normalizar_cnpj_filtro(
    self,
    emitente_cnpj: Optional[str],
    permitir_zerado: bool = False,
  ) -> Optional[str]:
    if not emitente_cnpj:
      return None

    cnpj = normalizar_cnpj(emitente_cnpj)
    if not cnpj:
      return None

    if not permitir_zerado and set(cnpj) == {"0"}:
      return None

    return cnpj  

  def _obter_cnpj_filtrado_obrigatorio(
    self,
    emitente_cnpj: Optional[str],
    mensagem_erro: str = "Informe um emitente_cnpj vÃ¡lido.",
  ) -> str:
    cnpj_filtrado = self._normalizar_cnpj_filtro(
      emitente_cnpj,
      permitir_zerado=False,
    )
    if not cnpj_filtrado:
      raise ValueError(mensagem_erro)

    return cnpj_filtrado

  def obter_cnpj_por_email(
    self,
    email: Optional[str],
  ) -> Optional[str]:
    if not email:
      return None

    email_normalizado = email.strip().lower()
    if not email_normalizado:
      return None

    cnpj_row = self._consulta_repository().obter_cnpj_por_email(email_normalizado)
    if not cnpj_row:
      return None

    cnpj = normalizar_cnpj(cnpj_row)
    if not cnpj or set(cnpj) == {"0"}:
      return None

    return cnpj

  def resolver_emitente_cnpj(
    self,
    emitente_cnpj: Optional[str],
    email: Optional[str],
  ) -> Optional[str]:
    cnpj_filtrado = self._normalizar_cnpj_filtro(
      emitente_cnpj,
      permitir_zerado=False,
    )
    if cnpj_filtrado:
      return cnpj_filtrado

    return self.obter_cnpj_por_email(email)

  def _montar_filtros_vendas_itens(
    self,
    emitente_cnpj: Optional[str],
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
  ) -> tuple[str, list[object]]:
    cnpj_filtrado = self._normalizar_cnpj_filtro(
      emitente_cnpj,
      permitir_zerado=False,
    )
    if not cnpj_filtrado:
      raise ValueError("Informe um emitente_cnpj válido.")

    filtros_vendas_docs = [
      "regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g') = %s",
      "regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g') = ANY(%s)",
    ]
    parametros: list[object] = [cnpj_filtrado, obter_cfops_faturamento_venda()]

    if periodo_ano:
      filtros_vendas_docs.append("EXTRACT(YEAR FROM n.data_emissao) = %s")
      parametros.append(periodo_ano)

    if periodo_mes:
      filtros_vendas_docs.append("EXTRACT(MONTH FROM n.data_emissao) = %s")
      parametros.append(periodo_mes)

    return " AND ".join(filtros_vendas_docs), parametros

  def _montar_filtros_kpis(
    self,
    emitente_cnpj: Optional[str] = None,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
  ) -> tuple[str, list[object]]:
    filtros: list[str] = []
    parametros: list[object] = []

    cnpj_filtrado = self._normalizar_cnpj_filtro(
      emitente_cnpj,
      permitir_zerado=False,
    )

    if cnpj_filtrado:
      filtros.append("regexp_replace(k.emitente_cnpj, '\\\\D', '', 'g') = %s")
      parametros.append(cnpj_filtrado)

    if periodo_ano:
      filtros.append("k.periodo_ano = %s")
      parametros.append(periodo_ano)

    if periodo_mes:
      filtros.append("k.periodo_mes = %s")
      parametros.append(periodo_mes)

    where_clause = " AND ".join(filtros)
    return (f"WHERE {where_clause}" if where_clause else ""), parametros

  def _obter_totais_tributos_analise(
    self,
    cnpj_filtrado: str,
    periodo_ano: Optional[int],
    periodo_mes: Optional[int],
    tipo_operacao: str,
  ) -> tuple[Decimal, Decimal]:
    total_impostos_complementares = obter_total_impostos_complementares_documentos(
      self.conn_params,
      "nfe",
      cnpj_filtrado,
      periodo_ano,
      periodo_mes,
      tipo_operacao,
    )
    total_tributos_reforma = obter_total_tributos_reforma_documentos(
      self.conn_params,
      "nfe",
      cnpj_filtrado,
      periodo_ano,
      periodo_mes,
      tipo_operacao,
    )

    return total_impostos_complementares, total_tributos_reforma

  def _construir_ranking_regioes_vendas(
    self,
    rows,
    limite: Optional[int],
  ) -> list[dict]:
    return construir_ranking_regioes_vendas(
      rows,
      obter_regiao_por_uf,
      limite,
    )

  def obter_total_vendido_bruto(
    self,
    emitente_cnpj: Optional[str],
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
  ) -> Decimal:
    where_clause, parametros = self._montar_filtros_vendas_itens(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
    )

    return self._consulta_repository().obter_total_vendas_itens(where_clause, parametros)

  def listar_totais_vendas_mensais_bruto(
    self,
    emitente_cnpj: Optional[str],
    periodo_ano: int,
  ) -> dict[int, Decimal]:
    where_clause, parametros = self._montar_filtros_vendas_itens(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=periodo_ano,
    )

    rows = self._consulta_repository().listar_totais_vendas_mensais(
      where_clause,
      parametros,
    )

    return {
      int(periodo_mes): valor_total or Decimal("0.00")
      for periodo_mes, valor_total in rows
    }

  def listar_totais_vendas_brutos_por_periodo(
    self,
    emitente_cnpj: Optional[str],
    periodos: set[tuple[int, int | None]],
  ) -> dict[tuple[int, int | None], Decimal]:
    cnpj_filtrado = self._normalizar_cnpj_filtro(
      emitente_cnpj,
      permitir_zerado=False,
    )
    if not cnpj_filtrado:
      raise ValueError("Informe um emitente_cnpj vÃ¡lido.")

    if not periodos:
      return {}

    anos = sorted({ano for ano, _mes in periodos})
    totais = {periodo: Decimal("0.00") for periodo in periodos}

    rows = self._consulta_repository().listar_totais_vendas_por_periodo(
      cnpj_emitente=cnpj_filtrado,
      cfops_faturamento=obter_cfops_faturamento_venda(),
      anos=anos,
    )

    for ano, mes, valor_total in rows:
      chave_mensal = (int(ano), int(mes))
      if chave_mensal in totais:
        totais[chave_mensal] += valor_total or Decimal("0.00")

      chave_anual = (int(ano), None)
      if chave_anual in totais:
        totais[chave_anual] += valor_total or Decimal("0.00")

    return totais

  @ttl_cache(ttl_seconds=15, maxsize=128)
  def consultar_dashboard_vendas(
    self,
    emitente_cnpj: str,
    periodo_ano: int | None = None,
    periodo_mes: int | None = None,
    limite: int = 5,
  ) -> DashboardVendasResponse:
    resultados_anos = self.listar_kpis(emitente_cnpj=emitente_cnpj, limite=120)
    anos_disponiveis = obter_anos_disponiveis_kpis(resultados_anos)
    ano_referencia = resolver_ano_referencia_dashboard(periodo_ano, anos_disponiveis)

    if ano_referencia is None:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Nenhum período disponível para o emitente informado.",
      )

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
    resultados_filtrados, resultados_anteriores, ano_anterior, mes_anterior = (
      selecionar_resultados_dashboard(
        resultados_ano_atual,
        resultados_ano_anterior,
        ano_referencia,
        periodo_mes,
      )
    )

    periodos_tributos = construir_periodos_dashboard(
      ano_referencia,
      periodo_mes,
      ano_anterior,
      mes_anterior,
      resultados_ano_atual,
    )
    totais_tributos = obter_totais_tributos_documentos_por_periodo(
      self.conn_params,
      "nfe",
      emitente_cnpj,
      sorted(periodos_tributos, key=lambda periodo: (periodo[0], periodo[1] or 0)),
      "saida",
    )
    totais_vendidos: dict[tuple[int, int | None], Decimal] = {}

    resumo_atual = construir_resumo_dashboard(
      resultados_filtrados,
      (ano_referencia, periodo_mes),
      totais_vendidos,
      totais_tributos,
      limite,
    )
    resumo_anterior = construir_resumo_dashboard(
      resultados_anteriores,
      (ano_anterior, mes_anterior),
      totais_vendidos,
      totais_tributos,
      limite,
    )

    serie_mensal = construir_serie_mensal_dashboard(
      ano_referencia,
      resultados_ano_atual,
      totais_vendidos,
      totais_tributos,
    )

    return construir_dashboard_vendas_response(
      emitente_cnpj=emitente_cnpj,
      ano_referencia=ano_referencia,
      periodo_mes=periodo_mes,
      anos_disponiveis=anos_disponiveis,
      resumo_atual=resumo_atual,
      resumo_anterior=resumo_anterior,
      serie_mensal=serie_mensal,
    )
    
  def _filtro_vendas(self) -> str:
    return self._consulta_repository().filtro_vendas_kpis()

  def obter_ultimo_periodo(
    self,
    emitente_cnpj: Optional[str] = None,
  ) -> tuple[int, int]:
    where_clause, parametros = self._montar_filtros_kpis(emitente_cnpj=emitente_cnpj)
    row = self._consulta_repository().obter_ultimo_periodo(where_clause, parametros)

    if not row:
      raise ValueError("Nenhum processamento encontrado para o emitente.")

    return row

  def obter_periodos_disponiveis(
    self,
    emitente_cnpj: Optional[str] = None,
    limite: int = 2,
  ) -> List[tuple[int, int]]:
    where_clause, parametros = self._montar_filtros_kpis(emitente_cnpj=emitente_cnpj)
    parametros.append(limite)
    rows = self._consulta_repository().listar_periodos_disponiveis(
      where_clause,
      parametros,
    )

    return [(row[0], row[1]) for row in rows]

  def _buscar_kpi_periodo(
    self,
    periodo_ano: int,
    periodo_mes: int,
    emitente_cnpj: Optional[str] = None,
  ) -> Optional[NFeKPI]:
    cnpj_filtrado = self._normalizar_cnpj_filtro(
      emitente_cnpj,
      permitir_zerado=False,
    )

    where_clause, parametros = self._montar_filtros_kpis(
      emitente_cnpj=cnpj_filtrado,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
    )
    row = self._consulta_repository().buscar_kpi_periodo(where_clause, parametros)

    if not row:
      return None

    return construir_nfe_kpi_de_row(row)

  def _normalizar_top_cidades(
    self,
    top_cidades: list[dict] | None,
  ) -> list[dict]:
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

  @ttl_cache(ttl_seconds=15, maxsize=256)
  def listar_kpis(
    self,
    emitente_cnpj: Optional[str] = None,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: int = 100,
    offset: int = 0,
  ) -> List[NFeKPIConsulta]:

    where_clause, parametros = self._montar_filtros_kpis(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
    )

    parametros.extend([limite, offset])

    try:
      logger.debug("Consultando KPIs")
      kpis_rows = self._consulta_repository().listar_kpis(where_clause, parametros)

      if not kpis_rows:
        return []

      resultados = []
      for row in kpis_rows:
        resultados.append(construir_nfe_kpi_consulta_de_row(row))

      return resultados
    
    except Exception:
      logger.exception("Erro ao consultar KPIs NFe")
      raise
    
  def analisar_compras(
    self,
    emitente_cnpj: Optional[str],
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: int = 5,
  ) -> dict:
    cnpj_filtrado = self._normalizar_cnpj_filtro(
      emitente_cnpj,
      permitir_zerado=False,
    )
    if not cnpj_filtrado:
      raise ValueError("Informe um emitente_cnpj válido.")

    where_clause, parametros = construir_filtros_compras_nfe(
      cnpj_filtrado,
      periodo_ano,
      periodo_mes,
    )

    repository = self._consulta_repository()
    parametros_com_limite = construir_params_com_limite_compras(parametros, limite)
    total_comprado = repository.obter_total_itens(
      where_clause,
      parametros,
      "total_comprado",
    )
    top_fornecedores_valor = construir_ranking_fornecedores_compras(
      repository.listar_fornecedores_compras_por_valor(
        where_clause,
        parametros_com_limite,
      )
    )
    top_fornecedores_quantidade = construir_ranking_fornecedores_compras(
      repository.listar_fornecedores_compras_por_quantidade(
        where_clause,
        parametros_com_limite,
      )
    )
    top_produtos_valor = construir_ranking_produtos_compras(
      repository.listar_produtos_compras_por_valor(
        where_clause,
        parametros_com_limite,
      )
    )
    top_produtos_quantidade = construir_ranking_produtos_compras(
      repository.listar_produtos_compras_por_quantidade(
        where_clause,
        parametros_com_limite,
      )
    )
    total_impostos_complementares, total_tributos_reforma = self._obter_totais_tributos_analise(
      cnpj_filtrado,
      periodo_ano,
      periodo_mes,
      "entrada",
    )

    return construir_resposta_analise_compras(
      cnpj_filtrado,
      periodo_ano,
      periodo_mes,
      total_comprado,
      total_impostos_complementares,
      total_tributos_reforma,
      top_fornecedores_valor,
      top_fornecedores_quantidade,
      top_produtos_valor,
      top_produtos_quantidade,
    )
    
  def analisar_vendas(
    self,
    emitente_cnpj: Optional[str],
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: Optional[int] = None,
  ) -> dict:
    cnpj_filtrado = self._normalizar_cnpj_filtro(
      emitente_cnpj,
      permitir_zerado=False,
    )
    if not cnpj_filtrado:
      raise ValueError("Informe um emitente_cnpj válido.")

    where_clause, parametros = self._montar_filtros_vendas_itens(
      emitente_cnpj=cnpj_filtrado,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
    )

    repository = self._consulta_repository()
    parametros_com_limite = construir_params_com_limite(parametros, limite)
    total_vendido = repository.obter_total_itens(
      where_clause,
      parametros,
      "total_vendido",
    )
    top_clientes_valor = construir_ranking_clientes_vendas(
      repository.listar_clientes_vendas_por_valor(
        where_clause,
        parametros_com_limite,
      )
    )
    top_clientes_quantidade = construir_ranking_clientes_vendas(
      repository.listar_clientes_vendas_por_quantidade(
        where_clause,
        parametros_com_limite,
      )
    )
    top_produtos_valor = construir_ranking_produtos_vendas(
      repository.listar_produtos_vendas_por_valor(
        where_clause,
        parametros_com_limite,
      )
    )
    top_produtos_quantidade = construir_ranking_produtos_vendas(
      repository.listar_produtos_vendas_por_quantidade(
        where_clause,
        parametros_com_limite,
      )
    )
    top_cfops_valor = construir_ranking_cfops_vendas(
      repository.listar_cfops_vendas(
        where_clause,
        parametros_com_limite,
      ),
      total_vendido,
    )
    top_cidades_valor = construir_ranking_cidades_vendas(
      repository.listar_cidades_vendas(
        where_clause,
        parametros_com_limite,
      )
    )
    top_regioes_valor = self._construir_ranking_regioes_vendas(
      repository.listar_regioes_vendas(
        where_clause,
        parametros,
      ),
      limite,
    )
    total_impostos_complementares, total_tributos_reforma = self._obter_totais_tributos_analise(
      cnpj_filtrado,
      periodo_ano,
      periodo_mes,
      "saida",
    )

    return construir_resposta_analise_vendas(
      cnpj_filtrado,
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

  @ttl_cache(ttl_seconds=15, maxsize=128)
  def analisar_fiscal_cfop(
    self,
    emitente_cnpj: Optional[str],
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: Optional[int] = None,
  ) -> dict:
    cnpj_filtrado = self._normalizar_cnpj_filtro(
      emitente_cnpj,
      permitir_zerado=False,
    )
    if not cnpj_filtrado:
      raise ValueError("Informe um emitente_cnpj válido.")

    resultado = analisar_fiscal_por_dimensao(
      conn_params=self.conn_params,
      config=NFE_CFOP_ANALYSIS_CONFIG,
      emitente_cnpj=cnpj_filtrado,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      limite=limite,
    )
    total_impostos_complementares = obter_total_impostos_complementares_documentos(
      conn_params=self.conn_params,
      origem_documento="nfe",
      emitente_cnpj=cnpj_filtrado,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
    )
    total_tributos_reforma = obter_total_tributos_reforma_documentos(
      conn_params=self.conn_params,
      origem_documento="nfe",
      emitente_cnpj=cnpj_filtrado,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
    )

    return construir_resposta_fiscal_cfop(
      cnpj_filtrado,
      periodo_ano,
      periodo_mes,
      resultado,
      total_impostos_complementares,
      total_tributos_reforma,
    )

  @ttl_cache(ttl_seconds=15, maxsize=128)
  def analisar_fiscal_ncm(
    self,
    emitente_cnpj: Optional[str],
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: Optional[int] = None,
  ) -> dict:
    cnpj_filtrado = self._normalizar_cnpj_filtro(
      emitente_cnpj,
      permitir_zerado=False,
    )
    if not cnpj_filtrado:
      raise ValueError("Informe um emitente_cnpj válido.")

    resultado = analisar_fiscal_por_dimensao(
      conn_params=self.conn_params,
      config=NFE_NCM_ANALYSIS_CONFIG,
      emitente_cnpj=cnpj_filtrado,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      limite=limite,
    )
    total_impostos_complementares = obter_total_impostos_complementares_documentos(
      conn_params=self.conn_params,
      origem_documento="nfe",
      emitente_cnpj=cnpj_filtrado,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
    )
    total_tributos_reforma = obter_total_tributos_reforma_documentos(
      conn_params=self.conn_params,
      origem_documento="nfe",
      emitente_cnpj=cnpj_filtrado,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
    )

    return construir_resposta_fiscal_ncm(
      cnpj_filtrado,
      periodo_ano,
      periodo_mes,
      resultado,
      total_impostos_complementares,
      total_tributos_reforma,
    )

  @ttl_cache(ttl_seconds=15, maxsize=128)
  def analisar_fiscal_hierarquia(
    self,
    emitente_cnpj: Optional[str],
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
    cnpj_filtrado = self._normalizar_cnpj_filtro(
      emitente_cnpj,
      permitir_zerado=False,
    )
    if not cnpj_filtrado:
      raise ValueError("Informe um emitente_cnpj valido.")

    where_clause, parametros = construir_filtros_hierarquia_nfe(
      cnpj_filtrado,
      periodo_ano,
      periodo_mes,
      estado,
      cidade,
      ncm,
      produto_codigo,
    )
    limite_consulta, offset_consulta = normalizar_paginacao_hierarquia(limite, offset)
    modo_legado_hierarquia_completa = deve_montar_hierarquia_legado(
      nivel_atual,
      estado,
      cidade,
      ncm,
      produto_codigo,
      offset_consulta,
    )

    repository = self._consulta_repository()

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        repository.criar_tmp_fiscal_hierarquia_base(cur, where_clause, parametros)
        resumo_row = repository.obter_resumo_fiscal_hierarquia(cur)

        total_faturamento = resumo_row[0] if resumo_row else Decimal("0.00")
        total_impostos = resumo_row[1] if resumo_row else Decimal("0.00")
        percentual_total = calcular_percentual_imposto(total_impostos, total_faturamento)
        hierarquia: list[dict] = []
        if modo_legado_hierarquia_completa:
          rows_hierarquia = repository.listar_hierarquia_fiscal_completa(cur, limite_consulta)
          hierarquia = [
            construir_item_hierarquia_completa(
              uf_item,
              cidade_item,
              ncm_item,
              descricao_item,
              codigo_item,
              produto_item,
              faturamento,
              imposto_valor,
            )
            for uf_item, cidade_item, ncm_item, descricao_item, codigo_item, produto_item, faturamento, imposto_valor in rows_hierarquia
          ]
        nivel_resolvido = resolver_nivel_hierarquia(nivel_atual, estado, cidade, ncm)
        itens_nivel_atual: list[dict] = []
        por_estado: list[dict] = []
        por_cidade: list[dict] = []
        por_ncm: list[dict] = []
        por_produto: list[dict] = []
        total_registros_nivel = 0

        if nivel_resolvido == "estado":
          total_registros_nivel = repository.contar_estados_fiscal_hierarquia(cur)
          rows_estado = repository.listar_estados_fiscal_hierarquia(cur, limite_consulta, offset_consulta)
          por_estado = [
            construir_item_estado(uf_item, faturamento, imposto_valor)
            for uf_item, faturamento, imposto_valor in rows_estado
          ]
          itens_nivel_atual = por_estado
        elif nivel_resolvido == "cidade":
          total_registros_nivel = repository.contar_cidades_fiscal_hierarquia(cur)
          rows_cidade = repository.listar_cidades_fiscal_hierarquia(cur, limite_consulta, offset_consulta)
          por_cidade = [
            construir_item_cidade(cidade_item, uf_item, faturamento, imposto_valor)
            for cidade_item, uf_item, faturamento, imposto_valor in rows_cidade
          ]
          itens_nivel_atual = por_cidade
        elif nivel_resolvido == "ncm":
          total_registros_nivel = repository.contar_ncms_fiscal_hierarquia(cur)
          rows_ncm = repository.listar_ncms_fiscal_hierarquia(cur, limite_consulta, offset_consulta)
          por_ncm = [
            construir_item_ncm(
              ncm_item,
              descricao_item,
              quantidade_produtos,
              faturamento,
              imposto_valor,
            )
            for ncm_item, descricao_item, quantidade_produtos, faturamento, imposto_valor in rows_ncm
          ]
          itens_nivel_atual = por_ncm
        else:
          total_registros_nivel = repository.contar_produtos_fiscal_hierarquia(cur)
          rows_produto = repository.listar_produtos_fiscal_hierarquia(cur, limite_consulta, offset_consulta)
          por_produto = [
            construir_item_produto(codigo_item, produto_item, faturamento, imposto_valor)
            for codigo_item, produto_item, faturamento, imposto_valor in rows_produto
          ]
          itens_nivel_atual = por_produto

    total_tributos_reforma = obter_total_tributos_reforma_documentos(
      self.conn_params,
      "nfe",
      cnpj_filtrado,
      periodo_ano,
      periodo_mes,
      "saida",
    )

    return construir_resposta_hierarquia_fiscal(
      cnpj_filtrado,
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
    emitente_cnpj: Optional[str],
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: Optional[int] = None,
  ) -> dict:
    cnpj_filtrado = self._normalizar_cnpj_filtro(
      emitente_cnpj,
      permitir_zerado=False,
    )
    if not cnpj_filtrado:
      raise ValueError("Informe um emitente_cnpj válido.")

    where_clause, parametros = construir_filtros_clientes_nfe(
      cnpj_filtrado,
      periodo_ano,
      periodo_mes,
    )

    total_vendido, total_clientes = self._consulta_repository().obter_totais_clientes(
      where_clause,
      parametros,
    )
    top_clientes_valor = construir_ranking_clientes(
      self._consulta_repository().listar_clientes_por_valor(
        where_clause,
        parametros,
        total_vendido,
        limite,
      )
    )
    top_clientes_quantidade = construir_ranking_clientes(
      self._consulta_repository().listar_clientes_por_quantidade(
        where_clause,
        parametros,
        total_vendido,
        limite,
      )
    )

    return construir_resposta_analise_clientes(
      cnpj_filtrado,
      periodo_ano,
      periodo_mes,
      total_vendido,
      total_clientes,
      top_clientes_valor,
      top_clientes_quantidade,
    )
      
  def comparar_kpis_mensal(
    self,
    periodo_ano: int,
    periodo_mes: int,
    emitente_cnpj: Optional[str] = None,
    periodo_anterior_ano: Optional[int] = None,
    periodo_anterior_mes: Optional[int] = None,
  ) -> Optional[KPIsComparativo]:
    periodo_anterior_ano, periodo_anterior_mes = resolver_periodo_anterior_kpi(
      periodo_ano,
      periodo_mes,
      periodo_anterior_ano,
      periodo_anterior_mes,
    )

    kpi_atual = self._buscar_kpi_periodo(
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      emitente_cnpj=emitente_cnpj,
    )
    kpi_anterior = self._buscar_kpi_periodo(
      periodo_ano=periodo_anterior_ano,
      periodo_mes=periodo_anterior_mes,
      emitente_cnpj=emitente_cnpj,
    )

    if not kpi_atual:
      return None
    
    return construir_comparativo_kpis(kpi_atual, kpi_anterior)
