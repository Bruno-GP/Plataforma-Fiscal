-- Tabela de empresas
CREATE TABLE IF NOT EXISTS empresas (
    id       BIGSERIAL PRIMARY KEY,
    cnpj     VARCHAR(20) NOT NULL UNIQUE,
    nome     VARCHAR(255) NOT NULL
);

-- Tabela de processamentos (com FK para empresas)
CREATE TABLE IF NOT EXISTS processamentos (
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
CREATE INDEX IF NOT EXISTS idx_processamentos_empresa
    ON processamentos (empresa_id);


-- 2) Notas
CREATE TABLE IF NOT EXISTS notas (
    id                      BIGSERIAL PRIMARY KEY,
    processamento_id        BIGINT REFERENCES processamentos(id) ON DELETE SET NULL,
    numero_nf               VARCHAR(50) NOT NULL,
    emitente_cnpj           VARCHAR(20) NOT NULL,
    modelo                  VARCHAR(5),
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
CREATE INDEX IF NOT EXISTS idx_notas_emitente_data ON notas (emitente_cnpj, data_emissao);
CREATE INDEX IF NOT EXISTS idx_notas_numero_emitente ON notas (numero_nf, emitente_cnpj);

-- 3) Itens
CREATE TABLE IF NOT EXISTS itens (
    id              BIGSERIAL PRIMARY KEY,
    nota_id         BIGINT NOT NULL REFERENCES notas(id) ON DELETE CASCADE,
    empresa_id      BIGINT REFERENCES empresas(id) ON DELETE SET NULL,
    cnpj            VARCHAR(20) REFERENCES empresas(cnpj) ON DELETE SET NULL,
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

-- 3.1) Tabela de CFOPs
CREATE TABLE IF NOT EXISTS cfops (
    id         BIGSERIAL PRIMARY KEY,
    codigo     VARCHAR(10) NOT NULL UNIQUE,
    descricao  VARCHAR(255) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cfops_codigo ON cfops (codigo);

CREATE INDEX IF NOT EXISTS idx_itens_nota ON itens (nota_id);
CREATE INDEX IF NOT EXISTS idx_itens_produto ON itens (produto_codigo);

CREATE INDEX IF NOT EXISTS idx_itens_empresa ON itens (empresa_id);
CREATE INDEX IF NOT EXISTS idx_itens_cnpj ON itens (cnpj);

ALTER TABLE IF EXISTS itens
    ADD COLUMN IF NOT EXISTS empresa_id BIGINT REFERENCES empresas(id) ON DELETE SET NULL;

ALTER TABLE IF EXISTS itens
    ADD COLUMN IF NOT EXISTS cnpj VARCHAR(20) REFERENCES empresas(cnpj) ON DELETE SET NULL;

-- 4) Erros do processamento (opcional)
CREATE TABLE IF NOT EXISTS processamento_erros (
    id                 BIGSERIAL PRIMARY KEY,
    processamento_id   BIGINT NOT NULL REFERENCES processamentos(id) ON DELETE CASCADE,
    codigo             VARCHAR(50) NOT NULL,
    mensagem           TEXT NOT NULL,
    detalhe            TEXT
);

CREATE INDEX IF NOT EXISTS idx_proc_erros_proc ON processamento_erros (processamento_id);

-- 5) KPIs do processamento (opcional)
CREATE TABLE IF NOT EXISTS kpis (
    id                   BIGSERIAL PRIMARY KEY,
    processamento_id     BIGINT NOT NULL REFERENCES processamentos(id) ON DELETE CASCADE,
    emitente_cnpj        VARCHAR(14),
    periodo_ano          INTEGER,
    periodo_mes          INTEGER,
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

CREATE INDEX IF NOT EXISTS idx_kpis_proc ON kpis (processamento_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_kpis_periodo
    ON kpis (emitente_cnpj, periodo_ano, periodo_mes);

-- 6) Login
CREATE TABLE IF NOT EXISTS login (
    id          BIGSERIAL PRIMARY KEY,
    empresa_id  BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    cnpj        VARCHAR(20) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    senha 		VARCHAR(255) NOT NULL,
    criado_em   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_login_empresa ON login (empresa_id);

CREATE INDEX IF NOT EXISTS idx_login_cnpj ON login (cnpj);

-- Ajustes para ambientes já existentes (migrations rápidas)
CREATE UNIQUE INDEX IF NOT EXISTS idx_login_email_lower ON login (LOWER(email));

-- 7) Controle de XMLs importados por CNPJ
CREATE TABLE IF NOT EXISTS xml_importados (
    id              BIGSERIAL PRIMARY KEY,
    cnpj_emitente   VARCHAR(20) NOT NULL,
    nome_arquivo    TEXT NOT NULL,
    hash_arquivo    VARCHAR(64) NOT NULL,
    tamanho_bytes   BIGINT,
    criado_em       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (cnpj_emitente, hash_arquivo)
);

CREATE INDEX IF NOT EXISTS idx_xml_importados_cnpj ON xml_importados (cnpj_emitente);