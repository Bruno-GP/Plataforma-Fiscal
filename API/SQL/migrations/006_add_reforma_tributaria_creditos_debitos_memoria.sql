CREATE TABLE IF NOT EXISTS public.creditos_tributarios (
    id BIGSERIAL PRIMARY KEY,
    apuracao_id BIGINT REFERENCES public.apuracao_tributaria(id) ON DELETE SET NULL,
    documento_tributo_id BIGINT REFERENCES public.documentos_fiscais_tributos(id) ON DELETE SET NULL,
    item_tributo_id BIGINT REFERENCES public.itens_documentos_fiscais_tributos(id) ON DELETE SET NULL,
    empresa_cnpj VARCHAR(20) NOT NULL,
    periodo_ano INTEGER NOT NULL,
    periodo_mes INTEGER NOT NULL,
    tributo_id BIGINT NOT NULL REFERENCES public.tributos(id) ON DELETE RESTRICT,
    regra_vigencia_id BIGINT REFERENCES public.regras_tributarias_vigencias(id) ON DELETE SET NULL,
    origem_credito VARCHAR(40) NOT NULL,
    tipo_credito VARCHAR(40) NOT NULL,
    valor_original NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_aproveitado NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_estornado NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_saldo NUMERIC(18,2) NOT NULL DEFAULT 0,
    data_origem DATE,
    data_aproveitamento DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'disponivel',
    codigo_ajuste VARCHAR(30),
    fundamento_legal TEXT,
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_creditos_tributarios_periodo_mes
        CHECK (periodo_mes BETWEEN 1 AND 12),
    CONSTRAINT ck_creditos_tributarios_origem
        CHECK (origem_credito IN ('entrada', 'devolucao', 'ajuste', 'saldo_anterior', 'credito_presumido', 'manual', 'outros')),
    CONSTRAINT ck_creditos_tributarios_tipo
        CHECK (tipo_credito IN ('basico', 'presumido', 'ressarcimento', 'compensacao', 'estorno_debito', 'outros')),
    CONSTRAINT ck_creditos_tributarios_status
        CHECK (status IN ('disponivel', 'aproveitado', 'parcial', 'estornado', 'cancelado')),
    CONSTRAINT ck_creditos_tributarios_valores
        CHECK (
            valor_original >= 0
            AND valor_aproveitado >= 0
            AND valor_estornado >= 0
            AND valor_saldo >= 0
        )
);

CREATE TABLE IF NOT EXISTS public.debitos_tributarios (
    id BIGSERIAL PRIMARY KEY,
    apuracao_id BIGINT REFERENCES public.apuracao_tributaria(id) ON DELETE SET NULL,
    documento_tributo_id BIGINT REFERENCES public.documentos_fiscais_tributos(id) ON DELETE SET NULL,
    item_tributo_id BIGINT REFERENCES public.itens_documentos_fiscais_tributos(id) ON DELETE SET NULL,
    empresa_cnpj VARCHAR(20) NOT NULL,
    periodo_ano INTEGER NOT NULL,
    periodo_mes INTEGER NOT NULL,
    tributo_id BIGINT NOT NULL REFERENCES public.tributos(id) ON DELETE RESTRICT,
    regra_vigencia_id BIGINT REFERENCES public.regras_tributarias_vigencias(id) ON DELETE SET NULL,
    origem_debito VARCHAR(40) NOT NULL,
    tipo_debito VARCHAR(40) NOT NULL,
    valor_original NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_reduzido NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_diferido NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_estornado NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_devido NUMERIC(18,2) NOT NULL DEFAULT 0,
    data_fato_gerador DATE,
    data_vencimento DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'aberto',
    codigo_ajuste VARCHAR(30),
    fundamento_legal TEXT,
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_debitos_tributarios_periodo_mes
        CHECK (periodo_mes BETWEEN 1 AND 12),
    CONSTRAINT ck_debitos_tributarios_origem
        CHECK (origem_debito IN ('saida', 'importacao', 'ajuste', 'saldo_anterior', 'manual', 'outros')),
    CONSTRAINT ck_debitos_tributarios_tipo
        CHECK (tipo_debito IN ('operacao', 'diferido', 'estorno_credito', 'ajuste_debito', 'multa_juros', 'outros')),
    CONSTRAINT ck_debitos_tributarios_status
        CHECK (status IN ('aberto', 'apurado', 'recolhido', 'estornado', 'cancelado')),
    CONSTRAINT ck_debitos_tributarios_valores
        CHECK (
            valor_original >= 0
            AND valor_reduzido >= 0
            AND valor_diferido >= 0
            AND valor_estornado >= 0
            AND valor_devido >= 0
        )
);

CREATE TABLE IF NOT EXISTS public.memoria_calculo_tributaria (
    id BIGSERIAL PRIMARY KEY,
    documento_tributo_id BIGINT REFERENCES public.documentos_fiscais_tributos(id) ON DELETE CASCADE,
    item_tributo_id BIGINT REFERENCES public.itens_documentos_fiscais_tributos(id) ON DELETE CASCADE,
    credito_tributario_id BIGINT REFERENCES public.creditos_tributarios(id) ON DELETE SET NULL,
    debito_tributario_id BIGINT REFERENCES public.debitos_tributarios(id) ON DELETE SET NULL,
    tributo_id BIGINT NOT NULL REFERENCES public.tributos(id) ON DELETE RESTRICT,
    regra_id BIGINT REFERENCES public.regras_tributarias(id) ON DELETE SET NULL,
    regra_vigencia_id BIGINT REFERENCES public.regras_tributarias_vigencias(id) ON DELETE SET NULL,
    empresa_cnpj VARCHAR(20) NOT NULL,
    periodo_ano INTEGER,
    periodo_mes INTEGER,
    etapa_calculo VARCHAR(50) NOT NULL,
    base_origem NUMERIC(18,2),
    base_calculo NUMERIC(18,2),
    aliquota_aplicada NUMERIC(9,6),
    percentual_reducao_base NUMERIC(9,6),
    percentual_diferimento NUMERIC(9,6),
    valor_calculado NUMERIC(18,2),
    formula_calculo TEXT,
    parametros_calculo JSONB NOT NULL DEFAULT '{}'::jsonb,
    resultado_calculo JSONB NOT NULL DEFAULT '{}'::jsonb,
    fonte_dados VARCHAR(40) NOT NULL DEFAULT 'calculado',
    hash_calculo VARCHAR(64),
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_memoria_calculo_tributaria_referencia
        CHECK (
            documento_tributo_id IS NOT NULL
            OR item_tributo_id IS NOT NULL
            OR credito_tributario_id IS NOT NULL
            OR debito_tributario_id IS NOT NULL
        ),
    CONSTRAINT ck_memoria_calculo_tributaria_periodo_mes
        CHECK (periodo_mes IS NULL OR periodo_mes BETWEEN 1 AND 12),
    CONSTRAINT ck_memoria_calculo_tributaria_fonte
        CHECK (fonte_dados IN ('xml', 'sped', 'calculado', 'manual', 'importado'))
);

CREATE INDEX IF NOT EXISTS idx_creditos_tributarios_apuracao
ON public.creditos_tributarios (apuracao_id);

CREATE INDEX IF NOT EXISTS idx_creditos_tributarios_documento_tributo
ON public.creditos_tributarios (documento_tributo_id);

CREATE INDEX IF NOT EXISTS idx_creditos_tributarios_item_tributo
ON public.creditos_tributarios (item_tributo_id);

CREATE INDEX IF NOT EXISTS idx_creditos_tributarios_empresa_periodo
ON public.creditos_tributarios (empresa_cnpj, periodo_ano, periodo_mes);

CREATE INDEX IF NOT EXISTS idx_creditos_tributarios_tributo
ON public.creditos_tributarios (tributo_id);

CREATE INDEX IF NOT EXISTS idx_creditos_tributarios_status
ON public.creditos_tributarios (status);

CREATE INDEX IF NOT EXISTS idx_debitos_tributarios_apuracao
ON public.debitos_tributarios (apuracao_id);

CREATE INDEX IF NOT EXISTS idx_debitos_tributarios_documento_tributo
ON public.debitos_tributarios (documento_tributo_id);

CREATE INDEX IF NOT EXISTS idx_debitos_tributarios_item_tributo
ON public.debitos_tributarios (item_tributo_id);

CREATE INDEX IF NOT EXISTS idx_debitos_tributarios_empresa_periodo
ON public.debitos_tributarios (empresa_cnpj, periodo_ano, periodo_mes);

CREATE INDEX IF NOT EXISTS idx_debitos_tributarios_tributo
ON public.debitos_tributarios (tributo_id);

CREATE INDEX IF NOT EXISTS idx_debitos_tributarios_status
ON public.debitos_tributarios (status);

CREATE INDEX IF NOT EXISTS idx_memoria_calculo_tributaria_documento_tributo
ON public.memoria_calculo_tributaria (documento_tributo_id);

CREATE INDEX IF NOT EXISTS idx_memoria_calculo_tributaria_item_tributo
ON public.memoria_calculo_tributaria (item_tributo_id);

CREATE INDEX IF NOT EXISTS idx_memoria_calculo_tributaria_credito
ON public.memoria_calculo_tributaria (credito_tributario_id);

CREATE INDEX IF NOT EXISTS idx_memoria_calculo_tributaria_debito
ON public.memoria_calculo_tributaria (debito_tributario_id);

CREATE INDEX IF NOT EXISTS idx_memoria_calculo_tributaria_empresa_periodo
ON public.memoria_calculo_tributaria (empresa_cnpj, periodo_ano, periodo_mes);

CREATE INDEX IF NOT EXISTS idx_memoria_calculo_tributaria_tributo
ON public.memoria_calculo_tributaria (tributo_id);

CREATE INDEX IF NOT EXISTS idx_memoria_calculo_tributaria_regra_vigencia
ON public.memoria_calculo_tributaria (regra_vigencia_id);

CREATE INDEX IF NOT EXISTS idx_memoria_calculo_tributaria_hash
ON public.memoria_calculo_tributaria (hash_calculo);
