-- Tabela de empresas
CREATE TABLE IF NOT EXISTS empresas (
    id       BIGSERIAL PRIMARY KEY,
    cnpj     VARCHAR(20) NOT NULL UNIQUE,
    nome     VARCHAR(255) NOT NULL
);

-- Tabela de processamentos (com FK para empresas)
CREATE TABLE IF NOT EXISTS nfe_processamentos (
    id                  BIGSERIAL PRIMARY KEY,
    empresa_id          BIGINT REFERENCES empresas(id) ON DELETE SET NULL,
    origem              TEXT,
    pasta_xml           TEXT,
    periodo_solicitado  TEXT,
    cnpj_emitente       TEXT,
    periodo_ano         INTEGER,
    periodo_mes         INTEGER,
    periodos_encontrados JSONB,
    notas_processadas   INTEGER,
    itens_processados   INTEGER,
    kpis                JSONB,
    erros               JSONB,
    status              TEXT,
    data_processamento  TIMESTAMPTZ
);

-- Índice útil para buscar processamentos por empresa
CREATE INDEX IF NOT EXISTS idx_nfe_processamentos_empresa
    ON nfe_processamentos (empresa_id);


-- 2) Notas
CREATE TABLE IF NOT EXISTS nfe_notas (
    id                      BIGSERIAL PRIMARY KEY,
    processamento_id        BIGINT REFERENCES nfe_processamentos(id) ON DELETE SET NULL,
    numero_nf               VARCHAR(50) NOT NULL,
    emitente_cnpj           VARCHAR(20) NOT NULL,
    data_emissao            DATE NOT NULL,
    natureza_operacao       VARCHAR(255),
    destinatario_documento  VARCHAR(20),
    destinatario_nome       VARCHAR(255),
    destinatario_cidade     VARCHAR(120),
    destinatario_uf         CHAR(2),
    valor_produtos          NUMERIC(18,2),
    valor_desconto          NUMERIC(18,2),
    valor_frete             NUMERIC(18,2),
    valor_icms              NUMERIC(18,2),
    valor_ipi               NUMERIC(18,2),
    valor_pis               NUMERIC(18,2),
    valor_cofins            NUMERIC(18,2),
    valor_total_nf          NUMERIC(18,2),
    criado_em               TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    atualizado_em           TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices úteis para notas
CREATE INDEX IF NOT EXISTS idx_nfe_notas_emitente_data ON nfe_notas (emitente_cnpj, data_emissao);
CREATE INDEX IF NOT EXISTS idx_nfe_notas_numero_emitente ON nfe_notas (numero_nf, emitente_cnpj);

-- 3) Itens
CREATE TABLE IF NOT EXISTS nfe_itens (
    id              BIGSERIAL PRIMARY KEY,
    nota_id         BIGINT NOT NULL REFERENCES nfe_notas(id) ON DELETE CASCADE,
    item_numero     INT,
    produto_codigo  VARCHAR(120),
    descricao       VARCHAR(255),
    ncm             VARCHAR(20),
    cfop            VARCHAR(10),
    quantidade      NUMERIC(18,4),
    valor_unitario  NUMERIC(18,6),
    valor_total     NUMERIC(18,2),
    icms_cst_csosn  VARCHAR(10),
    icms_base       NUMERIC(18,2),
    icms_aliquota   NUMERIC(10,4),
    icms_valor      NUMERIC(18,2)
);

CREATE INDEX IF NOT EXISTS idx_nfe_itens_nota ON nfe_itens (nota_id);
CREATE INDEX IF NOT EXISTS idx_nfe_itens_produto ON nfe_itens (produto_codigo);

-- 4) Erros do processamento (opcional)
CREATE TABLE IF NOT EXISTS nfe_processamento_erros (
    id                 BIGSERIAL PRIMARY KEY,
    processamento_id   BIGINT NOT NULL REFERENCES nfe_processamentos(id) ON DELETE CASCADE,
    codigo             VARCHAR(50) NOT NULL,
    mensagem           TEXT NOT NULL,
    detalhe            TEXT
);

CREATE INDEX IF NOT EXISTS idx_nfe_proc_erros_proc ON nfe_processamento_erros (processamento_id);

-- 5) KPIs do processamento (opcional)
CREATE TABLE IF NOT EXISTS nfe_kpis (
    id                   BIGSERIAL PRIMARY KEY,
    processamento_id     BIGINT NOT NULL REFERENCES nfe_processamentos(id) ON DELETE CASCADE,
    emitente_cnpj        VARCHAR(14),
    total_vendas         NUMERIC(18,2) DEFAULT 0,
    quantidade_notas     INT DEFAULT 0,
    ticket_medio         NUMERIC(18,2) DEFAULT 0,
    maior_nota           NUMERIC(18,2) DEFAULT 0,
    menor_nota           NUMERIC(18,2) DEFAULT 0,
    total_icms           NUMERIC(18,2) DEFAULT 0,
    total_ipi            NUMERIC(18,2) DEFAULT 0,
    total_pis            NUMERIC(18,2) DEFAULT 0,
    total_cofins         NUMERIC(18,2) DEFAULT 0,
    top_clientes         JSONB DEFAULT '[]'::jsonb,
    top_produtos         JSONB DEFAULT '[]'::jsonb,
    top_cidades          JSONB DEFAULT '[]'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_nfe_kpis_proc ON nfe_kpis (processamento_id);