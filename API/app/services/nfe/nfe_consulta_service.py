import logging
from typing import List, Optional
from decimal import Decimal

import psycopg
from fastapi import HTTPException, status

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
from app.services.nfe.empresa_service import normalizar_cnpj
from app.services.fiscal_analysis import (
  FiscalDimensionConfig,
  analisar_fiscal_por_dimensao,
  obter_regiao_por_uf,
)
from app.services.nfe.postres_config import carregar_config_postgres

logger = logging.getLogger("NFeConsultaService")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
formatter = logging.Formatter(
  "[%(asctime)s] [%(levelname)s] %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

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

  def obter_cnpj_por_email(
    self,
    email: Optional[str],
  ) -> Optional[str]:
    if not email:
      return None

    email_normalizado = email.strip().lower()
    if not email_normalizado:
      return None

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(
          """
          SELECT cnpj
          FROM public.login
          WHERE email = %s;
          """,
          (email_normalizado,),
        )
        row = cur.fetchone()

    if not row or not row[0]:
      return None

    cnpj = normalizar_cnpj(row[0])
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
      "LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('5','6','7')",
    ]
    parametros: list[object] = [cnpj_filtrado]

    if periodo_ano:
      filtros_vendas_docs.append("EXTRACT(YEAR FROM n.data_emissao) = %s")
      parametros.append(periodo_ano)

    if periodo_mes:
      filtros_vendas_docs.append("EXTRACT(MONTH FROM n.data_emissao) = %s")
      parametros.append(periodo_mes)

    return " AND ".join(filtros_vendas_docs), parametros

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

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(
          f"""
          SELECT COALESCE(SUM(i.valor_total), 0) AS total_vendido
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          """,
          parametros,
        )
        row = cur.fetchone()

    return row[0] if row else Decimal("0.00")

  def listar_totais_vendas_mensais_bruto(
    self,
    emitente_cnpj: Optional[str],
    periodo_ano: int,
  ) -> dict[int, Decimal]:
    where_clause, parametros = self._montar_filtros_vendas_itens(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=periodo_ano,
    )

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(
          f"""
          SELECT
            EXTRACT(MONTH FROM n.data_emissao)::int AS periodo_mes,
            COALESCE(SUM(i.valor_total), 0) AS total_vendido
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 1
          """,
          parametros,
        )
        rows = cur.fetchall()

    return {
      int(periodo_mes): valor_total or Decimal("0.00")
      for periodo_mes, valor_total in rows
    }

  def consultar_dashboard_vendas(
    self,
    emitente_cnpj: str,
    periodo_ano: int | None = None,
    periodo_mes: int | None = None,
    limite: int = 5,
  ) -> DashboardVendasResponse:
    resultados_anos = self.listar_kpis(emitente_cnpj=emitente_cnpj, limite=120)
    anos_disponiveis = sorted(
      {item.periodo_ano for item in resultados_anos if item.periodo_ano},
      reverse=True,
    )
    ano_referencia = periodo_ano or (anos_disponiveis[0] if anos_disponiveis else None)

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
    ano_anterior, mes_anterior = obter_periodo_anterior(ano_referencia, periodo_mes)

    if periodo_mes is not None:
      resultados_filtrados = [item for item in resultados_ano_atual if item.periodo_mes == periodo_mes]
      resultados_anteriores = (
        [item for item in resultados_ano_atual if item.periodo_mes == mes_anterior]
        if ano_anterior == ano_referencia
        else [item for item in resultados_ano_anterior if item.periodo_mes == mes_anterior]
      )
    else:
      resultados_filtrados = resultados_ano_atual
      resultados_anteriores = resultados_ano_anterior

    total_vendido_atual = self.obter_total_vendido_bruto(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=ano_referencia,
      periodo_mes=periodo_mes,
    )
    total_vendido_anterior = self.obter_total_vendido_bruto(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=ano_anterior,
      periodo_mes=mes_anterior,
    )
    totais_mensais_brutos = self.listar_totais_vendas_mensais_bruto(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=ano_referencia,
    )

    resumo_atual = resumir_vendas_por_kpis(
      resultados_filtrados,
      DashboardVendasResumo,
      limite,
    ).model_copy(update={"total_vendido": total_vendido_atual})
    resumo_anterior = resumir_vendas_por_kpis(
      resultados_anteriores,
      DashboardVendasResumo,
      limite,
    ).model_copy(update={"total_vendido": total_vendido_anterior})

    serie_mensal = [
      SerieMensalVendasItem(
        periodo_ano=ano_referencia,
        periodo_mes=item.periodo_mes or 0,
        total_vendido=totais_mensais_brutos.get(
          item.periodo_mes or 0,
          Decimal(str(item.kpis.total_vendas or 0)),
        ),
        quantidade_notas=int(item.kpis.quantidade_notas or 0),
        total_impostos=(
          Decimal(str(item.kpis.total_icms or 0))
          + Decimal(str(item.kpis.total_ipi or 0))
          + Decimal(str(item.kpis.total_pis or 0))
          + Decimal(str(item.kpis.total_cofins or 0))
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
      resumo_atual=resumo_atual,
      resumo_anterior=resumo_anterior,
      serie_mensal=serie_mensal,
    )
    
  def _filtro_vendas(self) -> str:
    return """
      EXISTS (
        SELECT 1
        FROM public.notas AS n
        JOIN public.notas_itens AS i
          ON i.nota_id = n.id
        JOIN public.notas_cfops AS c
          ON regexp_replace(COALESCE(c.codigo, ''), '\\D', '', 'g')
             = regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g')
        WHERE n.processamento_id = k.processamento_id
          AND LEFT(
                regexp_replace(COALESCE(c.codigo, ''), '\\D', '', 'g'),
                1
              ) IN ('5','6','7')
          AND COALESCE(c.descricao, '') ILIKE 'venda%%'
        LIMIT 1
      )
    """

  def obter_ultimo_periodo(
    self,
    emitente_cnpj: Optional[str] = None,
  ) -> tuple[int, int]:
    filtros = []
    parametros: List[object] = []
    
    cnpj_filtrado = self._normalizar_cnpj_filtro(
      emitente_cnpj,
      permitir_zerado=False,
    )

    if cnpj_filtrado:
      filtros.append(
        "regexp_replace(emitente_cnpj, '\\\\D', '', 'g') = %s"
      )
      parametros.append(cnpj_filtrado)

    where_clause = ""
    if filtros:
      where_clause = "WHERE " + " AND ".join(filtros)

    sql = f"""
      SELECT
        periodo_ano,
        periodo_mes
      FROM public.notas_kpis AS k
      {where_clause}
      ORDER BY periodo_ano DESC, periodo_mes DESC, id DESC
      LIMIT 1;
    """

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(sql, parametros)
        row = cur.fetchone()

    if not row:
      raise ValueError("Nenhum processamento encontrado para o emitente.")

    return row[0], row[1]

  def obter_periodos_disponiveis(
    self,
    emitente_cnpj: Optional[str] = None,
    limite: int = 2,
  ) -> List[tuple[int, int]]:
    filtros = []
    parametros: List[object] = []

    cnpj_filtrado = self._normalizar_cnpj_filtro(
      emitente_cnpj,
      permitir_zerado=False,
    )
    
    if cnpj_filtrado:
      filtros.append(
        "regexp_replace(emitente_cnpj, '\\\\D', '', 'g') = %s"
      )
      parametros.append(cnpj_filtrado)

    where_clause = ""
    if filtros:
      where_clause = "WHERE " + " AND ".join(filtros)

    sql = f"""
      SELECT
        periodo_ano,
        periodo_mes
      FROM public.notas_kpis AS k
      {where_clause}
      ORDER BY periodo_ano DESC, periodo_mes DESC, id DESC
      LIMIT %s;
    """
    parametros.append(limite)

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(sql, parametros)
        rows = cur.fetchall()

    return [(row[0], row[1]) for row in rows]

  def _buscar_kpi_periodo(
    self,
    periodo_ano: int,
    periodo_mes: int,
    emitente_cnpj: Optional[str] = None,
  ) -> Optional[NFeKPI]:
    filtros = ["k.periodo_ano = %s", "k.periodo_mes = %s"]
    parametros: List[object] = [periodo_ano, periodo_mes]

    cnpj_filtrado = self._normalizar_cnpj_filtro(
      emitente_cnpj,
      permitir_zerado=False,
    )
    
    if cnpj_filtrado:
      filtros.append(
        "regexp_replace(k.emitente_cnpj, '\\\\D', '', 'g') = %s"
      )
      parametros.append(cnpj_filtrado)

    where_clause = " AND ".join(filtros)
    if where_clause:
      where_clause = f"WHERE {where_clause}"

    sql_kpis = f"""
      SELECT
        k.emitente_cnpj,
        k.id,
        k.processamento_id,
        k.total_vendas,
        k.quantidade_notas,
        k.ticket_medio,
        k.maior_nota,
        k.menor_nota,
        k.total_icms,
        k.total_ipi,
        k.total_pis,
        k.total_cofins,
        k.top_clientes,
        k.top_produtos,
        k.top_cidades
      FROM public.notas_kpis AS k
      LEFT JOIN public.notas_processamentos AS p
        ON p.id = k.processamento_id
      {where_clause}
      ORDER BY k.periodo_ano DESC, k.periodo_mes DESC, k.id DESC
      LIMIT 1;
    """

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(sql_kpis, parametros)
        row = cur.fetchone()

    if not row:
      return None

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
      top_cidades=self._normalizar_top_cidades(row[14]),  
    )

  def _calcular_variacao_percentual(
    self,
    atual: Decimal,
    anterior: Decimal,
  ) -> Optional[Decimal]:
    if anterior == 0:
      if atual == 0:
        return Decimal("0.00")
      return None
    return ((atual - anterior) / anterior * Decimal("100")).quantize(
      Decimal("0.01")
    )
    
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

  def listar_kpis(
    self,
    emitente_cnpj: Optional[str] = None,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: int = 100,
    offset: int = 0,
  ) -> List[NFeKPIConsulta]:

    filtros = []
    parametros = []

    cnpj_filtrado = self._normalizar_cnpj_filtro(
      emitente_cnpj,
      permitir_zerado=False,
    )
    
    if cnpj_filtrado:
      filtros.append(
        "regexp_replace(k.emitente_cnpj, '\\\\D', '', 'g') = %s"
      )
      parametros.append(cnpj_filtrado)

    if periodo_ano:
      filtros.append("k.periodo_ano = %s")
      parametros.append(periodo_ano)

    if periodo_mes:
      filtros.append("k.periodo_mes = %s")
      parametros.append(periodo_mes)

    where_clause = " AND ".join(filtros)
    if where_clause:
      where_clause = f"WHERE {where_clause}"

    sql_kpis = f"""
      SELECT
        k.periodo_ano,
        k.periodo_mes,
        k.emitente_cnpj,
        k.id,
        k.processamento_id,
        k.total_vendas,
        k.quantidade_notas,
        k.ticket_medio,
        k.maior_nota,
        k.menor_nota,
        k.total_icms,
        k.total_ipi,
        k.total_pis,
        k.total_cofins,
        k.top_clientes,
        k.top_produtos,
        k.top_cidades
      FROM public.notas_kpis AS k
      {where_clause}
      ORDER BY
        k.emitente_cnpj,
        k.periodo_ano DESC,
        k.periodo_mes DESC,
        k.id DESC
      LIMIT %s OFFSET %s;
    """
    parametros.extend([limite, offset])

    try:
      #logger.debug("Abrindo conexão com PostgreSQL")
      with psycopg.connect(**self.conn_params) as conn:
        #logger.debug("Conexão aberta com sucesso")
        with conn.cursor() as cur:
          logger.debug("Consultando KPIs")
          cur.execute(sql_kpis, parametros)
          kpis_rows = cur.fetchall()

          if not kpis_rows:
            return []

      resultados = []
      for row in kpis_rows:
        resultados.append(
          NFeKPIConsulta(
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
              top_cidades=self._normalizar_top_cidades(row[16]),
            ),
          )
        )

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

    filtros_docs = [
      (
        "("
        "regexp_replace(COALESCE(n.destinatario_documento, ''), '\\D', '', 'g') = %s "
        "OR regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g') = %s"
        ")"
      ),
      "LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('1','2','3')",
    ]
    parametros: list[object] = [cnpj_filtrado, cnpj_filtrado]

    if periodo_ano:
      filtros_docs.append("EXTRACT(YEAR FROM n.data_emissao) = %s")
      parametros.append(periodo_ano)

    if periodo_mes:
      filtros_docs.append("EXTRACT(MONTH FROM n.data_emissao) = %s")
      parametros.append(periodo_mes)

    where_clause = " AND ".join(filtros_docs)

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(
          f"""
          SELECT COALESCE(SUM(i.valor_total), 0) AS total_comprado
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          """,
          parametros,
        )
        total_comprado_row = cur.fetchone()
        total_comprado = total_comprado_row[0] if total_comprado_row else Decimal("0.00")

        cur.execute(
          f"""
          SELECT
            COALESCE(NULLIF(TRIM(n.emitente_cnpj), ''), 'Fornecedor não identificado') AS fornecedor,
            COALESCE(SUM(i.valor_total), 0) AS valor_total,
            COUNT(DISTINCT n.id) AS quantidade_documentos
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC, 1 ASC
          LIMIT %s
          """,
          [*parametros, limite],
        )
        top_fornecedores_valor = [
          {
            "fornecedor": fornecedor,
            "valor_total": valor_total or Decimal("0.00"),
            "quantidade_documentos": quantidade_documentos or 0,
          }
          for fornecedor, valor_total, quantidade_documentos in cur.fetchall()
        ]

        cur.execute(
          f"""
          SELECT
            COALESCE(NULLIF(TRIM(n.emitente_cnpj), ''), 'Fornecedor não identificado') AS fornecedor,
            COALESCE(SUM(i.valor_total), 0) AS valor_total,
            COUNT(DISTINCT n.id) AS quantidade_documentos
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 3 DESC, 2 DESC, 1 ASC
          LIMIT %s
          """,
          [*parametros, limite],
        )
        top_fornecedores_quantidade = [
          {
            "fornecedor": fornecedor,
            "valor_total": valor_total or Decimal("0.00"),
            "quantidade_documentos": quantidade_documentos or 0,
          }
          for fornecedor, valor_total, quantidade_documentos in cur.fetchall()
        ]

        cur.execute(
          f"""
          SELECT
            COALESCE(NULLIF(TRIM(i.descricao), ''), 'Produto não identificado') AS produto,
            COALESCE(SUM(i.valor_total), 0) AS valor_total,
            COALESCE(SUM(i.quantidade), 0) AS quantidade_total
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC, 1 ASC
          LIMIT %s
          """,
          [*parametros, limite],
        )
        top_produtos_valor = [
          {
            "produto": produto,
            "valor_total": valor_total or Decimal("0.00"),
            "quantidade_total": quantidade_total or Decimal("0.00"),
          }
          for produto, valor_total, quantidade_total in cur.fetchall()
        ]

        cur.execute(
          f"""
          SELECT
            COALESCE(NULLIF(TRIM(i.descricao), ''), 'Produto não identificado') AS produto,
            COALESCE(SUM(i.valor_total), 0) AS valor_total,
            COALESCE(SUM(i.quantidade), 0) AS quantidade_total
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 3 DESC, 2 DESC, 1 ASC
          LIMIT %s
          """,
          [*parametros, limite],
        )
        top_produtos_quantidade = [
          {
            "produto": produto,
            "valor_total": valor_total or Decimal("0.00"),
            "quantidade_total": quantidade_total or Decimal("0.00"),
          }
          for produto, valor_total, quantidade_total in cur.fetchall()
        ]

    return {
      "emitente_cnpj": cnpj_filtrado,
      "periodo_ano": periodo_ano,
      "periodo_mes": periodo_mes,
      "total_comprado": total_comprado or Decimal("0.00"),
      "top_fornecedores_valor": top_fornecedores_valor,
      "top_fornecedores_quantidade": top_fornecedores_quantidade,
      "top_produtos_valor": top_produtos_valor,
      "top_produtos_quantidade": top_produtos_quantidade,
    }
    
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

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(
          f"""
          SELECT COALESCE(SUM(i.valor_total), 0) AS total_vendido
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          """,
          parametros,
        )
        total_vendido_row = cur.fetchone()
        total_vendido = total_vendido_row[0] if total_vendido_row else Decimal("0.00")

        cur.execute(
          f"""
          SELECT
            COALESCE(NULLIF(TRIM(n.destinatario_nome), ''), 'Cliente não identificado') AS cliente,
            COALESCE(SUM(i.valor_total), 0) AS valor_total,
            COUNT(DISTINCT n.id) AS quantidade_documentos
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC, 1 ASC
          LIMIT %s
          """,
          [*parametros, limite],
        )
        top_clientes_valor = [
          {
            "cliente": cliente,
            "valor_total": valor_total or Decimal("0.00"),
            "quantidade_documentos": quantidade_documentos or 0,
          }
          for cliente, valor_total, quantidade_documentos in cur.fetchall()
        ]

        cur.execute(
          f"""
          SELECT
            COALESCE(NULLIF(TRIM(n.destinatario_nome), ''), 'Cliente não identificado') AS cliente,
            COALESCE(SUM(i.valor_total), 0) AS valor_total,
            COUNT(DISTINCT n.id) AS quantidade_documentos
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 3 DESC, 2 DESC, 1 ASC
          LIMIT %s
          """,
          [*parametros, limite],
        )
        top_clientes_quantidade = [
          {
            "cliente": cliente,
            "valor_total": valor_total or Decimal("0.00"),
            "quantidade_documentos": quantidade_documentos or 0,
          }
          for cliente, valor_total, quantidade_documentos in cur.fetchall()
        ]

        cur.execute(
          f"""
          SELECT
            COALESCE(NULLIF(TRIM(i.descricao), ''), 'Produto não identificado') AS produto,
            COALESCE(SUM(i.valor_total), 0) AS valor_total,
            COALESCE(SUM(i.quantidade), 0) AS quantidade_total
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC, 1 ASC
          LIMIT %s
          """,
          [*parametros, limite],
        )
        top_produtos_valor = [
          {
            "produto": produto,
            "valor_total": valor_total or Decimal("0.00"),
            "quantidade_total": quantidade_total or Decimal("0.00"),
          }
          for produto, valor_total, quantidade_total in cur.fetchall()
        ]

        cur.execute(
          f"""
          SELECT
            COALESCE(NULLIF(TRIM(i.descricao), ''), 'Produto não identificado') AS produto,
            COALESCE(SUM(i.valor_total), 0) AS valor_total,
            COALESCE(SUM(i.quantidade), 0) AS quantidade_total
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 3 DESC, 2 DESC, 1 ASC
          LIMIT %s
          """,
          [*parametros, limite],
        )
        top_produtos_quantidade = [
          {
            "produto": produto,
            "valor_total": valor_total or Decimal("0.00"),
            "quantidade_total": quantidade_total or Decimal("0.00"),
          }
          for produto, valor_total, quantidade_total in cur.fetchall()
        ]

        cur.execute(
          f"""
          SELECT
            COALESCE(NULLIF(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), ''), '0000') AS cfop,
            COALESCE(NULLIF(TRIM(c.descricao), ''), 'CFOP sem descrição') AS descricao,
            COALESCE(SUM(i.valor_total), 0) AS valor_total
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          LEFT JOIN public.notas_cfops AS c
            ON regexp_replace(COALESCE(c.codigo, ''), '\\D', '', 'g')
               = regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g')
          WHERE {where_clause}
          GROUP BY 1, 2
          ORDER BY 3 DESC, 1 ASC
          LIMIT %s
          """,
          [*parametros, limite],
        )
        top_cfops_valor = [
          {
            "cfop": cfop,
            "descricao": descricao,
            "valor_total": valor_total or Decimal("0.00"),
            "participacao_percentual": (
              ((valor_total or Decimal("0.00")) / total_vendido) * Decimal("100")
              if total_vendido
              else Decimal("0.00")
            ),
          }
          for cfop, descricao, valor_total in cur.fetchall()
        ]

        cur.execute(
          f"""
          SELECT
            COALESCE(NULLIF(TRIM(n.destinatario_cidade), ''), 'Cidade nÃ£o identificada') AS cidade,
            COALESCE(NULLIF(TRIM(n.destinatario_uf), ''), '') AS uf,
            COALESCE(SUM(i.valor_total), 0) AS valor_total,
            COUNT(DISTINCT n.id) AS quantidade_documentos
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          GROUP BY 1, 2
          ORDER BY 3 DESC, 1 ASC
          LIMIT %s
          """,
          [*parametros, limite],
        )
        top_cidades_valor = [
          {
            "cidade": cidade,
            "uf": uf,
            "valor_total": valor_total or Decimal("0.00"),
            "quantidade_documentos": quantidade_documentos or 0,
          }
          for cidade, uf, valor_total, quantidade_documentos in cur.fetchall()
        ]

        cur.execute(
          f"""
          SELECT
            COALESCE(NULLIF(TRIM(n.destinatario_uf), ''), '') AS uf,
            COALESCE(SUM(i.valor_total), 0) AS valor_total,
            COUNT(DISTINCT n.id) AS quantidade_documentos
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC, 1 ASC
          """,
          parametros,
        )
        top_regioes_map: dict[str, dict[str, Decimal | int | str]] = {}
        for uf, valor_total, quantidade_documentos in cur.fetchall():
          regiao = obter_regiao_por_uf(uf)
          if not regiao:
            continue

          acumulado = top_regioes_map.setdefault(
            regiao,
            {
              "regiao": regiao,
              "valor_total": Decimal("0.00"),
              "quantidade_documentos": 0,
            },
          )
          acumulado["valor_total"] = Decimal(str(acumulado["valor_total"])) + (valor_total or Decimal("0.00"))
          acumulado["quantidade_documentos"] = int(acumulado["quantidade_documentos"]) + (quantidade_documentos or 0)

        top_regioes_valor = sorted(
          top_regioes_map.values(),
          key=lambda item: Decimal(str(item["valor_total"])),
          reverse=True,
        )[:limite]

    return {
      "emitente_cnpj": cnpj_filtrado,
      "periodo_ano": periodo_ano,
      "periodo_mes": periodo_mes,
      "total_vendido": total_vendido or Decimal("0.00"),
      "top_clientes_valor": top_clientes_valor,
      "top_clientes_quantidade": top_clientes_quantidade,
      "top_produtos_valor": top_produtos_valor,
      "top_produtos_quantidade": top_produtos_quantidade,
      "top_cfops_valor": top_cfops_valor,
      "top_regioes_valor": top_regioes_valor,
      "top_cidades_valor": top_cidades_valor,
    }

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

    return {
      "emitente_cnpj": cnpj_filtrado,
      "periodo_ano": periodo_ano,
      "periodo_mes": periodo_mes,
      "total_movimentado": resultado["total_movimentado"],
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

    return {
      "emitente_cnpj": cnpj_filtrado,
      "periodo_ano": periodo_ano,
      "periodo_mes": periodo_mes,
      "total_movimentado": resultado["total_movimentado"],
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

    filtros = [
      "regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g') = %s",
      "LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('5','6','7')",
    ]
    parametros: list[object] = [cnpj_filtrado]

    if periodo_ano is not None:
      filtros.append("EXTRACT(YEAR FROM n.data_emissao) = %s")
      parametros.append(periodo_ano)

    if periodo_mes is not None:
      filtros.append("EXTRACT(MONTH FROM n.data_emissao) = %s")
      parametros.append(periodo_mes)

    if estado and estado.strip():
      filtros.append("UPPER(COALESCE(NULLIF(TRIM(n.destinatario_uf), ''), 'Sem UF')) = %s")
      parametros.append(estado.strip().upper())

    if cidade and cidade.strip():
      filtros.append("UPPER(COALESCE(NULLIF(TRIM(n.destinatario_cidade), ''), 'Cidade nao identificada')) = %s")
      parametros.append(cidade.strip().upper())

    if ncm and ncm.strip():
      filtros.append("regexp_replace(COALESCE(i.ncm, ''), '\\D', '', 'g') = %s")
      parametros.append("".join(ch for ch in ncm if ch.isdigit()))

    if produto_codigo and produto_codigo.strip():
      filtros.append("COALESCE(NULLIF(TRIM(i.produto_codigo), ''), 'SEM-CODIGO') = %s")
      parametros.append(produto_codigo.strip())

    where_clause = " AND ".join(filtros)
    limite_consulta = limite if limite is not None else 100000
    offset_consulta = max(offset, 0)
    modo_legado_hierarquia_completa = (
      nivel_atual is None
      and not estado
      and not cidade
      and not ncm
      and not produto_codigo
      and offset_consulta == 0
    )

    base_cte = f"""
      WITH itens_filtrados AS (
        SELECT
          n.id AS documento_id,
          COALESCE(NULLIF(TRIM(n.destinatario_uf), ''), 'Sem UF') AS estado,
          COALESCE(NULLIF(TRIM(n.destinatario_cidade), ''), 'Cidade nao identificada') AS cidade,
          COALESCE(NULLIF(TRIM(i.produto_codigo), ''), 'SEM-CODIGO') AS produto_codigo,
          COALESCE(NULLIF(TRIM(i.descricao), ''), 'Produto sem descricao') AS produto_descricao,
          regexp_replace(COALESCE(i.ncm, ''), '\\D', '', 'g') AS ncm_codigo,
          COALESCE(i.valor_total, 0) AS faturamento,
          (
            COALESCE(n.valor_icms, 0)
            + COALESCE(n.valor_ipi, 0)
            + COALESCE(n.valor_pis, 0)
            + COALESCE(n.valor_cofins, 0)
          ) AS imposto_total_nota
        FROM public.notas AS n
        JOIN public.notas_itens AS i
          ON i.nota_id = n.id
        WHERE {where_clause}
      ),
      notas_rateio AS (
        SELECT
          documento_id,
          COALESCE(SUM(faturamento), 0) AS faturamento_total_nota,
          MAX(imposto_total_nota) AS imposto_total_nota
        FROM itens_filtrados
        GROUP BY documento_id
      ),
      base AS (
        SELECT
          itens.documento_id,
          itens.estado,
          itens.cidade,
          COALESCE(NULLIF(itens.ncm_codigo, ''), '00000000') AS ncm,
          COALESCE(NULLIF(TRIM(nc.descricao), ''), 'NCM sem descricao') AS descricao_ncm,
          itens.produto_codigo,
          itens.produto_descricao,
          itens.faturamento,
          CASE
            WHEN COALESCE(rateio.faturamento_total_nota, 0) > 0 THEN
              (itens.faturamento / rateio.faturamento_total_nota) * rateio.imposto_total_nota
            ELSE 0::numeric
          END AS imposto_valor
        FROM itens_filtrados AS itens
        JOIN notas_rateio AS rateio
          ON rateio.documento_id = itens.documento_id
        LEFT JOIN public.ncm_catalogo AS nc
          ON regexp_replace(COALESCE(nc.codigo, ''), '\\D', '', 'g')
             = COALESCE(NULLIF(itens.ncm_codigo, ''), '00000000')
      )
    """

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS tmp_nfe_fiscal_hierarquia_base")
        cur.execute(
          f"""
          CREATE TEMP TABLE tmp_nfe_fiscal_hierarquia_base ON COMMIT DROP AS
          {base_cte}
          SELECT *
          FROM base
          """,
          tuple(parametros),
        )
        cur.execute("ANALYZE tmp_nfe_fiscal_hierarquia_base")

        cur.execute(
          """
          SELECT
            COALESCE(SUM(faturamento), 0) AS total_faturamento,
            COALESCE(SUM(imposto_valor), 0) AS total_impostos,
            COUNT(DISTINCT documento_id) AS quantidade_documentos,
            COUNT(DISTINCT estado) AS total_estados,
            COUNT(DISTINCT CONCAT(cidade, '::', estado)) AS total_cidades,
            COUNT(DISTINCT ncm) AS total_ncms,
            COUNT(DISTINCT CONCAT(produto_codigo, '::', produto_descricao)) AS total_produtos
          FROM tmp_nfe_fiscal_hierarquia_base
          """,
        )
        resumo_row = cur.fetchone()

        total_faturamento = resumo_row[0] if resumo_row else Decimal("0.00")
        total_impostos = resumo_row[1] if resumo_row else Decimal("0.00")
        percentual_total = (
          (total_impostos / total_faturamento) * Decimal("100")
          if total_faturamento
          else Decimal("0.00")
        )
        hierarquia: list[dict] = []
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
              COALESCE(SUM(faturamento), 0) AS faturamento,
              COALESCE(SUM(imposto_valor), 0) AS imposto_valor
            FROM tmp_nfe_fiscal_hierarquia_base
            GROUP BY 1, 2, 3, 4, 5, 6
            ORDER BY 1 ASC, 2 ASC, 7 DESC, 5 ASC
            LIMIT %s
            """,
            (limite_consulta,),
          )
          hierarquia = [
            {
              "estado": uf_item,
              "cidade": cidade_item,
              "uf": uf_item,
              "ncm": ncm_item,
              "descricao_ncm": descricao_item,
              "produto_codigo": codigo_item,
              "produto": produto_item,
              "faturamento": faturamento or Decimal("0.00"),
              "imposto_valor": imposto_valor or Decimal("0.00"),
              "imposto_percentual": (((imposto_valor or Decimal("0.00")) / (faturamento or Decimal("0.00"))) * Decimal("100")) if faturamento else Decimal("0.00"),
            }
            for uf_item, cidade_item, ncm_item, descricao_item, codigo_item, produto_item, faturamento, imposto_valor in cur.fetchall()
          ]
        nivel_resolvido = nivel_atual or ("produto" if ncm else "ncm" if cidade else "cidade" if estado else "estado")
        itens_nivel_atual: list[dict] = []
        por_estado: list[dict] = []
        por_cidade: list[dict] = []
        por_ncm: list[dict] = []
        por_produto: list[dict] = []
        total_registros_nivel = 0

        if nivel_resolvido == "estado":
          cur.execute("SELECT COUNT(DISTINCT estado) FROM tmp_nfe_fiscal_hierarquia_base")
          total_registros_nivel = (cur.fetchone() or [0])[0] or 0
          cur.execute(
            """
            SELECT
              estado,
              COALESCE(SUM(faturamento), 0) AS faturamento,
              COALESCE(SUM(imposto_valor), 0) AS imposto_valor
            FROM tmp_nfe_fiscal_hierarquia_base
            GROUP BY 1
            ORDER BY 2 DESC, 1 ASC
            LIMIT %s
            OFFSET %s
            """,
            (limite_consulta, offset_consulta),
          )
          por_estado = [
            {
              "estado": uf_item,
              "faturamento": faturamento or Decimal("0.00"),
              "imposto_valor": imposto_valor or Decimal("0.00"),
              "imposto_percentual": (((imposto_valor or Decimal("0.00")) / (faturamento or Decimal("0.00"))) * Decimal("100")) if faturamento else Decimal("0.00"),
            }
            for uf_item, faturamento, imposto_valor in cur.fetchall()
          ]
          itens_nivel_atual = por_estado
        elif nivel_resolvido == "cidade":
          cur.execute("SELECT COUNT(DISTINCT CONCAT(cidade, '::', estado)) FROM tmp_nfe_fiscal_hierarquia_base")
          total_registros_nivel = (cur.fetchone() or [0])[0] or 0
          cur.execute(
            """
            SELECT
              cidade,
              estado,
              COALESCE(SUM(faturamento), 0) AS faturamento,
              COALESCE(SUM(imposto_valor), 0) AS imposto_valor
            FROM tmp_nfe_fiscal_hierarquia_base
            GROUP BY 1, 2
            ORDER BY 3 DESC, 1 ASC, 2 ASC
            LIMIT %s
            OFFSET %s
            """,
            (limite_consulta, offset_consulta),
          )
          por_cidade = [
            {
              "cidade": cidade_item,
              "uf": uf_item,
              "faturamento": faturamento or Decimal("0.00"),
              "imposto_valor": imposto_valor or Decimal("0.00"),
              "imposto_percentual": (((imposto_valor or Decimal("0.00")) / (faturamento or Decimal("0.00"))) * Decimal("100")) if faturamento else Decimal("0.00"),
            }
            for cidade_item, uf_item, faturamento, imposto_valor in cur.fetchall()
          ]
          itens_nivel_atual = por_cidade
        elif nivel_resolvido == "ncm":
          cur.execute("SELECT COUNT(DISTINCT ncm) FROM tmp_nfe_fiscal_hierarquia_base")
          total_registros_nivel = (cur.fetchone() or [0])[0] or 0
          cur.execute(
            """
            SELECT
              ncm,
              descricao_ncm,
              COUNT(DISTINCT CONCAT(produto_codigo, '::', produto_descricao)) AS quantidade_produtos,
              COALESCE(SUM(faturamento), 0) AS faturamento,
              COALESCE(SUM(imposto_valor), 0) AS imposto_valor
            FROM tmp_nfe_fiscal_hierarquia_base
            GROUP BY 1, 2
            ORDER BY 4 DESC, 1 ASC
            LIMIT %s
            OFFSET %s
            """,
            (limite_consulta, offset_consulta),
          )
          por_ncm = [
            {
              "ncm": ncm_item,
              "descricao": descricao_item,
              "quantidade_produtos": quantidade_produtos or 0,
              "faturamento": faturamento or Decimal("0.00"),
              "imposto_valor": imposto_valor or Decimal("0.00"),
              "imposto_percentual": (((imposto_valor or Decimal("0.00")) / (faturamento or Decimal("0.00"))) * Decimal("100")) if faturamento else Decimal("0.00"),
            }
            for ncm_item, descricao_item, quantidade_produtos, faturamento, imposto_valor in cur.fetchall()
          ]
          itens_nivel_atual = por_ncm
        else:
          cur.execute("SELECT COUNT(DISTINCT CONCAT(produto_codigo, '::', produto_descricao)) FROM tmp_nfe_fiscal_hierarquia_base")
          total_registros_nivel = (cur.fetchone() or [0])[0] or 0
          cur.execute(
            """
            SELECT
              produto_codigo,
              produto_descricao,
              COALESCE(SUM(faturamento), 0) AS faturamento,
              COALESCE(SUM(imposto_valor), 0) AS imposto_valor
            FROM tmp_nfe_fiscal_hierarquia_base
            GROUP BY 1, 2
            ORDER BY 3 DESC, 1 ASC, 2 ASC
            LIMIT %s
            OFFSET %s
            """,
            (limite_consulta, offset_consulta),
          )
          por_produto = [
            {
              "produto_codigo": codigo_item,
              "produto": produto_item,
              "faturamento": faturamento or Decimal("0.00"),
              "imposto_valor": imposto_valor or Decimal("0.00"),
              "imposto_percentual": (((imposto_valor or Decimal("0.00")) / (faturamento or Decimal("0.00"))) * Decimal("100")) if faturamento else Decimal("0.00"),
            }
            for codigo_item, produto_item, faturamento, imposto_valor in cur.fetchall()
          ]
          itens_nivel_atual = por_produto

    return {
      "emitente_cnpj": cnpj_filtrado,
      "periodo_ano": periodo_ano,
      "periodo_mes": periodo_mes,
      "nivel_atual": nivel_resolvido,
      "offset": offset_consulta,
      "limite": limite_consulta,
      "total_registros_nivel": total_registros_nivel,
      "possui_mais_registros": (offset_consulta + len(itens_nivel_atual)) < total_registros_nivel,
      "total_faturamento": total_faturamento or Decimal("0.00"),
      "total_impostos": total_impostos or Decimal("0.00"),
      "percentual_impostos_sobre_faturamento": percentual_total,
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

    filtros_docs = [
      "regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g') = %s",
      "LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('5','6','7')",
    ]
    parametros: list[object] = [cnpj_filtrado]

    if periodo_ano:
      filtros_docs.append("EXTRACT(YEAR FROM n.data_emissao) = %s")
      parametros.append(periodo_ano)

    if periodo_mes:
      filtros_docs.append("EXTRACT(MONTH FROM n.data_emissao) = %s")
      parametros.append(periodo_mes)

    where_clause = " AND ".join(filtros_docs)

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(
          f"""
          SELECT
            COALESCE(SUM(i.valor_total), 0) AS total_vendido,
            COUNT(DISTINCT COALESCE(NULLIF(TRIM(n.destinatario_nome), ''), 'Cliente não identificado')) AS total_clientes
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          """,
          parametros,
        )
        totais_row = cur.fetchone()
        total_vendido = totais_row[0] if totais_row else Decimal("0.00")
        total_clientes = totais_row[1] if totais_row else 0

        cur.execute(
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
              COALESCE(NULLIF(TRIM(n.destinatario_nome), ''), 'Cliente não identificado') AS cliente,
              COALESCE(SUM(i.valor_total), 0) AS valor_total,
              COUNT(DISTINCT n.id) AS quantidade_documentos,
              CASE
                WHEN COUNT(DISTINCT n.id) = 0 THEN 0
                ELSE COALESCE(SUM(i.valor_total), 0) / COUNT(DISTINCT n.id)
              END AS ticket_medio
            FROM public.notas AS n
            JOIN public.notas_itens AS i
              ON i.nota_id = n.id
            WHERE {where_clause}
            GROUP BY 1
          ) base
          ORDER BY valor_total DESC, cliente ASC
          LIMIT %s
          """,
          [total_vendido or Decimal("0.00"), total_vendido or Decimal("0.00"), *parametros, limite],
        )
        top_clientes_valor = [
          {
            "cliente": cliente,
            "valor_total": valor_total or Decimal("0.00"),
            "quantidade_documentos": quantidade_documentos or 0,
            "ticket_medio": ticket_medio or Decimal("0.00"),
            "percentual_participacao": percentual_participacao or Decimal("0.00"),
          }
          for cliente, valor_total, quantidade_documentos, ticket_medio, percentual_participacao in cur.fetchall()
        ]

        cur.execute(
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
              COALESCE(NULLIF(TRIM(n.destinatario_nome), ''), 'Cliente não identificado') AS cliente,
              COALESCE(SUM(i.valor_total), 0) AS valor_total,
              COUNT(DISTINCT n.id) AS quantidade_documentos,
              CASE
                WHEN COUNT(DISTINCT n.id) = 0 THEN 0
                ELSE COALESCE(SUM(i.valor_total), 0) / COUNT(DISTINCT n.id)
              END AS ticket_medio
            FROM public.notas AS n
            JOIN public.notas_itens AS i
              ON i.nota_id = n.id
            WHERE {where_clause}
            GROUP BY 1
          ) base
          ORDER BY quantidade_documentos DESC, valor_total DESC, cliente ASC
          LIMIT %s
          """,
          [total_vendido or Decimal("0.00"), total_vendido or Decimal("0.00"), *parametros, limite],
        )
        top_clientes_quantidade = [
          {
            "cliente": cliente,
            "valor_total": valor_total or Decimal("0.00"),
            "quantidade_documentos": quantidade_documentos or 0,
            "ticket_medio": ticket_medio or Decimal("0.00"),
            "percentual_participacao": percentual_participacao or Decimal("0.00"),
          }
          for cliente, valor_total, quantidade_documentos, ticket_medio, percentual_participacao in cur.fetchall()
        ]

    return {
      "emitente_cnpj": cnpj_filtrado,
      "periodo_ano": periodo_ano,
      "periodo_mes": periodo_mes,
      "total_vendido": total_vendido or Decimal("0.00"),
      "total_clientes": int(total_clientes or 0),
      "top_clientes_valor": top_clientes_valor,
      "top_clientes_quantidade": top_clientes_quantidade,
    }
      
  def comparar_kpis_mensal(
    self,
    periodo_ano: int,
    periodo_mes: int,
    emitente_cnpj: Optional[str] = None,
    periodo_anterior_ano: Optional[int] = None,
    periodo_anterior_mes: Optional[int] = None,
  ) -> Optional[KPIsComparativo]:
    if periodo_anterior_ano is None or periodo_anterior_mes is None:
      if periodo_mes == 1:
        periodo_anterior_mes = 12
        periodo_anterior_ano = periodo_ano - 1
      else:
        periodo_anterior_mes = periodo_mes - 1
        periodo_anterior_ano = periodo_ano

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
    
    return self._montar_comparativo(kpi_atual, kpi_anterior)

  def _montar_comparativo(
    self,
    kpi_atual: NFeKPI,
    kpi_anterior: Optional[NFeKPI],
  ) -> KPIsComparativo:
    anterior = kpi_anterior or NFeKPI(
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

    total_vendas_atual = Decimal(kpi_atual.total_vendas)
    total_vendas_anterior = Decimal(anterior.total_vendas)
    ticket_medio_atual = Decimal(kpi_atual.ticket_medio)
    ticket_medio_anterior = Decimal(anterior.ticket_medio)
    maior_nota_atual = Decimal(kpi_atual.maior_nota)
    maior_nota_anterior = Decimal(anterior.maior_nota)
    menor_nota_atual = Decimal(kpi_atual.menor_nota)
    menor_nota_anterior = Decimal(anterior.menor_nota)
    total_icms_atual = Decimal(kpi_atual.total_icms)
    total_icms_anterior = Decimal(anterior.total_icms)
    total_ipi_atual = Decimal(kpi_atual.total_ipi)
    total_ipi_anterior = Decimal(anterior.total_ipi)
    total_pis_atual = Decimal(kpi_atual.total_pis)
    total_pis_anterior = Decimal(anterior.total_pis)
    total_cofins_atual = Decimal(kpi_atual.total_cofins)
    total_cofins_anterior = Decimal(anterior.total_cofins)

    return KPIsComparativo(
      total_vendas=KPIComparativoValor(
        atual=total_vendas_atual,
        anterior=total_vendas_anterior,
        variacao_percentual=self._calcular_variacao_percentual(
          total_vendas_atual, total_vendas_anterior
        ),
      ),
      quantidade_notas=KPIComparativoQuantidade(
        atual=kpi_atual.quantidade_notas,
        anterior=anterior.quantidade_notas,
        variacao_percentual=self._calcular_variacao_percentual(
          Decimal(kpi_atual.quantidade_notas),
          Decimal(anterior.quantidade_notas),
        ),
      ),
      ticket_medio=KPIComparativoValor(
        atual=ticket_medio_atual,
        anterior=ticket_medio_anterior,
        variacao_percentual=self._calcular_variacao_percentual(
          ticket_medio_atual, ticket_medio_anterior
        ),
      ),
      maior_nota=KPIComparativoValor(
        atual=maior_nota_atual,
        anterior=maior_nota_anterior,
        variacao_percentual=self._calcular_variacao_percentual(
          maior_nota_atual, maior_nota_anterior
        ),
      ),
      menor_nota=KPIComparativoValor(
        atual=menor_nota_atual,
        anterior=menor_nota_anterior,
        variacao_percentual=self._calcular_variacao_percentual(
          menor_nota_atual, menor_nota_anterior
        ),
      ),
      total_icms=KPIComparativoValor(
        atual=total_icms_atual,
        anterior=total_icms_anterior,
        variacao_percentual=self._calcular_variacao_percentual(
          total_icms_atual, total_icms_anterior
        ),
      ),
      total_ipi=KPIComparativoValor(
        atual=total_ipi_atual,
        anterior=total_ipi_anterior,
        variacao_percentual=self._calcular_variacao_percentual(
          total_ipi_atual, total_ipi_anterior
        ),
      ),
      total_pis=KPIComparativoValor(
        atual=total_pis_atual,
        anterior=total_pis_anterior,
        variacao_percentual=self._calcular_variacao_percentual(
          total_pis_atual, total_pis_anterior
        ),
      ),
      total_cofins=KPIComparativoValor(
        atual=total_cofins_atual,
        anterior=total_cofins_anterior,
        variacao_percentual=self._calcular_variacao_percentual(
          total_cofins_atual, total_cofins_anterior
        ),
      ),
    )
