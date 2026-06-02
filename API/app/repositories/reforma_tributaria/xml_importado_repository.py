from __future__ import annotations


def tabela_xml_importados_existe(cur) -> bool:
  cur.execute("SELECT to_regclass('public.notas_xml_importados')")
  row = cur.fetchone()
  return bool(row and row[0])


def remover_tributos_reforma_nota(
  cur,
  *,
  nota_id: int,
  codigos_tributos: tuple[str, ...],
) -> None:
  cur.execute(
    """
    DELETE FROM public.documentos_fiscais_tributos dt
    USING public.tributos t
    WHERE dt.tributo_id = t.id
      AND dt.nota_id = %s
      AND t.codigo = ANY(%s);
    """,
    (nota_id, list(codigos_tributos)),
  )
  cur.execute(
    """
    DELETE FROM public.itens_documentos_fiscais_tributos it
    USING public.notas_itens ni, public.tributos t
    WHERE it.nota_item_id = ni.id
      AND it.tributo_id = t.id
      AND ni.nota_id = %s
      AND t.codigo = ANY(%s);
    """,
    (nota_id, list(codigos_tributos)),
  )


def inserir_tributo_reforma_item_importado(
  *,
  cur,
  nota_item_id: int,
  empresa_cnpj: str,
  periodo_ano: int,
  periodo_mes: int,
  numero_item: int,
  produto_codigo: str,
  ncm: str,
  cfop: str,
  tributo: dict,
) -> bool:
  valor_tributo = tributo.get("valor_tributo") or 0
  if valor_tributo == 0:
    return False

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
      CASE
        WHEN EXISTS (
          SELECT 1
          FROM public.ncm_catalogo nc
          WHERE nc.codigo = LEFT(regexp_replace(COALESCE(%s, ''), '\\D', '', 'g'), 8)::char(8)
        )
          THEN LEFT(regexp_replace(COALESCE(%s, ''), '\\D', '', 'g'), 8)::char(8)
        ELSE NULL
      END,
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
      'Tributo da Reforma Tributaria extraido do XML importado.'
    FROM public.tributos t
    WHERE t.codigo = %s
      AND NOT EXISTS (
        SELECT 1
        FROM public.itens_documentos_fiscais_tributos it
        JOIN public.tributos existente ON existente.id = it.tributo_id
        WHERE it.nota_item_id = %s
          AND existente.codigo = %s
          AND it.origem = 'xml'
          AND COALESCE(it.valor_tributo, 0) = COALESCE(%s, 0)
      );
    """,
    (
      nota_item_id,
      empresa_cnpj,
      periodo_ano,
      periodo_mes,
      numero_item,
      produto_codigo,
      ncm,
      ncm,
      cfop,
      tributo.get("cst_codigo"),
      tributo.get("classificacao_tributaria"),
      tributo.get("base_calculo") or 0,
      tributo.get("aliquota") or 0,
      valor_tributo,
      valor_tributo,
      tributo.get("tributo_codigo"),
      nota_item_id,
      tributo.get("tributo_codigo"),
      valor_tributo,
    ),
  )

  return cur.rowcount > 0
