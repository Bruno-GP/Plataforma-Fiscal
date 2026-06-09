from __future__ import annotations

from decimal import Decimal
from typing import Optional

import psycopg

from app.domain.nfe.normalization import normalizar_nome_produto
from app.services.fiscal.fiscal_clients import construir_ranking_clientes
from app.services.fiscal.fiscal_purchases import construir_ranking_fornecedores_compras
from app.services.fiscal.fiscal_sales import (
  construir_ranking_cfops_vendas,
  construir_ranking_clientes_vendas,
  construir_ranking_cidades_vendas,
  construir_ranking_produtos_vendas,
  construir_ranking_regioes_vendas,
)


class SpedRepository:
  def __init__(self, conn_params: dict) -> None:
    self.conn_params = conn_params

  def _safe_scalar_query(self, sql: str, params: tuple[object, ...]) -> Decimal:
    try:
      with psycopg.connect(**self.conn_params) as conn:
        with conn.cursor() as cur:
          cur.execute(sql, params)
          row = cur.fetchone()
          return row[0] if row else Decimal("0.00")
    except psycopg.errors.UndefinedTable:
      return Decimal("0.00")

  def _safe_top_query(
    self,
    sql: str,
    params: tuple[object, ...],
    label: str,
  ) -> list[dict]:
    try:
      with psycopg.connect(**self.conn_params) as conn:
        with conn.cursor() as cur:
          cur.execute(sql, params)
          return [
            {label: nome, "valor_total": valor or Decimal("0.00")}
            for nome, valor in cur.fetchall()
          ]
    except psycopg.errors.UndefinedTable:
      return []

  def _safe_top_fornecedor_query(self, sql: str, params: tuple[object, ...]) -> list[dict]:
    try:
      with psycopg.connect(**self.conn_params) as conn:
        with conn.cursor() as cur:
          cur.execute(sql, params)
          return construir_ranking_fornecedores_compras(cur.fetchall())
    except psycopg.errors.UndefinedTable:
      return []

  def _safe_top_cliente_query(self, sql: str, params: tuple[object, ...]) -> list[dict]:
    try:
      with psycopg.connect(**self.conn_params) as conn:
        with conn.cursor() as cur:
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

  def _safe_top_produto_query(
    self,
    sql: str,
    params: tuple[object, ...],
    sort_by: str = "valor_total",
  ) -> list[dict]:
    try:
      with psycopg.connect(**self.conn_params) as conn:
        with conn.cursor() as cur:
          cur.execute(sql, params)
          agregados: dict[str, dict[str, Decimal]] = {}
          for produto, valor_total, quantidade_total in cur.fetchall():
            nome = normalizar_nome_produto(produto) or "Produto não identificado"
            item = agregados.setdefault(
              nome,
              {
                "produto": nome,
                "valor_total": Decimal("0.00"),
                "quantidade_total": Decimal("0.00"),
              },
            )
            item["valor_total"] += Decimal(valor_total or 0)
            item["quantidade_total"] += Decimal(quantidade_total or 0)

          chave_principal = "quantidade_total" if sort_by == "quantidade_total" else "valor_total"
          chave_secundaria = "valor_total" if chave_principal == "quantidade_total" else "quantidade_total"

          return sorted(
            agregados.values(),
            key=lambda item: (
              -item[chave_principal],
              -item[chave_secundaria],
              item["produto"],
            ),
          )
    except psycopg.errors.UndefinedTable:
      return []

  def _safe_top_cliente_analise_query(self, sql: str, params: tuple[object, ...]) -> list[dict]:
    try:
      with psycopg.connect(**self.conn_params) as conn:
        with conn.cursor() as cur:
          cur.execute(sql, params)
          return construir_ranking_clientes(cur.fetchall())
    except psycopg.errors.UndefinedTable:
      return []

  def validar_tabela_kpis(self) -> None:
    required_columns = {
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

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(
          """
          SELECT column_name
          FROM information_schema.columns
          WHERE table_schema = 'public'
            AND table_name = 'sped_kpis_fiscal'
          """
        )
        existing_columns = {str(row[0]) for row in cur.fetchall()}

    missing_columns = sorted(required_columns - existing_columns)
    if missing_columns:
      raise RuntimeError(
        "Tabela public.sped_kpis_fiscal incompleta ou ausente. Execute as migrations Alembic. "
        f"Colunas ausentes: {', '.join(missing_columns)}."
      )

  def listar_kpis(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: int = 100,
    offset: int = 0,
  ) -> list[tuple]:
    filtros = ["regexp_replace(cnpj_emitente, '\\D', '', 'g') = %s"]
    params: list[object] = [emitente_cnpj]

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

    self.validar_tabela_kpis()

    try:
      with psycopg.connect(**self.conn_params) as conn:
        with conn.cursor() as cur:
          cur.execute(sql_kpis, tuple(params))
          return cur.fetchall()
    except psycopg.errors.UndefinedTable:
      return []

  def top_clientes(self, cnpj: str, ano: int, mes: int) -> list[dict]:
    return self._safe_top_query(
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

  def top_cidades(self, cnpj: str, ano: int, mes: int) -> list[dict]:
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

    return self._safe_top_query(sql_cidades_sped, (cnpj, ano, mes), "cidade")

  def top_produtos(self, cnpj: str, ano: int, mes: int) -> list[dict]:
    return self._safe_top_query(
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

  def listar_clientes(
    self,
    where_clause: str,
    params: list[object],
    limite: Optional[int] = None,
    offset: int = 0,
  ) -> dict:
    total_vendas = self._safe_scalar_query(
      f"""
      SELECT COALESCE(SUM(d.valor_total), 0)
      FROM public.sped_documentos_fiscais d
      WHERE {where_clause}
      """,
      tuple(params),
    )

    ticket_medio = self._safe_scalar_query(
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

    clientes_rows: list[tuple] = []
    try:
      with psycopg.connect(**self.conn_params) as conn:
        with conn.cursor() as cur:
          cur.execute(sql_clientes, tuple(query_params))
          clientes_rows = cur.fetchall()
    except psycopg.errors.UndefinedTable:
      clientes_rows = []

    total_clientes = self._safe_scalar_query(
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

    return {
      "total_vendas": total_vendas,
      "ticket_medio": ticket_medio,
      "total_clientes": total_clientes,
      "clientes_rows": clientes_rows,
    }

  def analisar_compras(
    self,
    where_clause: str,
    params: list[object],
    limite: int = 5,
  ) -> dict:
    total_comprado = self._safe_scalar_query(
      f"""
      SELECT COALESCE(SUM(d.valor_total), 0)
      FROM public.sped_documentos_fiscais d
      WHERE {where_clause}
      """,
      tuple(params),
    )

    limite_params = tuple([*params, limite])
    top_fornecedores_valor = self._safe_top_fornecedor_query(
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
      limite_params,
    )

    top_fornecedores_quantidade = self._safe_top_fornecedor_query(
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
      limite_params,
    )

    top_produtos_valor = self._safe_top_produto_query(
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
      limite_params,
      sort_by="valor_total",
    )

    top_produtos_quantidade = self._safe_top_produto_query(
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
      limite_params,
      sort_by="quantidade_total",
    )

    return {
      "total_comprado": total_comprado,
      "top_fornecedores_valor": top_fornecedores_valor,
      "top_fornecedores_quantidade": top_fornecedores_quantidade,
      "top_produtos_valor": top_produtos_valor,
      "top_produtos_quantidade": top_produtos_quantidade,
    }

  def analisar_vendas(
    self,
    where_clause: str,
    params: list[object],
    limite: Optional[int] = None,
  ) -> dict:
    total_vendido = self._safe_scalar_query(
      f"""
      SELECT COALESCE(SUM(d.valor_total), 0)
      FROM public.sped_documentos_fiscais d
      WHERE {where_clause}
      """,
      tuple(params),
    )

    limite_params = tuple([*params, limite])
    top_clientes_valor = self._safe_top_cliente_query(
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
      limite_params,
    )

    top_clientes_quantidade = self._safe_top_cliente_query(
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
      limite_params,
    )

    top_produtos_valor = self._safe_top_produto_query(
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
      limite_params,
      sort_by="valor_total",
    )

    top_produtos_quantidade = self._safe_top_produto_query(
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
      limite_params,
      sort_by="quantidade_total",
    )

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
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
          tuple([*params, limite]),
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
          tuple([*params, limite]),
        )
        top_cidades_rows = cur.fetchall()

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
        top_regioes_rows = cur.fetchall()

    return {
      "total_vendido": total_vendido,
      "top_clientes_valor": top_clientes_valor,
      "top_clientes_quantidade": top_clientes_quantidade,
      "top_produtos_valor": top_produtos_valor,
      "top_produtos_quantidade": top_produtos_quantidade,
      "top_cfops_valor": top_cfops_valor,
      "top_regioes_rows": top_regioes_rows,
      "top_cidades_rows": top_cidades_rows,
    }

  def analisar_clientes(
    self,
    where_clause: str,
    params: list[object],
    limite: Optional[int] = None,
  ) -> dict:
    total_vendido = self._safe_scalar_query(
      f"""
      SELECT COALESCE(SUM(d.valor_total), 0)
      FROM public.sped_documentos_fiscais d
      WHERE {where_clause}
      """,
      tuple(params),
    )

    total_clientes = self._safe_scalar_query(
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

    ranking_params = [total_vendido, total_vendido, *params]
    if limite is not None:
      ranking_params.append(limite)

    top_clientes_valor = self._safe_top_cliente_analise_query(
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
          COALESCE(NULLIF(TRIM(p.nome), ''), 'Cliente não identificado') AS cliente,
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
      tuple(ranking_params),
    )

    top_clientes_quantidade = self._safe_top_cliente_analise_query(
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
          COALESCE(NULLIF(TRIM(p.nome), ''), 'Cliente não identificado') AS cliente,
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
      tuple(ranking_params),
    )

    return {
      "total_vendido": total_vendido,
      "total_clientes": total_clientes,
      "top_clientes_valor": top_clientes_valor,
      "top_clientes_quantidade": top_clientes_quantidade,
    }

  def analisar_fiscal_hierarquia(
    self,
    where_clause_documentos: str,
    where_clause_kpis: str,
    where_clause_base: str,
    params_kpis: list[object],
    params_cte: list[object],
    params_base: list[object],
    nivel_resolvido: str,
    limite_consulta: int,
    offset_consulta: int,
    modo_legado_hierarquia_completa: bool,
  ) -> dict:
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
              COALESCE(NULLIF(TRIM(regexp_replace(COALESCE(pr.ncm, ''), '\\D', '', 'g')), ''), '00000000') AS ncm,
              COALESCE(NULLIF(TRIM(nc.descricao), ''), 'NCM sem descricao') AS descricao_ncm,
              COALESCE(NULLIF(TRIM(pr.codigo), ''), 'SEM-CODIGO') AS produto_codigo,
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
                 = COALESCE(NULLIF(TRIM(regexp_replace(COALESCE(pr.ncm, ''), '\\D', '', 'g')), ''), '00000000')
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

        cur.execute(
          """
          SELECT COALESCE(SUM(faturamento), 0)
          FROM tmp_sped_fiscal_hierarquia_base
          """,
        )
        row_faturamento_periodo = cur.fetchone()
        total_faturamento_periodo = row_faturamento_periodo[0] if row_faturamento_periodo else Decimal("0.00")

        hierarquia_rows: list[tuple] = []
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
          hierarquia_rows = cur.fetchall()

        total_registros_nivel = 0
        itens_nivel_rows: list[tuple] = []
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
          itens_nivel_rows = cur.fetchall()
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
          itens_nivel_rows = cur.fetchall()
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
          itens_nivel_rows = cur.fetchall()
        else:
          cur.execute(
            "SELECT COUNT(DISTINCT CONCAT(produto_codigo, '::', produto_descricao)) FROM tmp_sped_fiscal_hierarquia_base_filtrada WHERE NOT sem_item_detalhado"
          )
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
          itens_nivel_rows = cur.fetchall()

    return {
      "total_impostos_periodo": total_impostos_periodo,
      "resumo_row": resumo_row,
      "total_faturamento_periodo": total_faturamento_periodo,
      "hierarquia_rows": hierarquia_rows,
      "total_registros_nivel": total_registros_nivel,
      "itens_nivel_rows": itens_nivel_rows,
      "nivel_resolvido": nivel_resolvido,
      "limite_consulta": limite_consulta,
      "offset_consulta": offset_consulta,
    }
