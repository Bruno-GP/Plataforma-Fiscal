CREATE INDEX IF NOT EXISTS idx_documentos_fiscais_tributos_empresa_tipo_periodo
ON public.documentos_fiscais_tributos (empresa_cnpj, tipo_operacao, periodo_ano, periodo_mes);

CREATE INDEX IF NOT EXISTS idx_documentos_fiscais_tributos_nfe_empresa_tipo_periodo
ON public.documentos_fiscais_tributos (empresa_cnpj, tipo_operacao, periodo_ano, periodo_mes)
WHERE nota_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_documentos_fiscais_tributos_sped_empresa_tipo_periodo
ON public.documentos_fiscais_tributos (empresa_cnpj, tipo_operacao, periodo_ano, periodo_mes)
WHERE sped_documento_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_documentos_fiscais_tributos_nfe_dashboard_periodo
ON public.documentos_fiscais_tributos (
  (regexp_replace(COALESCE(empresa_cnpj, ''), '\D', '', 'g')),
  tipo_operacao,
  (COALESCE(periodo_ano, EXTRACT(YEAR FROM data_emissao)::int)),
  (COALESCE(periodo_mes, EXTRACT(MONTH FROM data_emissao)::int))
)
WHERE nota_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_documentos_fiscais_tributos_sped_dashboard_periodo
ON public.documentos_fiscais_tributos (
  (regexp_replace(COALESCE(empresa_cnpj, ''), '\D', '', 'g')),
  tipo_operacao,
  (COALESCE(periodo_ano, EXTRACT(YEAR FROM data_emissao)::int)),
  (COALESCE(periodo_mes, EXTRACT(MONTH FROM data_emissao)::int))
)
WHERE sped_documento_id IS NOT NULL;
