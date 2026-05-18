"""initial fiscal schema

Revision ID: 20260505_0001
Revises:
Create Date: 2026-05-05
"""

from alembic import op


revision = "20260505_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS empresas (
            id BIGSERIAL PRIMARY KEY,
            cnpj VARCHAR(20) NOT NULL UNIQUE,
            nome VARCHAR(255) NOT NULL,
            tem_sped BOOLEAN NOT NULL DEFAULT FALSE
        );

        CREATE TABLE IF NOT EXISTS notas_processamentos (
            id BIGSERIAL PRIMARY KEY,
            empresa_id BIGINT REFERENCES empresas(id) ON DELETE SET NULL,
            origem TEXT,
            pasta_xml TEXT,
            periodo_solicitado TEXT,
            cnpj_emitente TEXT,
            periodo_ano INTEGER,
            periodo_mes INTEGER,
            periodos_encontrados JSONB,
            notas_processadas INTEGER,
            itens_processados INTEGER,
            kpis JSONB,
            erros JSONB,
            status TEXT,
            data_processamento TIMESTAMPTZ
        );

        CREATE TABLE IF NOT EXISTS notas (
            id BIGSERIAL PRIMARY KEY,
            processamento_id BIGINT REFERENCES notas_processamentos(id) ON DELETE SET NULL,
            numero_nf VARCHAR(50) NOT NULL,
            emitente_cnpj VARCHAR(20) NOT NULL,
            modelo VARCHAR(5),
            data_emissao DATE NOT NULL,
            natureza_operacao VARCHAR(255),
            destinatario_documento VARCHAR(20),
            destinatario_nome VARCHAR(255),
            destinatario_cidade VARCHAR(120),
            destinatario_uf CHAR(2),
            valor_produtos NUMERIC(18,2),
            valor_desconto NUMERIC(18,2),
            valor_frete NUMERIC(18,2),
            valor_icms NUMERIC(18,2),
            valor_ipi NUMERIC(18,2),
            valor_pis NUMERIC(18,2),
            valor_cofins NUMERIC(18,2),
            valor_total_nf NUMERIC(18,2),
            criado_em TIMESTAMPTZ DEFAULT NOW(),
            atualizado_em TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS notas_itens (
            id BIGSERIAL PRIMARY KEY,
            nota_id BIGINT NOT NULL REFERENCES notas(id) ON DELETE CASCADE,
            empresa_id BIGINT REFERENCES empresas(id) ON DELETE SET NULL,
            cnpj VARCHAR(20) REFERENCES empresas(cnpj) ON DELETE SET NULL,
            item_numero INT,
            produto_codigo VARCHAR(120),
            descricao VARCHAR(255),
            ncm VARCHAR(20),
            cfop VARCHAR(10),
            quantidade NUMERIC(18,4),
            valor_unitario NUMERIC(18,6),
            valor_total NUMERIC(18,2),
            icms_cst_csosn VARCHAR(10),
            icms_base NUMERIC(18,2),
            icms_aliquota NUMERIC(10,4),
            icms_valor NUMERIC(18,2)
        );

        CREATE TABLE IF NOT EXISTS notas_kpis (
            id BIGSERIAL PRIMARY KEY,
            processamento_id BIGINT NOT NULL REFERENCES notas_processamentos(id) ON DELETE CASCADE,
            emitente_cnpj VARCHAR(14),
            periodo_ano INTEGER,
            periodo_mes INTEGER,
            total_vendas NUMERIC(18,2) DEFAULT 0,
            quantidade_notas INT DEFAULT 0,
            ticket_medio NUMERIC(18,2) DEFAULT 0,
            maior_nota NUMERIC(18,2) DEFAULT 0,
            menor_nota NUMERIC(18,2) DEFAULT 0,
            total_icms NUMERIC(18,2) DEFAULT 0,
            total_ipi NUMERIC(18,2) DEFAULT 0,
            total_pis NUMERIC(18,2) DEFAULT 0,
            total_cofins NUMERIC(18,2) DEFAULT 0,
            top_clientes JSONB DEFAULT '[]'::jsonb,
            top_produtos JSONB DEFAULT '[]'::jsonb,
            top_cidades JSONB DEFAULT '[]'::jsonb
        );

        CREATE TABLE IF NOT EXISTS notas_xml_importados (
            id BIGSERIAL PRIMARY KEY,
            cnpj_emitente VARCHAR(20) NOT NULL,
            nome_arquivo TEXT NOT NULL,
            hash_arquivo VARCHAR(64) NOT NULL,
            tamanho_bytes BIGINT,
            conteudo_xml BYTEA,
            processado_em TIMESTAMPTZ,
            criado_em TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (cnpj_emitente, hash_arquivo)
        );

        CREATE TABLE IF NOT EXISTS login (
            id BIGSERIAL PRIMARY KEY,
            empresa_id BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            cnpj VARCHAR(20) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            senha VARCHAR(255) NOT NULL,
            criado_em TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS sped_importados (
            id BIGSERIAL PRIMARY KEY,
            cnpj_emitente VARCHAR(20) NOT NULL,
            nome_arquivo TEXT NOT NULL,
            hash_arquivo VARCHAR(64) NOT NULL,
            tamanho_bytes BIGINT,
            conteudo_txt BYTEA,
            processado_em TIMESTAMPTZ,
            criado_em TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (cnpj_emitente, hash_arquivo)
        );

        CREATE TABLE IF NOT EXISTS sped_empresas (
            cnpj CHAR(14) PRIMARY KEY,
            razao_social VARCHAR(255),
            ie VARCHAR(20),
            uf CHAR(2),
            cnae VARCHAR(10),
            regime_tributario VARCHAR(30)
        );

        CREATE TABLE IF NOT EXISTS sped_participantes (
            id SERIAL PRIMARY KEY,
            empresa_cnpj CHAR(14),
            codigo VARCHAR(60),
            nome VARCHAR(255),
            cnpj_cpf VARCHAR(14),
            municipio VARCHAR(100),
            municipio_nome VARCHAR(120),
            uf CHAR(2),
            UNIQUE (empresa_cnpj, codigo)
        );

        CREATE TABLE IF NOT EXISTS sped_produtos (
            id SERIAL PRIMARY KEY,
            empresa_cnpj CHAR(14),
            codigo VARCHAR(60),
            descricao VARCHAR(255),
            ncm VARCHAR(10),
            unidade VARCHAR(10),
            tipo_item VARCHAR(10),
            UNIQUE (empresa_cnpj, codigo)
        );

        CREATE TABLE IF NOT EXISTS sped_documentos_fiscais (
            id SERIAL PRIMARY KEY,
            empresa_cnpj CHAR(14),
            participante_id INT,
            modelo INT,
            serie VARCHAR(10),
            numero INT,
            chave_acesso VARCHAR(44),
            tipo_operacao VARCHAR(10),
            data_emissao DATE,
            data_movimentacao DATE,
            valor_total NUMERIC(15,2),
            valor_produtos NUMERIC(15,2),
            valor_frete NUMERIC(15,2),
            valor_desconto NUMERIC(15,2),
            situacao VARCHAR(20),
            origem_importacao_id BIGINT
        );

        CREATE TABLE IF NOT EXISTS sped_documento_itens (
            id SERIAL PRIMARY KEY,
            documento_id INT,
            produto_id INT,
            numero_item INT,
            cfop VARCHAR(4),
            quantidade NUMERIC(15,4),
            valor_unitario NUMERIC(15,6),
            valor_total NUMERIC(15,2),
            desconto NUMERIC(15,2),
            cst_icms VARCHAR(3),
            valor_bc_icms NUMERIC(15,2) DEFAULT 0,
            aliquota_icms NUMERIC(9,4) DEFAULT 0,
            valor_icms NUMERIC(15,2) DEFAULT 0,
            valor_bc_ipi NUMERIC(15,2) DEFAULT 0,
            aliquota_ipi NUMERIC(9,4) DEFAULT 0,
            valor_ipi NUMERIC(15,2) DEFAULT 0,
            valor_pis NUMERIC(15,2) DEFAULT 0,
            valor_cofins NUMERIC(15,2) DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sped_apuracao_icms (
            id SERIAL PRIMARY KEY,
            empresa_cnpj CHAR(14) NOT NULL,
            periodo_ano INTEGER NOT NULL,
            periodo_mes INTEGER NOT NULL,
            total_debitos NUMERIC(15,2) DEFAULT 0,
            ajustes_debitos NUMERIC(15,2) DEFAULT 0,
            total_creditos NUMERIC(15,2) DEFAULT 0,
            ajustes_creditos NUMERIC(15,2) DEFAULT 0,
            saldo_apurado NUMERIC(15,2) DEFAULT 0,
            valor_icms_recolher NUMERIC(15,2) DEFAULT 0,
            saldo_credor_transportar NUMERIC(15,2) DEFAULT 0,
            debitos_especiais NUMERIC(15,2) DEFAULT 0,
            atualizado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_cnpj, periodo_ano, periodo_mes)
        );

        CREATE TABLE IF NOT EXISTS sped_kpis_fiscal (
            id SERIAL PRIMARY KEY,
            processamento_id INTEGER NOT NULL,
            cnpj_emitente VARCHAR(14) NOT NULL,
            periodo_ano INTEGER NOT NULL,
            periodo_mes INTEGER NOT NULL,
            total_documentos INTEGER DEFAULT 0,
            total_itens INTEGER DEFAULT 0,
            valor_total_saidas NUMERIC(15,2) DEFAULT 0,
            valor_total_produtos NUMERIC(15,2) DEFAULT 0,
            valor_total_frete NUMERIC(15,2) DEFAULT 0,
            valor_total_descontos NUMERIC(15,2) DEFAULT 0,
            icms_valor_debitado NUMERIC(15,2) DEFAULT 0,
            ipi_valor NUMERIC(15,2) DEFAULT 0,
            pis_valor NUMERIC(15,2) DEFAULT 0,
            cofins_valor NUMERIC(15,2) DEFAULT 0,
            ticket_medio NUMERIC(15,2) DEFAULT 0,
            data_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (cnpj_emitente, periodo_ano, periodo_mes)
        );

        CREATE TABLE IF NOT EXISTS municipios_catalogo (
            codigo_ibge CHAR(7) PRIMARY KEY,
            nome VARCHAR(255) NOT NULL,
            uf CHAR(2) NOT NULL,
            regiao VARCHAR(20),
            mesorregiao VARCHAR(100),
            microrregiao VARCHAR(100),
            capital BOOLEAN,
            codigo_uf CHAR(2),
            fonte_arquivo VARCHAR(255),
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS ncm_catalogo (
            codigo CHAR(8) PRIMARY KEY,
            descricao TEXT NOT NULL,
            codigo_formatado VARCHAR(20),
            vigencia DATE,
            fonte_arquivo VARCHAR(255),
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS ncm_tributacao (
            id BIGSERIAL PRIMARY KEY,
            ncm_codigo CHAR(8) NOT NULL REFERENCES ncm_catalogo(codigo) ON DELETE CASCADE,
            uf CHAR(2) NOT NULL,
            nacional_federal NUMERIC(6,2),
            importados_federal NUMERIC(6,2),
            estadual NUMERIC(6,2),
            municipal NUMERIC(6,2),
            vigencia_inicio DATE,
            vigencia_fim DATE,
            versao VARCHAR(20),
            fonte VARCHAR(100),
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (ncm_codigo, uf)
        );

        CREATE TABLE IF NOT EXISTS processing_jobs (
            id UUID PRIMARY KEY,
            tipo VARCHAR(80) NOT NULL,
            status VARCHAR(30) NOT NULL,
            mensagem TEXT,
            total_itens INTEGER DEFAULT 0,
            itens_processados INTEGER DEFAULT 0,
            erro TEXT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            iniciado_em TIMESTAMPTZ,
            finalizado_em TIMESTAMPTZ,
            payload JSONB,
            CONSTRAINT ck_processing_jobs_status
                CHECK (status IN ('PENDING', 'QUEUED', 'RUNNING', 'SUCCESS', 'FAILED', 'CANCELED'))
        );

        ALTER TABLE IF EXISTS empresas
            ADD COLUMN IF NOT EXISTS tem_sped BOOLEAN NOT NULL DEFAULT FALSE;

        ALTER TABLE IF EXISTS sped_participantes
            ADD COLUMN IF NOT EXISTS municipio_nome VARCHAR(120),
            ADD COLUMN IF NOT EXISTS uf CHAR(2);

        ALTER TABLE IF EXISTS sped_documentos_fiscais
            ADD COLUMN IF NOT EXISTS origem_importacao_id BIGINT;

        ALTER TABLE IF EXISTS sped_documento_itens
            ADD COLUMN IF NOT EXISTS cst_icms VARCHAR(3),
            ADD COLUMN IF NOT EXISTS valor_bc_icms NUMERIC(15,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS aliquota_icms NUMERIC(9,4) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS valor_icms NUMERIC(15,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS valor_bc_ipi NUMERIC(15,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS aliquota_ipi NUMERIC(9,4) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS valor_ipi NUMERIC(15,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS valor_pis NUMERIC(15,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS valor_cofins NUMERIC(15,2) DEFAULT 0;

        ALTER TABLE IF EXISTS sped_kpis_fiscal
            ADD COLUMN IF NOT EXISTS ipi_valor NUMERIC(15,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS pis_valor NUMERIC(15,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS cofins_valor NUMERIC(15,2) DEFAULT 0;

        ALTER TABLE IF EXISTS sped_apuracao_icms
            ADD COLUMN IF NOT EXISTS total_debitos NUMERIC(15,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS ajustes_debitos NUMERIC(15,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS total_creditos NUMERIC(15,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS ajustes_creditos NUMERIC(15,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS saldo_apurado NUMERIC(15,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS valor_icms_recolher NUMERIC(15,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS saldo_credor_transportar NUMERIC(15,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS debitos_especiais NUMERIC(15,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;

        CREATE INDEX IF NOT EXISTS idx_notas_processamentos_empresa ON notas_processamentos (empresa_id);
        CREATE INDEX IF NOT EXISTS idx_notas_emitente_data ON notas (emitente_cnpj, data_emissao);
        CREATE INDEX IF NOT EXISTS idx_notas_itens_nota ON notas_itens (nota_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_notas_kpis_periodo ON notas_kpis (emitente_cnpj, periodo_ano, periodo_mes);
        CREATE INDEX IF NOT EXISTS idx_notas_xml_importados_cnpj ON notas_xml_importados (cnpj_emitente);
        CREATE UNIQUE INDEX IF NOT EXISTS ux_participantes_empresa_codigo
            ON sped_participantes (empresa_cnpj, codigo);
        CREATE UNIQUE INDEX IF NOT EXISTS ux_produtos_empresa_codigo
            ON sped_produtos (empresa_cnpj, codigo);
        CREATE UNIQUE INDEX IF NOT EXISTS ux_sped_kpis_fiscal_periodo
            ON sped_kpis_fiscal (cnpj_emitente, periodo_ano, periodo_mes);
        CREATE UNIQUE INDEX IF NOT EXISTS ux_sped_apuracao_icms_periodo
            ON sped_apuracao_icms (empresa_cnpj, periodo_ano, periodo_mes);
        CREATE INDEX IF NOT EXISTS idx_sped_documentos_empresa_tipo_data_normalizado
            ON sped_documentos_fiscais ((regexp_replace(COALESCE(empresa_cnpj, ''), '\\D', '', 'g')), tipo_operacao, data_emissao);
        CREATE INDEX IF NOT EXISTS idx_sped_documento_itens_documento ON sped_documento_itens (documento_id);
        CREATE INDEX IF NOT EXISTS idx_sped_documentos_origem_importacao ON sped_documentos_fiscais (origem_importacao_id);
        CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs (status);
        CREATE INDEX IF NOT EXISTS idx_processing_jobs_tipo ON processing_jobs (tipo);
        CREATE INDEX IF NOT EXISTS idx_processing_jobs_criado_em ON processing_jobs (criado_em DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS processing_jobs;")
