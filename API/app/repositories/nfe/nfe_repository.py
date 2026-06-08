from __future__ import annotations

import psycopg

from app.services.fiscal.fiscal_sales import obter_cfops_faturamento_venda


class NFeRepository:
  """Consultas SQL usadas pelo NFeNotasService."""

  def _fetchall(self, cursor_or_conn, sql: str, params: tuple | list) -> list[tuple]:
    if hasattr(cursor_or_conn, "execute") and not hasattr(cursor_or_conn, "cursor"):
      cursor_or_conn.execute(sql, params)
      return cursor_or_conn.fetchall()

    with cursor_or_conn.cursor() as cur:
      cur.execute(sql, params)
      return cur.fetchall()

  def _rowcount(self, cursor_or_conn, sql: str, params: tuple | list) -> int:
    if hasattr(cursor_or_conn, "execute") and not hasattr(cursor_or_conn, "cursor"):
      cursor_or_conn.execute(sql, params)
      return cursor_or_conn.rowcount

    with cursor_or_conn.cursor() as cur:
      cur.execute(sql, params)
      return cur.rowcount

  def obter_cfops_venda(self, conn) -> list[tuple[str]]:
    sql = """
      SELECT c.codigo
      FROM public.notas_cfops AS c
      WHERE LEFT(
              regexp_replace(COALESCE(c.codigo, ''), '\\D', '', 'g'),
              1
            ) IN ('5','6','7')
        AND COALESCE(c.descricao, '') ILIKE 'venda%%';
    """

    return self._fetchall(conn, sql, ())

  def registrar_notas(self, cur: psycopg.Cursor, valores: list[tuple[object, ...]]) -> None:
    sql = """
      WITH atualizacao AS (
          UPDATE public.notas
          SET processamento_id = %s,
              natureza_operacao = %s,
              destinatario_documento = %s,
              destinatario_nome = %s,
              destinatario_cidade = %s,
              destinatario_uf = %s,
              valor_produtos = %s,
              valor_desconto = %s,
              valor_frete = %s,
              valor_icms = %s,
              valor_ipi = %s,
              valor_pis = %s,
              valor_cofins = %s,
              valor_total_nf = %s
          WHERE numero_nf = %s
            AND emitente_cnpj = %s
            AND COALESCE(modelo, '') = COALESCE(%s, '')
            AND data_emissao = %s
          RETURNING id
      )
      INSERT INTO public.notas (
          processamento_id,
          numero_nf,
          emitente_cnpj,
          modelo,
          data_emissao,
          natureza_operacao,
          destinatario_documento,
          destinatario_nome,
          destinatario_cidade,
          destinatario_uf,
          valor_produtos,
          valor_desconto,
          valor_frete,
          valor_icms,
          valor_ipi,
          valor_pis,
          valor_cofins,
          valor_total_nf
      ) SELECT
          %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s,
          %s, %s, %s,
          %s, %s, %s, %s, %s
      WHERE NOT EXISTS (SELECT 1 FROM atualizacao);
      """

    if hasattr(cur, "executemany") and not hasattr(cur, "cursor"):
      cur.executemany(sql, valores)
      return

    with cur.cursor() as cursor:
      cursor.executemany(sql, valores)

  def listar_notas_periodo_para_kpi(
    self,
    conn,
    cnpj_emitente: str,
    periodo_ano: int,
    periodo_mes: int,
  ) -> list[tuple]:
    sql = """
      SELECT
          id,
          numero_nf,
          emitente_cnpj,
          modelo,
          data_emissao,
          natureza_operacao,
          destinatario_documento,
          destinatario_nome,
          destinatario_cidade,
          destinatario_uf,
          valor_total_nf,
          valor_icms,
          valor_ipi,
          valor_pis,
          valor_cofins,
          valor_produtos,
          valor_desconto,
          valor_frete
      FROM public.notas
      WHERE emitente_cnpj = %s
        AND EXTRACT(YEAR FROM data_emissao) = %s
        AND EXTRACT(MONTH FROM data_emissao) = %s
      ORDER BY data_emissao, numero_nf;
    """

    return self._fetchall(conn, sql, (cnpj_emitente, periodo_ano, periodo_mes))

  def listar_itens_por_nota_ids_para_kpi(
    self,
    conn,
    cnpj_emitente: str,
    nota_ids: list[int],
  ) -> list[tuple]:
    sql = """
      SELECT
          id,
          nota_id,
          item_numero,
          produto_codigo,
          descricao,
          ncm,
          cfop,
          quantidade,
          valor_unitario,
          valor_total
      FROM public.notas_itens
      WHERE cnpj = %s
        AND nota_id = ANY(%s)
      ORDER BY nota_id, item_numero;
    """

    return self._fetchall(conn, sql, (cnpj_emitente, nota_ids))

  def montar_filtros_periodo_operacao(
    self,
    cnpj_empresa: str,
    periodo_ano: int,
    periodo_mes: int | None,
    tipo_operacao: str,
    cfops_faturamento: list[str] | None = None,
  ) -> tuple[str, list[object]]:
    filtros = ["EXTRACT(YEAR FROM n.data_emissao) = %s"]
    parametros: list[object] = [periodo_ano]

    if periodo_mes is not None:
      filtros.append("EXTRACT(MONTH FROM n.data_emissao) = %s")
      parametros.append(periodo_mes)

    if tipo_operacao == "compras":
      filtros.extend([
        "("
        "regexp_replace(COALESCE(n.destinatario_documento, ''), '\\D', '', 'g') = %s "
        "OR regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g') = %s"
        ")",
        "LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('1','2','3')",
      ])
      parametros.extend([cnpj_empresa, cnpj_empresa])
    elif tipo_operacao == "vendas":
      filtros.extend([
        "regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g') = %s",
        "regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g') = ANY(%s)",
      ])
      parametros.extend([
        cnpj_empresa,
        cfops_faturamento if cfops_faturamento is not None else obter_cfops_faturamento_venda(),
      ])
    else:
      filtros.append(
        "("
        "regexp_replace(COALESCE(n.destinatario_documento, ''), '\\D', '', 'g') = %s "
        "OR regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g') = %s"
        ")"
      )
      parametros.extend([cnpj_empresa, cnpj_empresa])

    return " AND ".join(filtros), parametros

  def listar_notas_periodo_para_operacao(
    self,
    conn,
    cnpj_empresa: str,
    periodo_ano: int,
    periodo_mes: int | None,
    tipo_operacao: str,
    cfops_faturamento: list[str] | None = None,
  ) -> list[tuple]:
    where_clause, parametros = self.montar_filtros_periodo_operacao(
      cnpj_empresa=cnpj_empresa,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      tipo_operacao=tipo_operacao,
      cfops_faturamento=cfops_faturamento,
    )

    sql = f"""
      SELECT DISTINCT
          n.id,
          n.numero_nf,
          n.emitente_cnpj,
          n.modelo,
          n.data_emissao,
          n.natureza_operacao,
          n.destinatario_documento,
          n.destinatario_nome,
          n.destinatario_cidade,
          n.destinatario_uf,
          n.valor_total_nf,
          n.valor_icms,
          n.valor_ipi,
          n.valor_pis,
          n.valor_cofins,
          n.valor_produtos,
          n.valor_desconto,
          n.valor_frete
      FROM public.notas AS n
      JOIN public.notas_itens AS i
        ON i.nota_id = n.id
      WHERE {where_clause}
      ORDER BY n.data_emissao, n.numero_nf;
    """

    return self._fetchall(conn, sql, tuple(parametros))

  def listar_itens_por_nota_ids_para_operacao(self, conn, nota_ids: list[int]) -> list[tuple]:
    sql = """
      SELECT
          id,
          nota_id,
          item_numero,
          produto_codigo,
          descricao,
          ncm,
          cfop,
          quantidade,
          valor_unitario,
          valor_total
      FROM public.notas_itens
      WHERE nota_id = ANY(%s)
      ORDER BY nota_id, item_numero;
    """

    return self._fetchall(conn, sql, (nota_ids,))

  def listar_tributos_itens(self, conn, item_ids: list[int]) -> list[tuple]:
    sql = """
      SELECT
          it.nota_item_id,
          t.codigo,
          t.nome,
          it.base_calculo,
          it.aliquota,
          it.valor_debito,
          it.valor_credito,
          it.valor_tributo,
          it.natureza,
          it.origem,
          it.status
      FROM public.itens_documentos_fiscais_tributos AS it
      JOIN public.tributos AS t
        ON t.id = it.tributo_id
      WHERE it.nota_item_id = ANY(%s)
      ORDER BY it.nota_item_id, t.codigo;
    """

    return self._fetchall(conn, sql, (item_ids,))

  def remover_notas_sem_cfop_venda(self, conn, processamento_id: int) -> int:
    sql = """
      DELETE FROM public.notas AS n
      WHERE n.processamento_id = %s
        AND COALESCE(n.modelo, '') <> 'NFSE'
        AND NOT EXISTS (
          SELECT 1
          FROM public.notas_itens AS i
          LEFT JOIN public.notas_cfops AS c
            ON regexp_replace(COALESCE(c.codigo, ''), '\\D', '', 'g')
               = regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g')
          WHERE i.nota_id = n.id
            AND (
                  (
                    LEFT(
                      regexp_replace(COALESCE(c.codigo, ''), '\\D', '', 'g'),
                      1
                    ) IN ('5','6','7')
                    AND COALESCE(c.descricao, '') ILIKE '%%venda%%'
                  )
                  OR LEFT(
                    regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'),
                    1
                  ) IN ('5','6','7')
                )
        );
    """

    return self._rowcount(conn, sql, (processamento_id,))
