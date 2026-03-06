CREATE DATABASE Fiscal;

-- =========================================================
-- BLOCO NFE
-- =========================================================

CREATE TABLE IF NOT EXISTS NFE_empresas (
    id       BIGSERIAL PRIMARY KEY,
    cnpj     VARCHAR(20) NOT NULL UNIQUE,
    nome     VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS NFE_processamentos (
    id                   BIGSERIAL PRIMARY KEY,
    empresa_id           BIGINT REFERENCES NFE_empresas(id) ON DELETE SET NULL,
    origem               TEXT,
    pasta_xml            TEXT,
    periodo_solicitado   TEXT,
    cnpj_emitente        TEXT,
    periodo_ano          INTEGER,
    periodo_mes          INTEGER,
    periodos_encontrados JSONB,
    notas_processadas    INTEGER,
    itens_processados    INTEGER,
    kpis                 JSONB,
    erros                JSONB,
    status               TEXT,
    data_processamento   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS NFE_notas (
    id                      BIGSERIAL PRIMARY KEY,
    processamento_id        BIGINT REFERENCES NFE_processamentos(id) ON DELETE SET NULL,
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

CREATE TABLE IF NOT EXISTS NFE_itens (
    id              BIGSERIAL PRIMARY KEY,
    nota_id         BIGINT NOT NULL REFERENCES NFE_notas(id) ON DELETE CASCADE,
    empresa_id      BIGINT REFERENCES NFE_empresas(id) ON DELETE SET NULL,
    cnpj            VARCHAR(20) REFERENCES NFE_empresas(cnpj) ON DELETE SET NULL,
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

CREATE TABLE IF NOT EXISTS NFE_cfops (
    id         BIGSERIAL PRIMARY KEY,
    codigo     VARCHAR(10) NOT NULL UNIQUE,
    descricao  VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS NFE_processamento_erros (
    id                BIGSERIAL PRIMARY KEY,
    processamento_id  BIGINT NOT NULL REFERENCES NFE_processamentos(id) ON DELETE CASCADE,
    codigo            VARCHAR(50) NOT NULL,
    mensagem          TEXT NOT NULL,
    detalhe           TEXT
);

CREATE TABLE IF NOT EXISTS NFE_kpis (
    id                BIGSERIAL PRIMARY KEY,
    processamento_id  BIGINT NOT NULL REFERENCES NFE_processamentos(id) ON DELETE CASCADE,
    emitente_cnpj     VARCHAR(14),
    periodo_ano       INTEGER,
    periodo_mes       INTEGER,
    total_vendas      NUMERIC(18,2) DEFAULT 0,
    quantidade_notas  INT DEFAULT 0,
    ticket_medio      NUMERIC(18,2) DEFAULT 0,
    maior_nota        NUMERIC(18,2) DEFAULT 0,
    menor_nota        NUMERIC(18,2) DEFAULT 0,
    total_icms        NUMERIC(18,2) DEFAULT 0,
    total_ipi         NUMERIC(18,2) DEFAULT 0,
    total_pis         NUMERIC(18,2) DEFAULT 0,
    total_cofins      NUMERIC(18,2) DEFAULT 0,
    top_clientes      JSONB DEFAULT '[]'::jsonb,
    top_produtos      JSONB DEFAULT '[]'::jsonb,
    top_cidades       JSONB DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS NFE_login (
    id          BIGSERIAL PRIMARY KEY,
    empresa_id  BIGINT NOT NULL REFERENCES NFE_empresas(id) ON DELETE CASCADE,
    cnpj        VARCHAR(20) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    senha       VARCHAR(255) NOT NULL,
    criado_em   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS NFE_xml_importados (
    id              BIGSERIAL PRIMARY KEY,
    cnpj_emitente   VARCHAR(20) NOT NULL,
    nome_arquivo    TEXT NOT NULL,
    hash_arquivo    VARCHAR(64) NOT NULL,
    tamanho_bytes   BIGINT,
    criado_em       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (cnpj_emitente, hash_arquivo)
);

CREATE INDEX IF NOT EXISTS idx_NFE_processamentos_empresa ON NFE_processamentos (empresa_id);
CREATE INDEX IF NOT EXISTS idx_NFE_notas_emitente_data ON NFE_notas (emitente_cnpj, data_emissao);
CREATE INDEX IF NOT EXISTS idx_NFE_notas_numero_emitente ON NFE_notas (numero_nf, emitente_cnpj);
CREATE INDEX IF NOT EXISTS idx_NFE_cfops_codigo ON NFE_cfops (codigo);
CREATE INDEX IF NOT EXISTS idx_NFE_itens_nota ON NFE_itens (nota_id);
CREATE INDEX IF NOT EXISTS idx_NFE_itens_produto ON NFE_itens (produto_codigo);
CREATE INDEX IF NOT EXISTS idx_NFE_itens_empresa ON NFE_itens (empresa_id);
CREATE INDEX IF NOT EXISTS idx_NFE_itens_cnpj ON NFE_itens (cnpj);
CREATE INDEX IF NOT EXISTS idx_NFE_proc_erros_proc ON NFE_processamento_erros (processamento_id);
CREATE INDEX IF NOT EXISTS idx_NFE_kpis_proc ON NFE_kpis (processamento_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_NFE_kpis_periodo ON NFE_kpis (emitente_cnpj, periodo_ano, periodo_mes);
CREATE INDEX IF NOT EXISTS idx_NFE_login_empresa ON NFE_login (empresa_id);
CREATE INDEX IF NOT EXISTS idx_NFE_login_cnpj ON NFE_login (cnpj);
CREATE UNIQUE INDEX IF NOT EXISTS idx_NFE_login_email_lower ON NFE_login (LOWER(email));
CREATE INDEX IF NOT EXISTS idx_NFE_xml_importados_cnpj ON NFE_xml_importados (cnpj_emitente);


-- =========================================================
-- BLOCO SPED
-- =========================================================

CREATE TABLE IF NOT EXISTS SPED_empresas (
    cnpj               CHAR(14) PRIMARY KEY,
    razao_social       VARCHAR(255),
    ie                 VARCHAR(20),
    uf                 CHAR(2),
    cnae               VARCHAR(10),
    regime_tributario  VARCHAR(30)
);

CREATE TABLE IF NOT EXISTS SPED_sped_importacoes (
    id              SERIAL PRIMARY KEY,
    empresa_cnpj    CHAR(14) NOT NULL REFERENCES SPED_empresas(cnpj),
    periodo_ano     INT NOT NULL,
    periodo_mes     INT NOT NULL,
    hash_arquivo    VARCHAR(64),
    nome_arquivo    VARCHAR(255),
    versao_layout   VARCHAR(10),
    total_registros INT,
    data_importacao TIMESTAMP DEFAULT NOW(),
    status          VARCHAR(20),
    observacoes     TEXT
);

CREATE TABLE IF NOT EXISTS SPED_participantes (
    id            SERIAL PRIMARY KEY,
    empresa_cnpj  CHAR(14) REFERENCES SPED_empresas(cnpj),
    codigo        VARCHAR(60),
    nome          VARCHAR(255),
    cnpj_cpf      VARCHAR(14),
    uf            CHAR(2),
    municipio     VARCHAR(100),
    municipio_nome VARCHAR(120),
    tipo          VARCHAR(20)
);

ALTER TABLE SPED_participantes
ADD COLUMN municipio_nome VARCHAR(120);

CREATE TABLE IF NOT EXISTS SPED_produtos (
    id            SERIAL PRIMARY KEY,
    empresa_cnpj  CHAR(14) REFERENCES SPED_empresas(cnpj),
    codigo        VARCHAR(60),
    descricao     VARCHAR(255),
    ncm           VARCHAR(10),
    unidade       VARCHAR(10),
    tipo_item     VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS SPED_documentos_fiscais (
    id                SERIAL PRIMARY KEY,
    empresa_cnpj      CHAR(14) REFERENCES SPED_empresas(cnpj),
    participante_id   INT REFERENCES SPED_participantes(id),
    modelo            INT,
    serie             VARCHAR(10),
    numero            INT,
    chave_acesso      VARCHAR(44),
    tipo_operacao     VARCHAR(10),
    data_emissao      DATE,
    data_movimentacao DATE,
    valor_total       NUMERIC(15,2),
    valor_produtos    NUMERIC(15,2),
    valor_frete       NUMERIC(15,2),
    valor_desconto    NUMERIC(15,2),
    situacao          VARCHAR(20)
);

CREATE INDEX IF NOT EXISTS idx_SPED_documentos_empresa_data
ON SPED_documentos_fiscais (empresa_cnpj, data_emissao);

CREATE TABLE IF NOT EXISTS SPED_documento_itens (
    id             SERIAL PRIMARY KEY,
    documento_id   INT REFERENCES SPED_documentos_fiscais(id),
    produto_id     INT REFERENCES SPED_produtos(id),
    numero_item    INT,
    cfop           VARCHAR(4),
    quantidade     NUMERIC(15,4),
    valor_unitario NUMERIC(15,6),
    valor_total    NUMERIC(15,2),
    desconto       NUMERIC(15,2)
);

CREATE TABLE IF NOT EXISTS SPED_tributos_itens (
    id            SERIAL PRIMARY KEY,
    item_id       INT REFERENCES SPED_documento_itens(id),
    imposto       VARCHAR(10),
    cst           VARCHAR(5),
    base_calculo  NUMERIC(15,2),
    aliquota      NUMERIC(7,4),
    valor         NUMERIC(15,2),
    icms_st       NUMERIC(15,2),
    reducao_base  NUMERIC(7,4)
);

CREATE TABLE IF NOT EXISTS SPED_resumo_cfop_cst (
    id             SERIAL PRIMARY KEY,
    empresa_cnpj   CHAR(14),
    periodo_ano    INT,
    periodo_mes    INT,
    cfop           VARCHAR(4),
    cst            VARCHAR(5),
    valor_contabil NUMERIC(15,2),
    base_icms      NUMERIC(15,2),
    valor_icms     NUMERIC(15,2),
    valor_ipi      NUMERIC(15,2)
);

CREATE INDEX IF NOT EXISTS idx_SPED_resumo_empresa_periodo
ON SPED_resumo_cfop_cst (empresa_cnpj, periodo_ano, periodo_mes);

CREATE TABLE IF NOT EXISTS SPED_apuracao_icms (
    id             SERIAL PRIMARY KEY,
    empresa_cnpj   CHAR(14),
    periodo_ano    INT,
    periodo_mes    INT,
    total_debitos  NUMERIC(15,2),
    total_creditos NUMERIC(15,2),
    ajustes        NUMERIC(15,2),
    saldo_apurado  NUMERIC(15,2)
);

CREATE TABLE IF NOT EXISTS SPED_apuracao_ipi (
    id             SERIAL PRIMARY KEY,
    empresa_cnpj   CHAR(14),
    periodo_ano    INT,
    periodo_mes    INT,
    total_debitos  NUMERIC(15,2),
    total_creditos NUMERIC(15,2),
    saldo_apurado  NUMERIC(15,2)
);

CREATE TABLE IF NOT EXISTS SPED_inventario (
    id             SERIAL PRIMARY KEY,
    empresa_cnpj   CHAR(14),
    periodo_ano    INT,
    produto_id     INT REFERENCES SPED_produtos(id),
    quantidade     NUMERIC(15,4),
    valor_unitario NUMERIC(15,6),
    valor_total    NUMERIC(15,2)
);

CREATE TABLE IF NOT EXISTS SPED_ajustes_fiscais (
    id            SERIAL PRIMARY KEY,
    empresa_cnpj  CHAR(14),
    periodo_ano   INT,
    periodo_mes   INT,
    codigo_ajuste VARCHAR(20),
    descricao     TEXT,
    valor         NUMERIC(15,2)
);

CREATE TABLE IF NOT EXISTS SPED_kpis_sped_fiscal (
    id                            SERIAL PRIMARY KEY,
    processamento_id              INTEGER NOT NULL,
    cnpj_emitente                 VARCHAR(14) NOT NULL,
    periodo_ano                   INTEGER NOT NULL,
    periodo_mes                   INTEGER NOT NULL,
    total_documentos              INTEGER DEFAULT 0,
    total_itens                   INTEGER DEFAULT 0,
    total_cfop_distintos          INTEGER DEFAULT 0,
    total_ncm_distintos           INTEGER DEFAULT 0,
    total_participantes           INTEGER DEFAULT 0,
    valor_total_entradas          NUMERIC(15,2) DEFAULT 0,
    valor_total_saidas            NUMERIC(15,2) DEFAULT 0,
    valor_total_produtos          NUMERIC(15,2) DEFAULT 0,
    valor_total_frete             NUMERIC(15,2) DEFAULT 0,
    valor_total_descontos         NUMERIC(15,2) DEFAULT 0,
    icms_base_calculo             NUMERIC(15,2) DEFAULT 0,
    icms_valor_debitado           NUMERIC(15,2) DEFAULT 0,
    icms_valor_creditado          NUMERIC(15,2) DEFAULT 0,
    icms_valor_st                 NUMERIC(15,2) DEFAULT 0,
    icms_isento                   NUMERIC(15,2) DEFAULT 0,
    icms_outros                   NUMERIC(15,2) DEFAULT 0,
    ipi_base_calculo              NUMERIC(15,2) DEFAULT 0,
    ipi_valor                     NUMERIC(15,2) DEFAULT 0,
    ticket_medio                  NUMERIC(15,2) DEFAULT 0,
    percentual_icms_sobre_saida   NUMERIC(5,2) DEFAULT 0,
    data_calculo                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (cnpj_emitente, periodo_ano, periodo_mes)
);