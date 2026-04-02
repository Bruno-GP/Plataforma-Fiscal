import logging
from typing import List, Optional
from decimal import Decimal

import psycopg

from app.models.nfe.schemas import (
  KPIComparativoQuantidade,
  KPIComparativoValor,
  KPIsComparativo,
  NFeKPI,
  NFeKPIConsulta,
)
from app.services.nfe.empresa_service import normalizar_cnpj
from app.services.nfe.postres_config import carregar_config_postgres

logger = logging.getLogger("NFeConsultaService")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
formatter = logging.Formatter(
  "[%(asctime)s] [%(levelname)s] %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

UF_PARA_REGIAO = {
  "AC": "Norte", "AL": "Nordeste", "AP": "Norte", "AM": "Norte", "BA": "Nordeste",
  "CE": "Nordeste", "DF": "Centro-Oeste", "ES": "Sudeste", "GO": "Centro-Oeste",
  "MA": "Nordeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste", "MG": "Sudeste",
  "PA": "Norte", "PB": "Nordeste", "PR": "Sul", "PE": "Nordeste", "PI": "Nordeste",
  "RJ": "Sudeste", "RN": "Nordeste", "RS": "Sul", "RO": "Norte", "RR": "Norte",
  "SC": "Sul", "SP": "Sudeste", "SE": "Nordeste", "TO": "Norte",
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

  def _obter_regiao_por_uf(self, uf: object) -> str | None:
    uf_normalizada = str(uf or "").strip().upper()
    return UF_PARA_REGIAO.get(uf_normalizada)

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

    return " AND ".join(filtros_docs), parametros

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

  def _categoria_fiscal_case(self) -> str:
    return """
      CASE
        WHEN COALESCE(c.descricao, n.natureza_operacao, '') ILIKE '%%devol%%' THEN 'Devolução'
        WHEN COALESCE(c.descricao, n.natureza_operacao, '') ILIKE '%%bonific%%'
          OR COALESCE(c.descricao, n.natureza_operacao, '') ILIKE '%%brinde%%'
          OR COALESCE(c.descricao, n.natureza_operacao, '') ILIKE '%%doaç%%'
          OR COALESCE(c.descricao, n.natureza_operacao, '') ILIKE '%%doac%%' THEN 'Bonificação'
        WHEN COALESCE(c.descricao, n.natureza_operacao, '') ILIKE '%%remessa%%'
          OR COALESCE(c.descricao, n.natureza_operacao, '') ILIKE '%%demonstra%%'
          OR COALESCE(c.descricao, n.natureza_operacao, '') ILIKE '%%conserto%%'
          OR COALESCE(c.descricao, n.natureza_operacao, '') ILIKE '%%comodato%%'
          OR COALESCE(c.descricao, n.natureza_operacao, '') ILIKE '%%industrializa%%' THEN 'Remessa'
        WHEN COALESCE(c.descricao, n.natureza_operacao, '') ILIKE '%%transfer%%' THEN 'Transferência'
        WHEN COALESCE(c.descricao, n.natureza_operacao, '') ILIKE '%%substitui%%'
          OR COALESCE(c.descricao, n.natureza_operacao, '') ILIKE '%%subst. trib%%'
          OR COALESCE(c.descricao, n.natureza_operacao, '') ILIKE '%%st%%' THEN 'Substituição Tributária'
        WHEN LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('5','6','7')
          AND COALESCE(c.descricao, n.natureza_operacao, '') ILIKE 'venda%%' THEN 'Venda'
        ELSE 'Outras operações'
      END
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
          regiao = self._obter_regiao_por_uf(uf)
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

    filtros_docs = [
      "regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g') = %s",
    ]
    parametros: list[object] = [cnpj_filtrado]

    if periodo_ano:
      filtros_docs.append("EXTRACT(YEAR FROM n.data_emissao) = %s")
      parametros.append(periodo_ano)

    if periodo_mes:
      filtros_docs.append("EXTRACT(MONTH FROM n.data_emissao) = %s")
      parametros.append(periodo_mes)

    where_clause = " AND ".join(filtros_docs)
    categoria_case = self._categoria_fiscal_case()

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(
          f"""
          SELECT
            COALESCE(SUM(i.valor_total), 0) AS total_movimentado,
            COUNT(DISTINCT n.id) AS quantidade_documentos,
            COUNT(DISTINCT regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g')) AS quantidade_cfops
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          """,
          parametros,
        )
        resumo_row = cur.fetchone()
        total_movimentado = resumo_row[0] if resumo_row else Decimal("0.00")
        quantidade_documentos = resumo_row[1] if resumo_row else 0
        quantidade_cfops = resumo_row[2] if resumo_row else 0

        cur.execute(
          f"""
          SELECT
            {categoria_case} AS categoria,
            COALESCE(SUM(i.valor_total), 0) AS valor_total,
            COUNT(DISTINCT n.id) AS quantidade_documentos
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          LEFT JOIN public.notas_cfops AS c
            ON regexp_replace(COALESCE(c.codigo, ''), '\\D', '', 'g')
               = regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g')
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC, 1 ASC
          LIMIT %s
          """,
          [*parametros, limite],
        )
        top_categorias = [
          {
            "categoria": categoria,
            "valor_total": valor_total or Decimal("0.00"),
            "participacao_percentual": (
              ((valor_total or Decimal("0.00")) / total_movimentado) * Decimal("100")
              if total_movimentado
              else Decimal("0.00")
            ),
            "quantidade_documentos": quantidade_docs or 0,
          }
          for categoria, valor_total, quantidade_docs in cur.fetchall()
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
        top_cfops = [
          {
            "cfop": cfop,
            "descricao": descricao,
            "valor_total": valor_total or Decimal("0.00"),
            "participacao_percentual": (
              ((valor_total or Decimal("0.00")) / total_movimentado) * Decimal("100")
              if total_movimentado
              else Decimal("0.00")
            ),
          }
          for cfop, descricao, valor_total in cur.fetchall()
        ]

    return {
      "emitente_cnpj": cnpj_filtrado,
      "periodo_ano": periodo_ano,
      "periodo_mes": periodo_mes,
      "total_movimentado": total_movimentado or Decimal("0.00"),
      "quantidade_documentos": quantidade_documentos or 0,
      "quantidade_cfops": quantidade_cfops or 0,
      "top_categorias": top_categorias,
      "top_cfops": top_cfops,
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
