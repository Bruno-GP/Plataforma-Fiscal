CREATE TABLE IF NOT EXISTS public.documentos_fiscais_tributos (
    id BIGSERIAL PRIMARY KEY,
    nota_id BIGINT REFERENCES public.notas(id) ON DELETE CASCADE,
    sped_documento_id INTEGER REFERENCES public.sped_documentos_fiscais(id) ON DELETE CASCADE,
    tributo_id BIGINT NOT NULL REFERENCES public.tributos(id) ON DELETE RESTRICT,
    regra_vigencia_id BIGINT REFERENCES public.regras_tributarias_vigencias(id) ON DELETE SET NULL,
    empresa_cnpj VARCHAR(20) NOT NULL,
    periodo_ano INTEGER,
    periodo_mes INTEGER,
    modelo_documento VARCHAR(10),
    chave_acesso VARCHAR(44),
    tipo_operacao VARCHAR(20),
    data_emissao DATE,
    base_calculo NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_debito NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_credito NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_tributo NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_isento NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_outros NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_reducao_base NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_diferido NUMERIC(18,2) NOT NULL DEFAULT 0,
    natureza VARCHAR(30) NOT NULL DEFAULT 'debito',
    origem VARCHAR(30) NOT NULL DEFAULT 'calculado',
    status VARCHAR(20) NOT NULL DEFAULT 'ativo',
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_documentos_fiscais_tributos_origem_documento
        CHECK (
            (nota_id IS NOT NULL AND sped_documento_id IS NULL)
            OR (nota_id IS NULL AND sped_documento_id IS NOT NULL)
        ),
    CONSTRAINT ck_documentos_fiscais_tributos_periodo_mes
        CHECK (periodo_mes IS NULL OR periodo_mes BETWEEN 1 AND 12),
    CONSTRAINT ck_documentos_fiscais_tributos_natureza
        CHECK (natureza IN ('debito', 'credito', 'informativo', 'ajuste')),
    CONSTRAINT ck_documentos_fiscais_tributos_origem
        CHECK (origem IN ('xml', 'sped', 'calculado', 'manual', 'importado')),
    CONSTRAINT ck_documentos_fiscais_tributos_status
        CHECK (status IN ('ativo', 'cancelado', 'substituido', 'ignorado'))
);

CREATE TABLE IF NOT EXISTS public.itens_documentos_fiscais_tributos (
    id BIGSERIAL PRIMARY KEY,
    documento_tributo_id BIGINT REFERENCES public.documentos_fiscais_tributos(id) ON DELETE CASCADE,
    nota_item_id BIGINT REFERENCES public.notas_itens(id) ON DELETE CASCADE,
    sped_item_id INTEGER REFERENCES public.sped_documento_itens(id) ON DELETE CASCADE,
    tributo_id BIGINT NOT NULL REFERENCES public.tributos(id) ON DELETE RESTRICT,
    regra_vigencia_id BIGINT REFERENCES public.regras_tributarias_vigencias(id) ON DELETE SET NULL,
    empresa_cnpj VARCHAR(20) NOT NULL,
    periodo_ano INTEGER,
    periodo_mes INTEGER,
    numero_item INTEGER,
    produto_codigo VARCHAR(120),
    ncm_codigo CHAR(8),
    cfop VARCHAR(10),
    cst_codigo VARCHAR(20),
    classificacao_tributaria VARCHAR(30),
    base_calculo NUMERIC(18,2) NOT NULL DEFAULT 0,
    aliquota NUMERIC(9,6),
    aliquota_federal NUMERIC(9,6),
    aliquota_estadual NUMERIC(9,6),
    aliquota_municipal NUMERIC(9,6),
    percentual_reducao_base NUMERIC(9,6),
    percentual_diferimento NUMERIC(9,6),
    valor_debito NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_credito NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_tributo NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_isento NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_outros NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_reducao_base NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_diferido NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_credito_presumido NUMERIC(18,2) NOT NULL DEFAULT 0,
    natureza VARCHAR(30) NOT NULL DEFAULT 'debito',
    origem VARCHAR(30) NOT NULL DEFAULT 'calculado',
    status VARCHAR(20) NOT NULL DEFAULT 'ativo',
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_itens_documentos_fiscais_tributos_origem_item
        CHECK (
            (nota_item_id IS NOT NULL AND sped_item_id IS NULL)
            OR (nota_item_id IS NULL AND sped_item_id IS NOT NULL)
        ),
    CONSTRAINT ck_itens_documentos_fiscais_tributos_periodo_mes
        CHECK (periodo_mes IS NULL OR periodo_mes BETWEEN 1 AND 12),
    CONSTRAINT ck_itens_documentos_fiscais_tributos_natureza
        CHECK (natureza IN ('debito', 'credito', 'informativo', 'ajuste')),
    CONSTRAINT ck_itens_documentos_fiscais_tributos_origem
        CHECK (origem IN ('xml', 'sped', 'calculado', 'manual', 'importado')),
    CONSTRAINT ck_itens_documentos_fiscais_tributos_status
        CHECK (status IN ('ativo', 'cancelado', 'substituido', 'ignorado')),
    CONSTRAINT fk_itens_documentos_fiscais_tributos_ncm
        FOREIGN KEY (ncm_codigo)
        REFERENCES public.ncm_catalogo (codigo)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_documentos_fiscais_tributos_nota
ON public.documentos_fiscais_tributos (nota_id);

CREATE INDEX IF NOT EXISTS idx_documentos_fiscais_tributos_sped_documento
ON public.documentos_fiscais_tributos (sped_documento_id);

CREATE INDEX IF NOT EXISTS idx_documentos_fiscais_tributos_empresa_periodo
ON public.documentos_fiscais_tributos (empresa_cnpj, periodo_ano, periodo_mes);

CREATE INDEX IF NOT EXISTS idx_documentos_fiscais_tributos_tributo
ON public.documentos_fiscais_tributos (tributo_id);

CREATE INDEX IF NOT EXISTS idx_documentos_fiscais_tributos_regra_vigencia
ON public.documentos_fiscais_tributos (regra_vigencia_id);

CREATE INDEX IF NOT EXISTS idx_documentos_fiscais_tributos_chave_acesso
ON public.documentos_fiscais_tributos (chave_acesso);

CREATE INDEX IF NOT EXISTS idx_itens_documentos_fiscais_tributos_documento_tributo
ON public.itens_documentos_fiscais_tributos (documento_tributo_id);

CREATE INDEX IF NOT EXISTS idx_itens_documentos_fiscais_tributos_nota_item
ON public.itens_documentos_fiscais_tributos (nota_item_id);

CREATE INDEX IF NOT EXISTS idx_itens_documentos_fiscais_tributos_sped_item
ON public.itens_documentos_fiscais_tributos (sped_item_id);

CREATE INDEX IF NOT EXISTS idx_itens_documentos_fiscais_tributos_empresa_periodo
ON public.itens_documentos_fiscais_tributos (empresa_cnpj, periodo_ano, periodo_mes);

CREATE INDEX IF NOT EXISTS idx_itens_documentos_fiscais_tributos_tributo
ON public.itens_documentos_fiscais_tributos (tributo_id);

CREATE INDEX IF NOT EXISTS idx_itens_documentos_fiscais_tributos_regra_vigencia
ON public.itens_documentos_fiscais_tributos (regra_vigencia_id);

CREATE INDEX IF NOT EXISTS idx_itens_documentos_fiscais_tributos_ncm
ON public.itens_documentos_fiscais_tributos (ncm_codigo);

CREATE INDEX IF NOT EXISTS idx_itens_documentos_fiscais_tributos_cfop
ON public.itens_documentos_fiscais_tributos (cfop);

CREATE INDEX IF NOT EXISTS idx_itens_documentos_fiscais_tributos_produto
ON public.itens_documentos_fiscais_tributos (produto_codigo);
