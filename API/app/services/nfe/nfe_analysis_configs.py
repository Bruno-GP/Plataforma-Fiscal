from app.services.fiscal.fiscal_analysis import FiscalDimensionConfig

NFE_CFOP_ANALYSIS_CONFIG = FiscalDimensionConfig(
  from_clause="""
    public.notas AS n
    JOIN public.notas_itens AS i
      ON i.nota_id = n.id
  """,
  company_filter_expr="regexp_replace(UPPER(COALESCE(n.emitente_cnpj, '')), '[^0-9A-Z]', '', 'g')",
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
  unknown_description="CFOP sem descrição",
)

NFE_NCM_ANALYSIS_CONFIG = FiscalDimensionConfig(
  from_clause="""
    public.notas AS n
    JOIN public.notas_itens AS i
      ON i.nota_id = n.id
  """,
  company_filter_expr="regexp_replace(UPPER(COALESCE(n.emitente_cnpj, '')), '[^0-9A-Z]', '', 'g')",
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
