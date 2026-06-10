from __future__ import annotations

import logging
from time import perf_counter
from decimal import Decimal
from typing import Optional

import psycopg


logger = logging.getLogger("repositories.nfe.consulta")
NFE_EMPRESA_JOIN = """
  LEFT JOIN public.empresas AS e
    ON regexp_replace(COALESCE(e.cnpj, ''), '\\D', '', 'g')
       = regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g')
"""

NFE_ESTADO_EXPR = "COALESCE(NULLIF(TRIM(n.destinatario_uf), ''), NULLIF(TRIM(e.estado), ''), 'Sem UF')"
NFE_CIDADE_EXPR = "COALESCE(NULLIF(TRIM(n.destinatario_cidade), ''), NULLIF(TRIM(e.cidade), ''), 'Cidade nao identificada')"


class NFeConsultaRepository:
  """Consultas de leitura usadas pelo service analitico de NFe."""

  def __init__(self, conn_params: dict) -> None:
    self.conn_params = conn_params

  def obter_cnpj_por_email(self, email: str) -> Optional[str]:
    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        inicio = perf_counter()
        cur.execute(
          """
          SELECT cnpj
          FROM public.login
          WHERE email = %s;
          """,
          (email,),
        )
        row = cur.fetchone()

    return row[0] if row and row[0] else None

  def obter_total_vendas_itens(self, where_clause: str, parametros: list[object]) -> Decimal:
    return self.obter_total_itens(where_clause, parametros, "total_vendido")

  def obter_total_itens(
    self,
    where_clause: str,
    parametros: list[object],
    alias_total: str,
  ) -> Decimal:
    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        inicio = perf_counter()
        cur.execute(
          f"""
          SELECT COALESCE(SUM(i.valor_total), 0) AS {alias_total}
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          """,
          parametros,
        )
        row = cur.fetchone()
        logger.info(
          "SQL obter_total_itens alias=%s linha=%s tempo=%.3fs parametros=%s",
          alias_total,
          1 if row else 0,
          perf_counter() - inicio,
          parametros,
        )

    return row[0] if row else Decimal("0.00")

  def listar_fornecedores_compras_por_valor(
    self,
    where_clause: str,
    parametros_com_limite: list[object],
  ) -> list[tuple]:
    return self._listar_fornecedores_compras(
      where_clause,
      parametros_com_limite,
      "2 DESC, 1 ASC",
    )

  def listar_fornecedores_compras_por_quantidade(
    self,
    where_clause: str,
    parametros_com_limite: list[object],
  ) -> list[tuple]:
    return self._listar_fornecedores_compras(
      where_clause,
      parametros_com_limite,
      "3 DESC, 2 DESC, 1 ASC",
    )

  def _listar_fornecedores_compras(
    self,
    where_clause: str,
    parametros_com_limite: list[object],
    order_by: str,
  ) -> list[tuple]:
    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        inicio = perf_counter()
        cur.execute(
          f"""
          SELECT
            COALESCE(NULLIF(TRIM(n.emitente_cnpj), ''), 'Fornecedor nÃ£o identificado') AS fornecedor,
            COALESCE(SUM(i.valor_total), 0) AS valor_total,
            COUNT(DISTINCT n.id) AS quantidade_documentos
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY {order_by}
          LIMIT %s
          """,
          parametros_com_limite,
        )
        rows = cur.fetchall()
        logger.info(
          "SQL listar_fornecedores_compras order_by=%s linhas=%s tempo=%.3fs parametros=%s",
          order_by,
          len(rows),
          perf_counter() - inicio,
          parametros_com_limite,
        )
        return rows

  def listar_produtos_compras_por_valor(
    self,
    where_clause: str,
    parametros_com_limite: list[object],
  ) -> list[tuple]:
    return self._listar_produtos_por_ordem(
      where_clause,
      parametros_com_limite,
      "2 DESC, 1 ASC",
    )

  def listar_produtos_compras_por_quantidade(
    self,
    where_clause: str,
    parametros_com_limite: list[object],
  ) -> list[tuple]:
    return self._listar_produtos_por_ordem(
      where_clause,
      parametros_com_limite,
      "3 DESC, 2 DESC, 1 ASC",
    )

  def listar_clientes_vendas_por_valor(
    self,
    where_clause: str,
    parametros_com_limite: list[object],
  ) -> list[tuple]:
    return self._listar_clientes_vendas(
      where_clause,
      parametros_com_limite,
      "2 DESC, 1 ASC",
    )

  def listar_clientes_vendas_por_quantidade(
    self,
    where_clause: str,
    parametros_com_limite: list[object],
  ) -> list[tuple]:
    return self._listar_clientes_vendas(
      where_clause,
      parametros_com_limite,
      "3 DESC, 2 DESC, 1 ASC",
    )

  def _listar_clientes_vendas(
    self,
    where_clause: str,
    parametros_com_limite: list[object],
    order_by: str,
  ) -> list[tuple]:
    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        inicio = perf_counter()
        cur.execute(
          f"""
          SELECT
            COALESCE(NULLIF(TRIM(n.destinatario_nome), ''), 'Cliente nÃ£o identificado') AS cliente,
            COALESCE(SUM(i.valor_total), 0) AS valor_total,
            COUNT(DISTINCT n.id) AS quantidade_documentos
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY {order_by}
          LIMIT %s
          """,
          parametros_com_limite,
        )
        rows = cur.fetchall()
        logger.info(
          "SQL listar_produtos order_by=%s linhas=%s tempo=%.3fs parametros=%s",
          order_by,
          len(rows),
          perf_counter() - inicio,
          parametros_com_limite,
        )
        return rows

  def listar_produtos_vendas_por_valor(
    self,
    where_clause: str,
    parametros_com_limite: list[object],
  ) -> list[tuple]:
    return self._listar_produtos_por_ordem(
      where_clause,
      parametros_com_limite,
      "2 DESC, 1 ASC",
    )

  def listar_produtos_vendas_por_quantidade(
    self,
    where_clause: str,
    parametros_com_limite: list[object],
  ) -> list[tuple]:
    return self._listar_produtos_por_ordem(
      where_clause,
      parametros_com_limite,
      "3 DESC, 2 DESC, 1 ASC",
    )

  def _listar_produtos_por_ordem(
    self,
    where_clause: str,
    parametros_com_limite: list[object],
    order_by: str,
  ) -> list[tuple]:
    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        inicio = perf_counter()
        cur.execute(
          f"""
          SELECT
            COALESCE(NULLIF(TRIM(i.descricao), ''), 'Produto nÃ£o identificado') AS produto,
            COALESCE(SUM(i.valor_total), 0) AS valor_total,
            COALESCE(SUM(i.quantidade), 0) AS quantidade_total
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY {order_by}
          LIMIT %s
          """,
          parametros_com_limite,
        )
        rows = cur.fetchall()
        logger.info(
          "SQL listar_produtos_compras linhas=%s tempo=%.3fs parametros=%s",
          len(rows),
          perf_counter() - inicio,
          parametros_com_limite,
        )
        return rows

  def listar_cfops_vendas(
    self,
    where_clause: str,
    parametros_com_limite: list[object],
  ) -> list[tuple]:
    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        inicio = perf_counter()
        cur.execute(
          f"""
          SELECT
            COALESCE(NULLIF(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), ''), '0000') AS cfop,
            COALESCE(NULLIF(TRIM(c.descricao), ''), 'CFOP sem descriÃ§Ã£o') AS descricao,
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
          parametros_com_limite,
        )
        rows = cur.fetchall()
        logger.info(
          "SQL listar_cfops_vendas linhas=%s tempo=%.3fs parametros=%s",
          len(rows),
          perf_counter() - inicio,
          parametros_com_limite,
        )
        return rows

  def listar_cidades_vendas(
    self,
    where_clause: str,
    parametros_com_limite: list[object],
  ) -> list[tuple]:
    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        inicio = perf_counter()
        cur.execute(
          f"""
          SELECT
            {NFE_CIDADE_EXPR} AS cidade,
            {NFE_ESTADO_EXPR} AS uf,
            COALESCE(SUM(i.valor_total), 0) AS valor_total,
            COUNT(DISTINCT n.id) AS quantidade_documentos
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          {NFE_EMPRESA_JOIN}
          WHERE {where_clause}
          GROUP BY 1, 2
          ORDER BY 3 DESC, 1 ASC
          LIMIT %s
          """,
          parametros_com_limite,
        )
        rows = cur.fetchall()
        logger.info(
          "SQL listar_cidades_vendas linhas=%s tempo=%.3fs parametros=%s",
          len(rows),
          perf_counter() - inicio,
          parametros_com_limite,
        )
        return rows

  def listar_regioes_vendas(
    self,
    where_clause: str,
    parametros: list[object],
  ) -> list[tuple]:
    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        inicio = perf_counter()
        cur.execute(
          f"""
          SELECT
            {NFE_ESTADO_EXPR} AS uf,
            COALESCE(SUM(i.valor_total), 0) AS valor_total,
            COUNT(DISTINCT n.id) AS quantidade_documentos
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          {NFE_EMPRESA_JOIN}
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC, 1 ASC
          """,
          parametros,
        )
        rows = cur.fetchall()
        logger.info(
          "SQL listar_regioes_vendas linhas=%s tempo=%.3fs parametros=%s",
          len(rows),
          perf_counter() - inicio,
          parametros,
        )
        return rows

  def criar_tmp_fiscal_hierarquia_base(
    self,
    cur: psycopg.Cursor,
    where_clause: str,
    parametros: list[object],
  ) -> None:
    cur.execute("DROP TABLE IF EXISTS tmp_nfe_fiscal_hierarquia_base")
    cur.execute(
      f"""
      CREATE TEMP TABLE tmp_nfe_fiscal_hierarquia_base ON COMMIT DROP AS
      WITH tributos_item AS (
        SELECT
          nota_item_id,
          COALESCE(
            NULLIF(SUM(valor_tributo), 0),
            SUM(valor_debito) - SUM(valor_credito),
            0
          ) AS imposto_valor
        FROM public.itens_documentos_fiscais_tributos
        WHERE nota_item_id IS NOT NULL
        GROUP BY nota_item_id
      ),
      itens_filtrados AS (
        SELECT
          n.id AS documento_id,
          i.id AS item_id,
          {NFE_ESTADO_EXPR} AS estado,
          {NFE_CIDADE_EXPR} AS cidade,
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
        {NFE_EMPRESA_JOIN}
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
          COALESCE(
            tributos.imposto_valor,
            CASE
              WHEN COALESCE(rateio.faturamento_total_nota, 0) > 0 THEN
                (itens.faturamento / rateio.faturamento_total_nota) * rateio.imposto_total_nota
              ELSE 0::numeric
            END
          ) AS imposto_valor
        FROM itens_filtrados AS itens
        JOIN notas_rateio AS rateio
          ON rateio.documento_id = itens.documento_id
        LEFT JOIN tributos_item AS tributos
          ON tributos.nota_item_id = itens.item_id
        LEFT JOIN public.ncm_catalogo AS nc
          ON regexp_replace(COALESCE(nc.codigo, ''), '\\D', '', 'g')
             = COALESCE(NULLIF(itens.ncm_codigo, ''), '00000000')
      )
      SELECT *
      FROM base
      """,
      parametros,
    )
    cur.execute("ANALYZE tmp_nfe_fiscal_hierarquia_base")

  def obter_resumo_fiscal_hierarquia(self, cur: psycopg.Cursor) -> tuple:
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
    return cur.fetchone()

  def listar_hierarquia_fiscal_completa(
    self,
    cur: psycopg.Cursor,
    limite: int,
  ) -> list[tuple]:
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
      (limite,),
    )
    return cur.fetchall()

  def contar_estados_fiscal_hierarquia(self, cur: psycopg.Cursor) -> int:
    cur.execute("SELECT COUNT(DISTINCT estado) FROM tmp_nfe_fiscal_hierarquia_base")
    row = cur.fetchone()
    return (row[0] if row else 0) or 0

  def listar_estados_fiscal_hierarquia(
    self,
    cur: psycopg.Cursor,
    limite: int,
    offset: int,
  ) -> list[tuple]:
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
      (limite, offset),
    )
    return cur.fetchall()

  def contar_cidades_fiscal_hierarquia(self, cur: psycopg.Cursor) -> int:
    cur.execute("SELECT COUNT(DISTINCT CONCAT(cidade, '::', estado)) FROM tmp_nfe_fiscal_hierarquia_base")
    row = cur.fetchone()
    return (row[0] if row else 0) or 0

  def listar_cidades_fiscal_hierarquia(
    self,
    cur: psycopg.Cursor,
    limite: int,
    offset: int,
  ) -> list[tuple]:
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
      (limite, offset),
    )
    return cur.fetchall()

  def contar_ncms_fiscal_hierarquia(self, cur: psycopg.Cursor) -> int:
    cur.execute("SELECT COUNT(DISTINCT ncm) FROM tmp_nfe_fiscal_hierarquia_base")
    row = cur.fetchone()
    return (row[0] if row else 0) or 0

  def listar_ncms_fiscal_hierarquia(
    self,
    cur: psycopg.Cursor,
    limite: int,
    offset: int,
  ) -> list[tuple]:
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
      (limite, offset),
    )
    return cur.fetchall()

  def contar_produtos_fiscal_hierarquia(self, cur: psycopg.Cursor) -> int:
    cur.execute("SELECT COUNT(DISTINCT CONCAT(produto_codigo, '::', produto_descricao)) FROM tmp_nfe_fiscal_hierarquia_base")
    row = cur.fetchone()
    return (row[0] if row else 0) or 0

  def listar_produtos_fiscal_hierarquia(
    self,
    cur: psycopg.Cursor,
    limite: int,
    offset: int,
  ) -> list[tuple]:
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
      (limite, offset),
    )
    return cur.fetchall()

  def listar_totais_vendas_mensais(
    self,
    where_clause: str,
    parametros: list[object],
  ) -> list[tuple[int, Decimal]]:
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
        return cur.fetchall()

  def listar_totais_vendas_por_periodo(
    self,
    cnpj_emitente: str,
    cfops_faturamento: list[str],
    anos: list[int],
  ) -> list[tuple[int, int, Decimal]]:
    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(
          """
          SELECT
            EXTRACT(YEAR FROM n.data_emissao)::int AS periodo_ano,
            EXTRACT(MONTH FROM n.data_emissao)::int AS periodo_mes,
            COALESCE(SUM(i.valor_total), 0) AS total_vendido
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g') = %s
            AND regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g') = ANY(%s)
            AND EXTRACT(YEAR FROM n.data_emissao)::int = ANY(%s)
          GROUP BY 1, 2
          """,
          (cnpj_emitente, cfops_faturamento, anos),
        )
        return cur.fetchall()

  def obter_ultimo_periodo(self, where_clause: str, parametros: list[object]) -> Optional[tuple[int, int]]:
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

    return (row[0], row[1]) if row else None

  def listar_periodos_disponiveis(
    self,
    where_clause: str,
    parametros: list[object],
  ) -> list[tuple[int, int]]:
    sql = f"""
      SELECT
        periodo_ano,
        periodo_mes
      FROM public.notas_kpis AS k
      {where_clause}
      ORDER BY periodo_ano DESC, periodo_mes DESC, id DESC
      LIMIT %s;
    """

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(sql, parametros)
        return cur.fetchall()

  def buscar_kpi_periodo(self, where_clause: str, parametros: list[object]) -> Optional[tuple]:
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
        return cur.fetchone()

  def listar_kpis(self, where_clause: str, parametros: list[object]) -> list[tuple]:
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

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        inicio = perf_counter()
        cur.execute(sql_kpis, parametros)
        rows = cur.fetchall()
        logger.info(
          "SQL listar_kpis linhas=%s tempo=%.3fs parametros=%s",
          len(rows),
          perf_counter() - inicio,
          parametros,
        )
        return rows

  def obter_totais_clientes(
    self,
    where_clause: str,
    parametros: list[object],
  ) -> tuple[Decimal, int]:
    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(
          f"""
          SELECT
            COALESCE(SUM(i.valor_total), 0) AS total_vendido,
            COUNT(DISTINCT COALESCE(NULLIF(TRIM(n.destinatario_nome), ''), 'Cliente nÃ£o identificado')) AS total_clientes
          FROM public.notas AS n
          JOIN public.notas_itens AS i
            ON i.nota_id = n.id
          WHERE {where_clause}
          """,
          parametros,
        )
        row = cur.fetchone()

    return (
      row[0] if row else Decimal("0.00"),
      row[1] if row else 0,
    )

  def listar_clientes_por_valor(
    self,
    where_clause: str,
    parametros: list[object],
    total_vendido: Decimal,
    limite: Optional[int],
  ) -> list[tuple]:
    return self._listar_ranking_clientes(
      where_clause=where_clause,
      parametros=parametros,
      total_vendido=total_vendido,
      limite=limite,
      order_by="valor_total DESC, cliente ASC",
    )

  def listar_clientes_por_quantidade(
    self,
    where_clause: str,
    parametros: list[object],
    total_vendido: Decimal,
    limite: Optional[int],
  ) -> list[tuple]:
    return self._listar_ranking_clientes(
      where_clause=where_clause,
      parametros=parametros,
      total_vendido=total_vendido,
      limite=limite,
      order_by="quantidade_documentos DESC, valor_total DESC, cliente ASC",
    )

  def _listar_ranking_clientes(
    self,
    where_clause: str,
    parametros: list[object],
    total_vendido: Decimal,
    limite: Optional[int],
    order_by: str,
  ) -> list[tuple]:
    total_base = total_vendido or Decimal("0.00")
    parametros_ranking = [total_base, total_base, *parametros, limite]

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
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
              COALESCE(NULLIF(TRIM(n.destinatario_nome), ''), 'Cliente nÃ£o identificado') AS cliente,
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
          ORDER BY {order_by}
          LIMIT %s
          """,
          parametros_ranking,
        )
        return cur.fetchall()

  def filtro_vendas_kpis(self) -> str:
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
