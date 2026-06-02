from __future__ import annotations


def coletar_resumo_periodo(
  cur,
  cnpj: str,
  periodo_ano: int,
  periodo_mes: int,
  origem: str,
) -> dict:
  cur.execute(
    """
    SELECT COUNT(*)
    FROM public.documentos_fiscais_tributos dt
    WHERE regexp_replace(dt.empresa_cnpj, '\\D', '', 'g') = %s
      AND dt.periodo_ano = %s
      AND dt.periodo_mes = %s
      AND dt.origem = %s;
    """,
    (cnpj, periodo_ano, periodo_mes, origem),
  )
  documentos_tributos = int(cur.fetchone()[0] or 0)

  cur.execute(
    """
    SELECT COUNT(*)
    FROM public.itens_documentos_fiscais_tributos it
    WHERE regexp_replace(it.empresa_cnpj, '\\D', '', 'g') = %s
      AND it.periodo_ano = %s
      AND it.periodo_mes = %s
      AND it.origem = %s;
    """,
    (cnpj, periodo_ano, periodo_mes, origem),
  )
  itens_tributos = int(cur.fetchone()[0] or 0)

  cur.execute(
    """
    SELECT COUNT(*)
    FROM public.debitos_tributarios d
    WHERE regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s
      AND d.periodo_ano = %s
      AND d.periodo_mes = %s;
    """,
    (cnpj, periodo_ano, periodo_mes),
  )
  debitos = int(cur.fetchone()[0] or 0)

  cur.execute(
    """
    SELECT COUNT(*)
    FROM public.creditos_tributarios c
    WHERE regexp_replace(c.empresa_cnpj, '\\D', '', 'g') = %s
      AND c.periodo_ano = %s
      AND c.periodo_mes = %s;
    """,
    (cnpj, periodo_ano, periodo_mes),
  )
  creditos = int(cur.fetchone()[0] or 0)

  cur.execute(
    """
    SELECT COUNT(*)
    FROM public.memoria_calculo_tributaria m
    WHERE regexp_replace(m.empresa_cnpj, '\\D', '', 'g') = %s
      AND m.periodo_ano = %s
      AND m.periodo_mes = %s
      AND m.fonte_dados = %s;
    """,
    (cnpj, periodo_ano, periodo_mes, origem),
  )
  memorias = int(cur.fetchone()[0] or 0)

  cur.execute(
    """
    SELECT COUNT(*)
    FROM public.apuracao_tributaria a
    WHERE regexp_replace(a.empresa_cnpj, '\\D', '', 'g') = %s
      AND a.periodo_ano = %s
      AND a.periodo_mes = %s;
    """,
    (cnpj, periodo_ano, periodo_mes),
  )
  apuracoes = int(cur.fetchone()[0] or 0)

  return {
    "documentos_tributos": documentos_tributos,
    "itens_tributos": itens_tributos,
    "debitos": debitos,
    "creditos": creditos,
    "memorias": memorias,
    "apuracoes": apuracoes,
  }
