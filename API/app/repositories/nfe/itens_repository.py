from __future__ import annotations

from decimal import Decimal
from typing import Optional

import psycopg


class NFeItensRepository:
  def __init__(self, conn_params: dict) -> None:
    self.conn_params = conn_params

  def obter_nota_para_registrar_itens(
    self,
    cur: psycopg.Cursor,
    numero_nf: str,
    emitente_cnpj: str,
    modelo: str | None,
    data_emissao,
  ) -> Optional[tuple]:
    cur.execute(
      """
      SELECT
        n.id,
        p.empresa_id,
        p.cnpj_emitente
      FROM public.notas AS n
      JOIN public.notas_processamentos AS p
        ON p.id = n.processamento_id
      WHERE n.numero_nf = %s
        AND n.emitente_cnpj = %s
        AND COALESCE(n.modelo, '') = COALESCE(%s, '')
        AND n.data_emissao = %s
      LIMIT 1;
      """,
      (numero_nf, emitente_cnpj, modelo, data_emissao),
    )
    return cur.fetchone()

  def upsert_item_nota(
    self,
    cur: psycopg.Cursor,
    nota_id: int,
    empresa_id: int,
    cnpj: str,
    item_numero: int,
    produto_codigo: str,
    descricao: str,
    ncm: str,
    cfop: str,
    quantidade,
    valor_unitario,
    valor_total,
  ) -> Optional[tuple]:
    cur.execute(
      """
      WITH atualizacao AS (
          UPDATE public.notas_itens
          SET
              empresa_id = %s,
              cnpj = %s,
              descricao = %s,
              ncm = %s,
              cfop = %s,
              quantidade = %s,
              valor_unitario = %s,
              valor_total = %s
          WHERE nota_id = %s
            AND item_numero = %s
            AND produto_codigo = %s
          RETURNING id
      ),
      insercao AS (
      INSERT INTO public.notas_itens (
          nota_id,
          empresa_id,
          cnpj,
          item_numero,
          produto_codigo,
          descricao,
          ncm,
          cfop,
          quantidade,
          valor_unitario,
          valor_total
      )
      SELECT
          %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s,
          %s
      WHERE NOT EXISTS (SELECT 1 FROM atualizacao)
      RETURNING id
      )
      SELECT id FROM atualizacao
      UNION ALL
      SELECT id FROM insercao
      LIMIT 1;
      """,
      (
        empresa_id,
        cnpj,
        descricao,
        ncm,
        cfop,
        quantidade,
        valor_unitario,
        valor_total,
        nota_id,
        item_numero,
        produto_codigo,
        nota_id,
        empresa_id,
        cnpj,
        item_numero,
        produto_codigo,
        descricao,
        ncm,
        cfop,
        quantidade,
        valor_unitario,
        valor_total,
      ),
    )
    return cur.fetchone()

  def remover_tributos_reforma_item(self, cur: psycopg.Cursor, nota_item_id: int) -> None:
    cur.execute(
      """
      DELETE FROM public.itens_documentos_fiscais_tributos it
      USING public.tributos t
      WHERE it.tributo_id = t.id
        AND it.nota_item_id = %s
        AND t.codigo = ANY(%s)
      """,
      (nota_item_id, ["CBS", "IBS", "IBS_UF", "IBS_MUN", "IS"]),
    )

  def inserir_tributo_reforma_item(
    self,
    cur: psycopg.Cursor,
    nota_item_id: int,
    empresa_cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
    numero_item: int,
    produto_codigo: str,
    ncm_codigo: str | None,
    cfop: str,
    tributo: dict,
  ) -> None:
    cur.execute(
      """
      INSERT INTO public.itens_documentos_fiscais_tributos (
          nota_item_id,
          tributo_id,
          empresa_cnpj,
          periodo_ano,
          periodo_mes,
          numero_item,
          produto_codigo,
          ncm_codigo,
          cfop,
          cst_codigo,
          classificacao_tributaria,
          base_calculo,
          aliquota,
          valor_debito,
          valor_credito,
          valor_tributo,
          natureza,
          origem,
          status,
          observacoes
      )
      SELECT
          %s,
          t.id,
          %s,
          %s,
          %s,
          %s,
          %s,
          %s::char(8),
          %s,
          %s,
          %s,
          %s,
          %s,
          %s,
          0,
          %s,
          'debito',
          'xml',
          'ativo',
          'Tributo da Reforma Tributaria extraido do XML.'
      FROM public.tributos t
      WHERE t.codigo = %s
      """,
      (
        nota_item_id,
        empresa_cnpj,
        periodo_ano,
        periodo_mes,
        numero_item,
        produto_codigo,
        ncm_codigo,
        cfop,
        tributo.get("cst_codigo"),
        tributo.get("classificacao_tributaria"),
        tributo.get("base_calculo") or Decimal("0"),
        tributo.get("aliquota") or Decimal("0"),
        tributo.get("valor_tributo") or Decimal("0"),
        tributo.get("valor_tributo") or Decimal("0"),
        tributo.get("tributo_codigo"),
      ),
    )

  def ncm_catalogo_existe(self, cur: psycopg.Cursor, codigo_ncm: str) -> bool:
    cur.execute(
      "SELECT 1 FROM public.ncm_catalogo WHERE codigo = %s LIMIT 1",
      (codigo_ncm,),
    )
    return cur.fetchone() is not None

  def remover_documentos_reforma_agregados(
    self,
    cur: psycopg.Cursor,
    nota_ids: list[int],
    codigos_reforma: list[str],
  ) -> None:
    cur.execute(
      """
      DELETE FROM public.documentos_fiscais_tributos dt
      USING public.tributos t
      WHERE dt.tributo_id = t.id
        AND dt.nota_id = ANY(%s)
        AND t.codigo = ANY(%s)
      """,
      (nota_ids, codigos_reforma),
    )

  def registrar_documentos_reforma_agregados(
    self,
    cur: psycopg.Cursor,
    nota_ids: list[int],
    codigos_reforma: list[str],
  ) -> None:
    self.remover_documentos_reforma_agregados(cur, nota_ids, codigos_reforma)

    cur.execute(
      """
      WITH agregados AS (
          SELECT
              i.nota_id,
              it.tributo_id,
              it.empresa_cnpj,
              it.periodo_ano,
              it.periodo_mes,
              SUM(COALESCE(it.base_calculo, 0)) AS base_calculo,
              SUM(COALESCE(it.valor_debito, 0)) AS valor_debito,
              SUM(COALESCE(it.valor_credito, 0)) AS valor_credito,
              SUM(COALESCE(it.valor_tributo, 0)) AS valor_tributo
          FROM public.itens_documentos_fiscais_tributos it
          JOIN public.notas_itens i ON i.id = it.nota_item_id
          JOIN public.tributos t ON t.id = it.tributo_id
          WHERE i.nota_id = ANY(%s)
            AND t.codigo = ANY(%s)
          GROUP BY 1, 2, 3, 4, 5
      ),
      documentos AS (
          INSERT INTO public.documentos_fiscais_tributos (
              nota_id,
              tributo_id,
              empresa_cnpj,
              periodo_ano,
              periodo_mes,
              modelo_documento,
              chave_acesso,
              tipo_operacao,
              data_emissao,
              base_calculo,
              valor_debito,
              valor_credito,
              valor_tributo,
              natureza,
              origem,
              status,
              observacoes
          )
          SELECT
              a.nota_id,
              a.tributo_id,
              a.empresa_cnpj,
              a.periodo_ano,
              a.periodo_mes,
              n.modelo,
              n.numero_nf::varchar,
              CASE
                WHEN EXISTS (
                  SELECT 1 FROM public.notas_itens ni
                  WHERE ni.nota_id = n.id
                    AND LEFT(regexp_replace(COALESCE(ni.cfop, ''), '\\D', '', 'g'), 1) IN ('1','2','3')
                ) THEN 'entrada'
                ELSE 'saida'
              END,
              n.data_emissao,
              a.base_calculo,
              a.valor_debito,
              a.valor_credito,
              a.valor_tributo,
              'debito',
              'xml',
              'ativo',
              'Tributo da Reforma Tributaria extraido do XML.'
          FROM agregados a
          JOIN public.notas n ON n.id = a.nota_id
          WHERE COALESCE(a.valor_tributo, 0) <> 0
          RETURNING id, nota_id, tributo_id
      )
      UPDATE public.itens_documentos_fiscais_tributos it
      SET documento_tributo_id = d.id
      FROM documentos d
      JOIN public.notas_itens ni ON ni.nota_id = d.nota_id
      WHERE it.nota_item_id = ni.id
        AND it.tributo_id = d.tributo_id
        AND ni.nota_id = ANY(%s)
      """,
      (nota_ids, codigos_reforma, nota_ids),
    )
