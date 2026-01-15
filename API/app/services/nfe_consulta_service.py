import logging
from typing import List, Optional
from decimal import Decimal

import psycopg

from app.models.schemas import (
  KPIComparativoQuantidade,
  KPIComparativoValor,
  KPIsComparativo,
  NFeKPI,
  NFeKPIConsulta,
)
from app.services.empresa_service import normalizar_cnpj
from app.services.postres_config import carregar_config_postgres

logger = logging.getLogger("NFeConsultaService")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
formatter = logging.Formatter(
  "[%(asctime)s] [%(levelname)s] %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

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
    
  def _filtro_vendas(self) -> str:
    return """
      EXISTS (
        SELECT 1
        FROM public.nfe_notas AS n
        JOIN public.nfe_itens AS i
          ON i.nota_id = n.id
        JOIN public.cfops AS c
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

    if emitente_cnpj:
      filtros.append(
        "regexp_replace(emitente_cnpj, '\\\\D', '', 'g') = %s"
      )
      parametros.append(normalizar_cnpj(emitente_cnpj))

    where_clause = ""
    if filtros:
      where_clause = "WHERE " + " AND ".join(filtros)

    sql = f"""
      SELECT
        periodo_ano,
        periodo_mes
      FROM public.nfe_kpis AS k
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

  def _buscar_kpi_periodo(
    self,
    periodo_ano: int,
    periodo_mes: int,
    emitente_cnpj: Optional[str] = None,
  ) -> Optional[NFeKPI]:
    filtros = ["k.periodo_ano = %s", "k.periodo_mes = %s"]
    parametros: List[object] = [periodo_ano, periodo_mes]

    if emitente_cnpj:
      filtros.append(
        "regexp_replace(k.emitente_cnpj, '\\\\D', '', 'g') = %s"
      )
      parametros.append(normalizar_cnpj(emitente_cnpj))

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
      FROM public.nfe_kpis AS k
      LEFT JOIN public.nfe_processamentos AS p
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
      top_cidades=row[14] or [],
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

    if emitente_cnpj:
      filtros.append(
        "regexp_replace(k.emitente_cnpj, '\\\\D', '', 'g') = %s"
      )
      parametros.append(normalizar_cnpj(emitente_cnpj))

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
      FROM public.nfe_kpis AS k
      {where_clause}
      ORDER BY k.periodo_ano DESC, k.periodo_mes DESC, k.id DESC
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
              top_cidades=row[16] or [],
            ),
          )
        )

      return resultados
    except Exception:
        logger.exception("Erro ao consultar KPIs NFe")
        raise
      
  def comparar_kpis_mensal(
    self,
    periodo_ano: int,
    periodo_mes: int,
    emitente_cnpj: Optional[str] = None,
  ) -> Optional[KPIsComparativo]:
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

    if not kpi_atual or not kpi_anterior:
      return None

    total_vendas_atual = Decimal(kpi_atual.total_vendas)
    total_vendas_anterior = Decimal(kpi_anterior.total_vendas)
    ticket_medio_atual = Decimal(kpi_atual.ticket_medio)
    ticket_medio_anterior = Decimal(kpi_anterior.ticket_medio)
    maior_nota_atual = Decimal(kpi_atual.maior_nota)
    maior_nota_anterior = Decimal(kpi_anterior.maior_nota)
    menor_nota_atual = Decimal(kpi_atual.menor_nota)
    menor_nota_anterior = Decimal(kpi_anterior.menor_nota)
    total_icms_atual = Decimal(kpi_atual.total_icms)
    total_icms_anterior = Decimal(kpi_anterior.total_icms)
    total_ipi_atual = Decimal(kpi_atual.total_ipi)
    total_ipi_anterior = Decimal(kpi_anterior.total_ipi)
    total_pis_atual = Decimal(kpi_atual.total_pis)
    total_pis_anterior = Decimal(kpi_anterior.total_pis)
    total_cofins_atual = Decimal(kpi_atual.total_cofins)
    total_cofins_anterior = Decimal(kpi_anterior.total_cofins)

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
        anterior=kpi_anterior.quantidade_notas,
        variacao_percentual=self._calcular_variacao_percentual(
          Decimal(kpi_atual.quantidade_notas),
          Decimal(kpi_anterior.quantidade_notas),
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