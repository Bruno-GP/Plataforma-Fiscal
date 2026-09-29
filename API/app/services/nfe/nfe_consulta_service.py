import logging
from time import perf_counter
from typing import List, Optional
from decimal import Decimal
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
from app.services.fiscal.fiscal_analysis import (
  analisar_fiscal_por_dimensao,
  obter_total_impostos_complementares_documentos,
  obter_totais_tributos_documentos_por_periodo,
  obter_total_tributos_reforma_documentos,
  obter_regiao_por_uf,
)
from app.services.fiscal.fiscal_clients import (
  construir_filtros_clientes_nfe,
  construir_ranking_clientes,
  construir_resposta_analise_clientes,
)
from app.services.fiscal.fiscal_dimensions import (
  construir_resposta_fiscal_cfop,
  construir_resposta_fiscal_ncm,
)
from app.services.fiscal.fiscal_hierarchy import (
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
from app.services.fiscal.fiscal_kpis import (
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
from app.services.fiscal.fiscal_purchases import (
  construir_filtros_compras_nfe,
  construir_params_com_limite_compras,
  construir_ranking_fornecedores_compras,
  construir_ranking_produtos_compras,
  construir_resposta_analise_compras,
)
from app.services.fiscal.fiscal_sales import (
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
from app.services.nfe.nfe_analysis_configs import (
  NFE_CFOP_ANALYSIS_CONFIG,
  NFE_NCM_ANALYSIS_CONFIG,
)
from app.services.shared.email_validation import normalizar_email

logger = logging.getLogger("NFeConsultaService")

NIVEL_HIERARQUIA_BUILDERS = {
  "estado": construir_item_estado,
  "cidade": construir_item_cidade,
  "ncm": construir_item_ncm,
  "produto": construir_item_produto,
}

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
    mensagem_erro: str = "Informe um emitente_cnpj válido.",
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

    email_normalizado = normalizar_email(email)
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
      "regexp_replace(UPPER(COALESCE(n.emitente_cnpj, '')), '[^0-9A-Z]', '', 'g') = %s",
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
      filtros.append("regexp_replace(UPPER(k.emitente_cnpj), '[^0-9A-Z]', '', 'g') = %s")
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
    cnpj_filtrado = self._obter_cnpj_filtrado_obrigatorio(emitente_cnpj)

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

  def _montar_dados_dashboard_vendas(
    self,
    emitente_cnpj: str,
    ano_referencia: int,
    periodo_mes: int | None,
    ano_anterior: int,
    mes_anterior: int | None,
    resultados_ano_atual,
    resultados_filtrados,
    resultados_anteriores,
    limite: int,
  ) -> tuple[dict, dict, list]:
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

    return resumo_atual, resumo_anterior, serie_mensal

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

    resumo_atual, resumo_anterior, serie_mensal = self._montar_dados_dashboard_vendas(
      emitente_cnpj,
      ano_referencia,
      periodo_mes,
      ano_anterior,
      mes_anterior,
      resultados_ano_atual,
      resultados_filtrados,
      resultados_anteriores,
      limite,
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
      inicio = perf_counter()
      logger.debug(
        "Consultando KPIs emitente_cnpj=%s periodo_ano=%s periodo_mes=%s limite=%s offset=%s",
        emitente_cnpj,
        periodo_ano,
        periodo_mes,
        limite,
        offset,
      )
      kpis_rows = self._consulta_repository().listar_kpis(where_clause, parametros)
      logger.info(
        "KPIs consultados emitente_cnpj=%s periodo_ano=%s periodo_mes=%s limite=%s offset=%s linhas=%s tempo=%.3fs",
        emitente_cnpj,
        periodo_ano,
        periodo_mes,
        limite,
        offset,
        len(kpis_rows),
        perf_counter() - inicio,
      )

      if not kpis_rows:
        return []

      resultados = []
      for row in kpis_rows:
        resultados.append(construir_nfe_kpi_consulta_de_row(row))

      return resultados
    
    except Exception:
      logger.exception("Erro ao consultar KPIs NFe")
      raise
    
  def _montar_rankings_compras(
    self,
    repository: NFeConsultaRepository,
    where_clause: str,
    parametros_com_limite: list[object],
  ) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
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

    return (
      top_fornecedores_valor,
      top_fornecedores_quantidade,
      top_produtos_valor,
      top_produtos_quantidade,
    )

  def analisar_compras(
    self,
    emitente_cnpj: Optional[str],
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: int = 5,
  ) -> dict:
    inicio_total = perf_counter()
    cnpj_filtrado = self._obter_cnpj_filtrado_obrigatorio(emitente_cnpj)

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
    (
      top_fornecedores_valor,
      top_fornecedores_quantidade,
      top_produtos_valor,
      top_produtos_quantidade,
    ) = self._montar_rankings_compras(repository, where_clause, parametros_com_limite)
    total_impostos_complementares, total_tributos_reforma = self._obter_totais_tributos_analise(
      cnpj_filtrado,
      periodo_ano,
      periodo_mes,
      "entrada",
    )
    logger.info(
      "Analise compras montada emitente_cnpj=%s periodo_ano=%s periodo_mes=%s limite=%s tempo=%.3fs total_comprado=%s fornecedores_valor=%s fornecedores_qtd=%s produtos_valor=%s produtos_qtd=%s",
      cnpj_filtrado,
      periodo_ano,
      periodo_mes,
      limite,
      perf_counter() - inicio_total,
      total_comprado,
      len(top_fornecedores_valor),
      len(top_fornecedores_quantidade),
      len(top_produtos_valor),
      len(top_produtos_quantidade),
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
    
  def _montar_rankings_vendas(
    self,
    repository: NFeConsultaRepository,
    where_clause: str,
    parametros: list[object],
    parametros_com_limite: list[object],
    limite: Optional[int],
    total_vendido: Decimal,
  ) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict], list[dict], list[dict]]:
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

    return (
      top_clientes_valor,
      top_clientes_quantidade,
      top_produtos_valor,
      top_produtos_quantidade,
      top_cfops_valor,
      top_cidades_valor,
      top_regioes_valor,
    )

  def analisar_vendas(
    self,
    emitente_cnpj: Optional[str],
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: Optional[int] = None,
  ) -> dict:
    cnpj_filtrado = self._obter_cnpj_filtrado_obrigatorio(emitente_cnpj)

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
    (
      top_clientes_valor,
      top_clientes_quantidade,
      top_produtos_valor,
      top_produtos_quantidade,
      top_cfops_valor,
      top_cidades_valor,
      top_regioes_valor,
    ) = self._montar_rankings_vendas(
      repository,
      where_clause,
      parametros,
      parametros_com_limite,
      limite,
      total_vendido,
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
    cnpj_filtrado = self._obter_cnpj_filtrado_obrigatorio(emitente_cnpj)

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
    cnpj_filtrado = self._obter_cnpj_filtrado_obrigatorio(emitente_cnpj)

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

  def _montar_dados_hierarquia_fiscal(
    self,
    dados_hierarquia: dict,
    nivel_resolvido: str,
  ) -> tuple[Decimal, Decimal, Decimal, Optional[tuple], list[dict], int, list[dict], list[dict], list[dict], list[dict], list[dict]]:
    resumo_row = dados_hierarquia["resumo_row"]
    total_faturamento = resumo_row[0] if resumo_row else Decimal("0.00")
    total_impostos = resumo_row[1] if resumo_row else Decimal("0.00")
    percentual_total = calcular_percentual_imposto(total_impostos, total_faturamento)

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
      for uf_item, cidade_item, ncm_item, descricao_item, codigo_item, produto_item, faturamento, imposto_valor
      in dados_hierarquia["rows_hierarquia_completa"]
    ]

    total_registros_nivel = dados_hierarquia["total_registros_nivel"]
    builder_nivel = NIVEL_HIERARQUIA_BUILDERS.get(nivel_resolvido, construir_item_produto)
    itens_nivel_atual = [builder_nivel(*row) for row in dados_hierarquia["rows_nivel"]]

    por_estado = itens_nivel_atual if nivel_resolvido == "estado" else []
    por_cidade = itens_nivel_atual if nivel_resolvido == "cidade" else []
    por_ncm = itens_nivel_atual if nivel_resolvido == "ncm" else []
    por_produto = itens_nivel_atual if nivel_resolvido not in ("estado", "cidade", "ncm") else []

    return (
      total_faturamento,
      total_impostos,
      percentual_total,
      resumo_row,
      hierarquia,
      total_registros_nivel,
      itens_nivel_atual,
      por_estado,
      por_cidade,
      por_ncm,
      por_produto,
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
    cnpj_filtrado = self._obter_cnpj_filtrado_obrigatorio(emitente_cnpj)

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

    nivel_resolvido = resolver_nivel_hierarquia(nivel_atual, estado, cidade, ncm)
    repository = self._consulta_repository()
    dados_hierarquia = repository.consultar_hierarquia_fiscal(
      where_clause,
      parametros,
      nivel_resolvido,
      limite_consulta,
      offset_consulta,
      modo_legado_hierarquia_completa,
    )

    (
      total_faturamento,
      total_impostos,
      percentual_total,
      resumo_row,
      hierarquia,
      total_registros_nivel,
      itens_nivel_atual,
      por_estado,
      por_cidade,
      por_ncm,
      por_produto,
    ) = self._montar_dados_hierarquia_fiscal(dados_hierarquia, nivel_resolvido)

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
    cnpj_filtrado = self._obter_cnpj_filtrado_obrigatorio(emitente_cnpj)

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
