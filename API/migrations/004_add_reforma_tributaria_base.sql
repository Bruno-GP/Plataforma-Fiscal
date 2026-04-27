CREATE TABLE IF NOT EXISTS public.tributos (
    id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(20) NOT NULL UNIQUE,
    nome VARCHAR(120) NOT NULL,
    esfera VARCHAR(20) NOT NULL,
    tipo VARCHAR(30) NOT NULL,
    descricao TEXT,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_tributos_esfera
        CHECK (esfera IN ('federal', 'estadual', 'municipal', 'compartilhada')),
    CONSTRAINT ck_tributos_tipo
        CHECK (tipo IN ('atual', 'reforma', 'transicao'))
);

INSERT INTO public.tributos (codigo, nome, esfera, tipo, descricao)
VALUES
    ('ICMS', 'Imposto sobre Circulacao de Mercadorias e Servicos', 'estadual', 'atual', 'Tributo estadual vigente antes da Reforma Tributaria do Consumo.'),
    ('ICMS_ST', 'ICMS Substituicao Tributaria', 'estadual', 'atual', 'Modalidade de recolhimento por substituicao tributaria do ICMS.'),
    ('IPI', 'Imposto sobre Produtos Industrializados', 'federal', 'atual', 'Tributo federal vigente antes da Reforma Tributaria do Consumo.'),
    ('PIS', 'Programa de Integracao Social', 'federal', 'atual', 'Contribuicao federal a ser substituida/absorvida no contexto da CBS.'),
    ('COFINS', 'Contribuicao para o Financiamento da Seguridade Social', 'federal', 'atual', 'Contribuicao federal a ser substituida/absorvida no contexto da CBS.'),
    ('ISS', 'Imposto sobre Servicos', 'municipal', 'atual', 'Tributo municipal vigente antes da Reforma Tributaria do Consumo.'),
    ('CBS', 'Contribuicao sobre Bens e Servicos', 'federal', 'reforma', 'Novo tributo federal da Reforma Tributaria do Consumo.'),
    ('IBS', 'Imposto sobre Bens e Servicos', 'compartilhada', 'reforma', 'Novo tributo compartilhado entre estados, Distrito Federal e municipios.'),
    ('IBS_UF', 'IBS Parcela Estadual', 'estadual', 'reforma', 'Componente estadual do IBS.'),
    ('IBS_MUN', 'IBS Parcela Municipal', 'municipal', 'reforma', 'Componente municipal do IBS.'),
    ('IS', 'Imposto Seletivo', 'federal', 'reforma', 'Imposto Seletivo incidente sobre bens e servicos especificos.')
ON CONFLICT (codigo) DO UPDATE SET
    nome = EXCLUDED.nome,
    esfera = EXCLUDED.esfera,
    tipo = EXCLUDED.tipo,
    descricao = EXCLUDED.descricao,
    atualizado_em = CURRENT_TIMESTAMP;

CREATE TABLE IF NOT EXISTS public.regras_tributarias (
    id BIGSERIAL PRIMARY KEY,
    tributo_id BIGINT NOT NULL REFERENCES public.tributos(id) ON DELETE RESTRICT,
    descricao VARCHAR(255) NOT NULL,
    tipo_operacao VARCHAR(20),
    regime_tributario VARCHAR(30),
    cfop VARCHAR(10),
    ncm_codigo CHAR(8),
    produto_codigo VARCHAR(120),
    uf_origem CHAR(2),
    uf_destino CHAR(2),
    municipio_origem_ibge CHAR(7),
    municipio_destino_ibge CHAR(7),
    natureza_calculo VARCHAR(30) NOT NULL DEFAULT 'debito',
    prioridade INTEGER NOT NULL DEFAULT 100,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_regras_tributarias_natureza_calculo
        CHECK (natureza_calculo IN ('debito', 'credito', 'informativo', 'ajuste')),
    CONSTRAINT fk_regras_tributarias_ncm
        FOREIGN KEY (ncm_codigo)
        REFERENCES public.ncm_catalogo (codigo)
        ON DELETE SET NULL,
    CONSTRAINT fk_regras_tributarias_municipio_origem
        FOREIGN KEY (municipio_origem_ibge)
        REFERENCES public.municipios_catalogo (codigo_ibge)
        ON DELETE SET NULL,
    CONSTRAINT fk_regras_tributarias_municipio_destino
        FOREIGN KEY (municipio_destino_ibge)
        REFERENCES public.municipios_catalogo (codigo_ibge)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS public.regras_tributarias_vigencias (
    id BIGSERIAL PRIMARY KEY,
    regra_id BIGINT NOT NULL REFERENCES public.regras_tributarias(id) ON DELETE CASCADE,
    inicio_vigencia DATE NOT NULL,
    fim_vigencia DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'ativa',
    fundamento_legal TEXT,
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_regras_tributarias_vigencias_periodo
        CHECK (fim_vigencia IS NULL OR fim_vigencia >= inicio_vigencia),
    CONSTRAINT ck_regras_tributarias_vigencias_status
        CHECK (status IN ('ativa', 'inativa', 'simulacao'))
);

CREATE TABLE IF NOT EXISTS public.aliquotas_tributarias (
    id BIGSERIAL PRIMARY KEY,
    regra_vigencia_id BIGINT NOT NULL REFERENCES public.regras_tributarias_vigencias(id) ON DELETE CASCADE,
    aliquota NUMERIC(9,6),
    aliquota_federal NUMERIC(9,6),
    aliquota_estadual NUMERIC(9,6),
    aliquota_municipal NUMERIC(9,6),
    reducao_base NUMERIC(9,6),
    percentual_diferimento NUMERIC(9,6),
    percentual_credito_presumido NUMERIC(9,6),
    valor_pauta NUMERIC(18,6),
    formula_calculo TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.apuracao_tributaria (
    id BIGSERIAL PRIMARY KEY,
    empresa_cnpj VARCHAR(20) NOT NULL,
    periodo_ano INTEGER NOT NULL,
    periodo_mes INTEGER NOT NULL,
    tributo_id BIGINT NOT NULL REFERENCES public.tributos(id) ON DELETE RESTRICT,
    total_debitos NUMERIC(18,2) NOT NULL DEFAULT 0,
    total_creditos NUMERIC(18,2) NOT NULL DEFAULT 0,
    ajustes_debito NUMERIC(18,2) NOT NULL DEFAULT 0,
    ajustes_credito NUMERIC(18,2) NOT NULL DEFAULT 0,
    estornos_debito NUMERIC(18,2) NOT NULL DEFAULT 0,
    estornos_credito NUMERIC(18,2) NOT NULL DEFAULT 0,
    compensacoes NUMERIC(18,2) NOT NULL DEFAULT 0,
    saldo_apurado NUMERIC(18,2) NOT NULL DEFAULT 0,
    saldo_periodo_anterior NUMERIC(18,2) NOT NULL DEFAULT 0,
    saldo_a_recolher NUMERIC(18,2) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'aberta',
    data_fechamento TIMESTAMP,
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_apuracao_tributaria_empresa_periodo_tributo
        UNIQUE (empresa_cnpj, periodo_ano, periodo_mes, tributo_id),
    CONSTRAINT ck_apuracao_tributaria_periodo_mes
        CHECK (periodo_mes BETWEEN 1 AND 12),
    CONSTRAINT ck_apuracao_tributaria_status
        CHECK (status IN ('aberta', 'fechada', 'retificada', 'cancelada'))
);

CREATE TABLE IF NOT EXISTS public.ajustes_tributarios (
    id BIGSERIAL PRIMARY KEY,
    apuracao_id BIGINT REFERENCES public.apuracao_tributaria(id) ON DELETE CASCADE,
    empresa_cnpj VARCHAR(20) NOT NULL,
    periodo_ano INTEGER NOT NULL,
    periodo_mes INTEGER NOT NULL,
    tributo_id BIGINT NOT NULL REFERENCES public.tributos(id) ON DELETE RESTRICT,
    codigo_ajuste VARCHAR(30),
    tipo_ajuste VARCHAR(30) NOT NULL,
    origem VARCHAR(30),
    valor NUMERIC(18,2) NOT NULL DEFAULT 0,
    descricao TEXT,
    fundamento_legal TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_ajustes_tributarios_periodo_mes
        CHECK (periodo_mes BETWEEN 1 AND 12),
    CONSTRAINT ck_ajustes_tributarios_tipo
        CHECK (tipo_ajuste IN ('debito', 'credito', 'estorno_debito', 'estorno_credito', 'compensacao', 'outros'))
);

CREATE INDEX IF NOT EXISTS idx_tributos_codigo
ON public.tributos (codigo);

CREATE INDEX IF NOT EXISTS idx_regras_tributarias_tributo
ON public.regras_tributarias (tributo_id);

CREATE INDEX IF NOT EXISTS idx_regras_tributarias_ncm
ON public.regras_tributarias (ncm_codigo);

CREATE INDEX IF NOT EXISTS idx_regras_tributarias_cfop
ON public.regras_tributarias (cfop);

CREATE INDEX IF NOT EXISTS idx_regras_tributarias_uf_destino
ON public.regras_tributarias (uf_destino);

CREATE INDEX IF NOT EXISTS idx_regras_tributarias_municipio_destino
ON public.regras_tributarias (municipio_destino_ibge);

CREATE INDEX IF NOT EXISTS idx_regras_tributarias_vigencias_regra
ON public.regras_tributarias_vigencias (regra_id);

CREATE INDEX IF NOT EXISTS idx_regras_tributarias_vigencias_periodo
ON public.regras_tributarias_vigencias (inicio_vigencia, fim_vigencia);

CREATE INDEX IF NOT EXISTS idx_aliquotas_tributarias_regra_vigencia
ON public.aliquotas_tributarias (regra_vigencia_id);

CREATE INDEX IF NOT EXISTS idx_apuracao_tributaria_empresa_periodo
ON public.apuracao_tributaria (empresa_cnpj, periodo_ano, periodo_mes);

CREATE INDEX IF NOT EXISTS idx_apuracao_tributaria_tributo
ON public.apuracao_tributaria (tributo_id);

CREATE INDEX IF NOT EXISTS idx_ajustes_tributarios_apuracao
ON public.ajustes_tributarios (apuracao_id);

CREATE INDEX IF NOT EXISTS idx_ajustes_tributarios_empresa_periodo
ON public.ajustes_tributarios (empresa_cnpj, periodo_ano, periodo_mes);

CREATE INDEX IF NOT EXISTS idx_ajustes_tributarios_tributo
ON public.ajustes_tributarios (tributo_id);
