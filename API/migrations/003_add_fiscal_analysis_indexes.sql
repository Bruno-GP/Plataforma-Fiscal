CREATE INDEX IF NOT EXISTS idx_notas_emitente_cnpj_normalizado
ON public.notas ((regexp_replace(COALESCE(emitente_cnpj, ''), '\D', '', 'g')));

CREATE INDEX IF NOT EXISTS idx_notas_emitente_cnpj_data_normalizado
ON public.notas ((regexp_replace(COALESCE(emitente_cnpj, ''), '\D', '', 'g')), data_emissao);

CREATE INDEX IF NOT EXISTS idx_notas_destinatario_uf_normalizado
ON public.notas ((UPPER(COALESCE(NULLIF(TRIM(destinatario_uf), ''), 'Sem UF'))));

CREATE INDEX IF NOT EXISTS idx_notas_destinatario_cidade_normalizada
ON public.notas ((UPPER(COALESCE(NULLIF(TRIM(destinatario_cidade), ''), 'Cidade nao identificada'))));

CREATE INDEX IF NOT EXISTS idx_notas_itens_nota_cfop_tipo
ON public.notas_itens (nota_id, (LEFT(regexp_replace(COALESCE(cfop, ''), '\D', '', 'g'), 1)));

CREATE INDEX IF NOT EXISTS idx_notas_itens_ncm_normalizado
ON public.notas_itens ((regexp_replace(COALESCE(ncm, ''), '\D', '', 'g')));

CREATE INDEX IF NOT EXISTS idx_notas_itens_produto_codigo_normalizado
ON public.notas_itens ((COALESCE(NULLIF(TRIM(produto_codigo), ''), 'SEM-CODIGO')));

CREATE INDEX IF NOT EXISTS idx_sped_documentos_empresa_tipo_data_normalizado
ON public.sped_documentos_fiscais ((regexp_replace(COALESCE(empresa_cnpj, ''), '\D', '', 'g')), tipo_operacao, data_emissao);

CREATE INDEX IF NOT EXISTS idx_sped_documento_itens_documento
ON public.sped_documento_itens (documento_id);

CREATE INDEX IF NOT EXISTS idx_sped_documento_itens_produto
ON public.sped_documento_itens (produto_id);

CREATE INDEX IF NOT EXISTS idx_sped_produtos_codigo_normalizado
ON public.sped_produtos ((COALESCE(NULLIF(TRIM(codigo), ''), 'SEM-CODIGO')));

CREATE INDEX IF NOT EXISTS idx_sped_produtos_ncm_normalizado
ON public.sped_produtos ((regexp_replace(COALESCE(ncm, ''), '\D', '', 'g')));

CREATE INDEX IF NOT EXISTS idx_sped_participantes_uf_normalizada
ON public.sped_participantes ((UPPER(COALESCE(NULLIF(TRIM(uf), ''), 'Sem UF'))));

CREATE INDEX IF NOT EXISTS idx_sped_participantes_cidade_normalizada
ON public.sped_participantes ((UPPER(COALESCE(NULLIF(TRIM(municipio_nome), ''), NULLIF(TRIM(municipio), ''), 'Cidade nao identificada'))));
