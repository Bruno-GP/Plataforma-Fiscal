CREATE DATABASE SPED_Fiscal

-- =========================================
-- 1. EMPRESAS
-- =========================================
CREATE TABLE empresas (
    cnpj CHAR(14) PRIMARY KEY,
    razao_social VARCHAR(255),
    ie VARCHAR(20),
    uf CHAR(2),
    cnae VARCHAR(10),
    regime_tributario VARCHAR(30)
);

-- =========================================
-- 2. CONTROLE DE IMPORTAÇÕES DO SPED
-- =========================================
CREATE TABLE sped_importacoes (
    id SERIAL PRIMARY KEY,
    empresa_cnpj CHAR(14) NOT NULL REFERENCES empresas(cnpj),
    periodo_ano INT NOT NULL,
    periodo_mes INT NOT NULL,
    hash_arquivo VARCHAR(64),
    nome_arquivo VARCHAR(255),
    versao_layout VARCHAR(10),
    total_registros INT,
    data_importacao TIMESTAMP DEFAULT now(),
    status VARCHAR(20), -- processado | erro | parcial
    observacoes TEXT
);

-- =========================================
-- 3. PARTICIPANTES (CLIENTES / FORNECEDORES)
-- =========================================
CREATE TABLE participantes (
    id SERIAL PRIMARY KEY,
    empresa_cnpj CHAR(14) REFERENCES empresas(cnpj),
    codigo VARCHAR(60),
    nome VARCHAR(255),
    cnpj_cpf VARCHAR(14),
    uf CHAR(2),
    municipio VARCHAR(100),
    tipo VARCHAR(20) -- cliente | fornecedor | ambos
);

-- =========================================
-- 4. PRODUTOS (CADASTRO FISCAL)
-- =========================================
CREATE TABLE produtos (
    id SERIAL PRIMARY KEY,
    empresa_cnpj CHAR(14) REFERENCES empresas(cnpj),
    codigo VARCHAR(60),
    descricao VARCHAR(255),
    ncm VARCHAR(10),
    unidade VARCHAR(10),
    tipo_item VARCHAR(10)
);

-- =========================================
-- 5. DOCUMENTOS FISCAIS
-- =========================================
CREATE TABLE documentos_fiscais (
    id SERIAL PRIMARY KEY,
    empresa_cnpj CHAR(14) REFERENCES empresas(cnpj),
    participante_id INT REFERENCES participantes(id),
    modelo INT, -- 55, 65, etc
    serie VARCHAR(10),
    numero INT,
    chave_acesso VARCHAR(44),
    tipo_operacao VARCHAR(10), -- entrada | saida
    data_emissao DATE,
    data_movimentacao DATE,
    valor_total NUMERIC(15,2),
    valor_produtos NUMERIC(15,2),
    valor_frete NUMERIC(15,2),
    valor_desconto NUMERIC(15,2),
    situacao VARCHAR(20) -- normal | cancelada | denegada
);

CREATE INDEX idx_documentos_empresa_data
ON documentos_fiscais (empresa_cnpj, data_emissao);

-- =========================================
-- 6. ITENS DOS DOCUMENTOS
-- =========================================
CREATE TABLE documento_itens (
    id SERIAL PRIMARY KEY,
    documento_id INT REFERENCES documentos_fiscais(id),
    produto_id INT REFERENCES produtos(id),
    numero_item INT,
    cfop VARCHAR(4),
    quantidade NUMERIC(15,4),
    valor_unitario NUMERIC(15,6),
    valor_total NUMERIC(15,2),
    desconto NUMERIC(15,2)
);

-- =========================================
-- 7. TRIBUTOS POR ITEM
-- =========================================
CREATE TABLE tributos_itens (
    id SERIAL PRIMARY KEY,
    item_id INT REFERENCES documento_itens(id),
    imposto VARCHAR(10), -- ICMS | IPI
    cst VARCHAR(5),
    base_calculo NUMERIC(15,2),
    aliquota NUMERIC(7,4),
    valor NUMERIC(15,2),
    icms_st NUMERIC(15,2),
    reducao_base NUMERIC(7,4)
);

-- =========================================
-- 8. RESUMO POR CFOP / CST (PERFORMANCE)
-- =========================================
CREATE TABLE resumo_cfop_cst (
    id SERIAL PRIMARY KEY,
    empresa_cnpj CHAR(14),
    periodo_ano INT,
    periodo_mes INT,
    cfop VARCHAR(4),
    cst VARCHAR(5),
    valor_contabil NUMERIC(15,2),
    base_icms NUMERIC(15,2),
    valor_icms NUMERIC(15,2),
    valor_ipi NUMERIC(15,2)
);

CREATE INDEX idx_resumo_empresa_periodo
ON resumo_cfop_cst (empresa_cnpj, periodo_ano, periodo_mes);

-- =========================================
-- 9. APURAÇÃO ICMS
-- =========================================
CREATE TABLE apuracao_icms (
    id SERIAL PRIMARY KEY,
    empresa_cnpj CHAR(14),
    periodo_ano INT,
    periodo_mes INT,
    total_debitos NUMERIC(15,2),
    total_creditos NUMERIC(15,2),
    ajustes NUMERIC(15,2),
    saldo_apurado NUMERIC(15,2)
);

-- =========================================
-- 10. APURAÇÃO IPI
-- =========================================
CREATE TABLE apuracao_ipi (
    id SERIAL PRIMARY KEY,
    empresa_cnpj CHAR(14),
    periodo_ano INT,
    periodo_mes INT,
    total_debitos NUMERIC(15,2),
    total_creditos NUMERIC(15,2),
    saldo_apurado NUMERIC(15,2)
);

-- =========================================
-- 11. INVENTÁRIO
-- =========================================
CREATE TABLE inventario (
    id SERIAL PRIMARY KEY,
    empresa_cnpj CHAR(14),
    periodo_ano INT,
    produto_id INT REFERENCES produtos(id),
    quantidade NUMERIC(15,4),
    valor_unitario NUMERIC(15,6),
    valor_total NUMERIC(15,2)
);

-- =========================================
-- 12. AJUSTES E OBSERVAÇÕES FISCAIS
-- =========================================
CREATE TABLE ajustes_fiscais (
    id SERIAL PRIMARY KEY,
    empresa_cnpj CHAR(14),
    periodo_ano INT,
    periodo_mes INT,
    codigo_ajuste VARCHAR(20),
    descricao TEXT,
    valor NUMERIC(15,2)
);

CREATE TABLE kpis_sped_fiscal (
    id SERIAL PRIMARY KEY,

    -- Identificação
    processamento_id INTEGER NOT NULL,
    cnpj_emitente VARCHAR(14) NOT NULL,
    periodo_ano INTEGER NOT NULL,
    periodo_mes INTEGER NOT NULL,

    -- Operacionais
    total_documentos INTEGER DEFAULT 0,
    total_itens INTEGER DEFAULT 0,
    total_cfop_distintos INTEGER DEFAULT 0,
    total_ncm_distintos INTEGER DEFAULT 0,
    total_participantes INTEGER DEFAULT 0,

    -- Financeiros
    valor_total_entradas NUMERIC(15,2) DEFAULT 0,
    valor_total_saidas NUMERIC(15,2) DEFAULT 0,
    valor_total_produtos NUMERIC(15,2) DEFAULT 0,
    valor_total_frete NUMERIC(15,2) DEFAULT 0,
    valor_total_descontos NUMERIC(15,2) DEFAULT 0,

    -- ICMS
    icms_base_calculo NUMERIC(15,2) DEFAULT 0,
    icms_valor_debitado NUMERIC(15,2) DEFAULT 0,
    icms_valor_creditado NUMERIC(15,2) DEFAULT 0,
    icms_valor_st NUMERIC(15,2) DEFAULT 0,
    icms_isento NUMERIC(15,2) DEFAULT 0,
    icms_outros NUMERIC(15,2) DEFAULT 0,

    -- IPI
    ipi_base_calculo NUMERIC(15,2) DEFAULT 0,
    ipi_valor NUMERIC(15,2) DEFAULT 0,

    -- Indicadores analíticos
    ticket_medio NUMERIC(15,2) DEFAULT 0,
    percentual_icms_sobre_saida NUMERIC(5,2) DEFAULT 0,

    -- Auditoria
    data_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (cnpj_emitente, periodo_ano, periodo_mes)
);