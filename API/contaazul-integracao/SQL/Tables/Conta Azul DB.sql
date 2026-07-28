-- =========================================================
-- CONTA AZUL — TABELAS SEM SCHEMA SEPARADO
-- Adaptado para o banco Fiscal existente.
--
-- DECISÕES DE DESIGN:
-- 1. Sem schema conta_azul — todas as tabelas usam prefixo conta_azul_
-- 2. conta_azul_empresas NÃO existe — empresa_id é BIGINT FK para empresas(id)
--    (tabela empresas já existe no banco Fiscal)
-- 3. conta_azul_notas_fiscais mantém nome próprio — não conflita com notas
-- 4. Sem venda_pagamentos (modelo incorreto) — substituída por
--    conta_azul_eventos_financeiros + conta_azul_parcelas
-- 5. Triggers set_updated_at usam nome único para não conflitar com outros triggers
-- =========================================================

BEGIN;

-- =========================================================
-- FUNCAO set_updated_at (prefixada para não conflitar)
-- =========================================================
CREATE OR REPLACE FUNCTION ca_set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- =========================================================
-- INTEGRACOES
-- Tokens OAuth2 por empresa. empresa_id → empresas(id) existente.
-- Tokens devem ser criptografados pela aplicação antes de gravar.
-- =========================================================
CREATE TABLE IF NOT EXISTS conta_azul_integracoes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id          BIGINT NOT NULL,
    access_token        TEXT,
    refresh_token       TEXT,
    token_expira_em     TIMESTAMPTZ,
    status              VARCHAR(30) NOT NULL DEFAULT 'ATIVA',
    ultimo_sync_em      TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ca_integracoes_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT ck_ca_integracoes_status
        CHECK (status IN ('ATIVA', 'EXPIRADA', 'REVOGADA', 'ERRO', 'DESCONECTADA')),
    CONSTRAINT uq_ca_integracoes_empresa
        UNIQUE (empresa_id)
);

COMMENT ON TABLE conta_azul_integracoes
    IS 'Credenciais OAuth2 da integração Conta Azul por empresa. Uma linha por empresa conectada.';
COMMENT ON COLUMN conta_azul_integracoes.empresa_id
    IS 'FK para empresas(id) — tabela existente no banco Fiscal.';

-- =========================================================
-- SINCRONIZACOES
-- Log de cada execução de sync por entidade.
-- =========================================================
CREATE TABLE IF NOT EXISTS conta_azul_sincronizacoes (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id              BIGINT NOT NULL,
    entidade                VARCHAR(50) NOT NULL,
    inicio_em               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fim_em                  TIMESTAMPTZ,
    status                  VARCHAR(30) NOT NULL DEFAULT 'EM_PROCESSAMENTO',
    registros_processados   INTEGER NOT NULL DEFAULT 0,
    erro                    TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ca_sincronizacoes_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT ck_ca_sincronizacoes_status
        CHECK (status IN ('EM_PROCESSAMENTO', 'SUCESSO', 'SUCESSO_PARCIAL', 'ERRO', 'CANCELADA')),
    CONSTRAINT ck_ca_sincronizacoes_registros
        CHECK (registros_processados >= 0)
);

COMMENT ON TABLE conta_azul_sincronizacoes
    IS 'Histórico de execuções de sincronização por empresa e entidade. Usado para delta sync e auditoria.';

-- =========================================================
-- INTEGRACAO PAYLOADS
-- Raw JSONB de cada registro recebido da API.
-- Permite reprocessamento sem re-chamar a API.
-- =========================================================
CREATE TABLE IF NOT EXISTS conta_azul_integracao_payloads (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id              BIGINT NOT NULL,
    sincronizacao_id        UUID,
    entidade                VARCHAR(50) NOT NULL,
    identificador_externo   VARCHAR(100),
    payload_jsonb           JSONB NOT NULL,
    hash_payload            VARCHAR(64),
    recebido_em             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ca_payloads_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_ca_payloads_sincronizacao
        FOREIGN KEY (sincronizacao_id) REFERENCES conta_azul_sincronizacoes(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT uq_ca_payloads_registro
        UNIQUE (empresa_id, entidade, identificador_externo, hash_payload)
);

COMMENT ON TABLE conta_azul_integracao_payloads
    IS 'Payloads JSONB brutos para auditoria e reprocessamento. hash_payload detecta mudanças entre syncs.';

-- =========================================================
-- PESSOAS (clientes e fornecedores)
-- =========================================================
CREATE TABLE IF NOT EXISTS conta_azul_pessoas (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id              BIGINT NOT NULL,
    conta_azul_id           UUID NOT NULL,
    nome                    VARCHAR(255) NOT NULL,
    documento               VARCHAR(20),
    -- Normalizar para FISICA/JURIDICA/ESTRANGEIRA no Python antes de inserir
    -- (API retorna "Física" e "Jurídica" com acento)
    tipo_pessoa             VARCHAR(20),
    email                   VARCHAR(255),
    telefone                VARCHAR(30),
    ativo                   BOOLEAN NOT NULL DEFAULT TRUE,
    id_legado               BIGINT,
    uuid_legado             UUID,
    data_criacao_origem     TIMESTAMPTZ,
    data_alteracao_origem   TIMESTAMPTZ,
    sincronizado_em         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ca_pessoas_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT uq_ca_pessoas_empresa_ca_id
        UNIQUE (empresa_id, conta_azul_id),
    CONSTRAINT ck_ca_pessoas_tipo
        CHECK (tipo_pessoa IS NULL OR tipo_pessoa IN ('FISICA', 'JURIDICA', 'ESTRANGEIRA'))
);

COMMENT ON COLUMN conta_azul_pessoas.conta_azul_id
    IS 'UUID retornado pelo Conta Azul — chave de idempotência no sync.';
COMMENT ON COLUMN conta_azul_pessoas.tipo_pessoa
    IS 'Normalizado para FISICA/JURIDICA/ESTRANGEIRA. A API retorna "Física"/"Jurídica" com acento.';

-- Perfis normalizados (uma pessoa pode ser cliente E fornecedor)
CREATE TABLE IF NOT EXISTS conta_azul_perfis (
    id      SMALLSERIAL PRIMARY KEY,
    nome    VARCHAR(50) NOT NULL,
    CONSTRAINT uq_ca_perfis_nome UNIQUE (nome)
);

INSERT INTO conta_azul_perfis (nome)
VALUES ('CLIENTE'), ('FORNECEDOR'), ('VENDEDOR'), ('TRANSPORTADOR'), ('PARCEIRO')
ON CONFLICT (nome) DO NOTHING;

CREATE TABLE IF NOT EXISTS conta_azul_pessoa_perfis (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pessoa_id   UUID NOT NULL,
    perfil_id   SMALLINT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ca_pessoa_perfis_pessoa
        FOREIGN KEY (pessoa_id) REFERENCES conta_azul_pessoas(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_ca_pessoa_perfis_perfil
        FOREIGN KEY (perfil_id) REFERENCES conta_azul_perfis(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT uq_ca_pessoa_perfis
        UNIQUE (pessoa_id, perfil_id)
);

-- =========================================================
-- CATEGORIAS FINANCEIRAS (hierárquicas — auto-referência)
-- =========================================================
CREATE TABLE IF NOT EXISTS conta_azul_categorias (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id          BIGINT NOT NULL,
    conta_azul_id       UUID NOT NULL,
    categoria_pai_id    UUID,
    nome                VARCHAR(255) NOT NULL,
    tipo                VARCHAR(20) NOT NULL,
    entrada_dre         VARCHAR(100),
    considera_custo_dre BOOLEAN NOT NULL DEFAULT FALSE,
    versao              INTEGER NOT NULL DEFAULT 0,
    sincronizado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ca_categorias_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_ca_categorias_pai
        FOREIGN KEY (categoria_pai_id) REFERENCES conta_azul_categorias(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT uq_ca_categorias_empresa_ca_id
        UNIQUE (empresa_id, conta_azul_id),
    CONSTRAINT ck_ca_categorias_tipo
        CHECK (tipo IN ('RECEITA', 'DESPESA')),
    CONSTRAINT ck_ca_categorias_versao
        CHECK (versao >= 0),
    CONSTRAINT ck_ca_categorias_nao_auto_pai
        CHECK (categoria_pai_id IS NULL OR categoria_pai_id <> id)
);

COMMENT ON COLUMN conta_azul_categorias.categoria_pai_id
    IS 'Auto-referência para hierarquia de categorias. NULL = categoria raiz.';

-- =========================================================
-- PRODUTOS E SERVICOS
-- fiscal_enriquecido = FALSE até chamar GET /v1/produtos/{id}
-- =========================================================
CREATE TABLE IF NOT EXISTS conta_azul_produtos (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id                  BIGINT NOT NULL,
    conta_azul_id               UUID NOT NULL,
    id_legado                   BIGINT,
    nome                        VARCHAR(255) NOT NULL,
    codigo_sku                  VARCHAR(100),
    codigo_ean                  VARCHAR(30),
    -- Enum completo da API: PRODUTO, SERVICO, ATIVOS_IMOBILIZADOS, FINANCEIRO, KIT_PRODUTOS
    tipo                        VARCHAR(30) NOT NULL,
    status                      VARCHAR(20) NOT NULL DEFAULT 'ATIVO',
    estoque                     NUMERIC(18,4) NOT NULL DEFAULT 0,
    valor_venda                 NUMERIC(18,2) NOT NULL DEFAULT 0,
    custo_medio                 NUMERIC(18,4) NOT NULL DEFAULT 0,
    nivel_estoque               VARCHAR(30),
    estoque_minimo              NUMERIC(18,4) NOT NULL DEFAULT 0,
    estoque_maximo              NUMERIC(18,4),
    movimentado                 BOOLEAN,
    id_pai                      UUID,
    integracao_ecommerce_ativa  BOOLEAN,
    -- Dados fiscais do endpoint GET /v1/produtos/{id}
    fiscal_ncm_codigo           VARCHAR(20),
    fiscal_ncm_descricao        VARCHAR(500),
    fiscal_cest_codigo          VARCHAR(20),
    fiscal_cest_descricao       VARCHAR(500),
    fiscal_origem               VARCHAR(100),
    fiscal_tipo_produto         VARCHAR(100),
    fiscal_unidade_medida       VARCHAR(50),
    -- FALSE = só listagem básica. TRUE = detalhe fiscal já carregado.
    fiscal_enriquecido          BOOLEAN NOT NULL DEFAULT FALSE,
    atualizado_em_origem        TIMESTAMPTZ,
    sincronizado_em             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ca_produtos_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_ca_produtos_pai
        FOREIGN KEY (id_pai) REFERENCES conta_azul_produtos(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT uq_ca_produtos_empresa_ca_id
        UNIQUE (empresa_id, conta_azul_id),
    CONSTRAINT ck_ca_produtos_tipo
        CHECK (tipo IN ('PRODUTO', 'SERVICO', 'ATIVOS_IMOBILIZADOS', 'FINANCEIRO', 'KIT_PRODUTOS')),
    CONSTRAINT ck_ca_produtos_status
        CHECK (status IN ('ATIVO', 'INATIVO')),
    CONSTRAINT ck_ca_produtos_valores
        CHECK (estoque_minimo >= 0
            AND (estoque_maximo IS NULL OR estoque_maximo >= 0)
            AND valor_venda >= 0
            AND custo_medio >= 0),
    CONSTRAINT ck_ca_produtos_nao_auto_pai
        CHECK (id_pai IS NULL OR id_pai <> id)
);

COMMENT ON COLUMN conta_azul_produtos.fiscal_enriquecido
    IS 'FALSE = só listagem básica sincronizada. TRUE = detalhe fiscal (NCM/CEST/origem) carregado via GET /v1/produtos/{id}.';
COMMENT ON COLUMN conta_azul_produtos.fiscal_ncm_codigo
    IS 'Fonte: GET /v1/produtos/{id} → fiscal.ncm.codigo. Pode ser cruzado com ncm_catalogo(codigo).';
COMMENT ON COLUMN conta_azul_produtos.fiscal_cest_codigo
    IS 'Fonte: GET /v1/produtos/{id} → fiscal.cest.codigo.';

-- =========================================================
-- VENDAS
-- =========================================================
CREATE TABLE IF NOT EXISTS conta_azul_vendas (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id              BIGINT NOT NULL,
    conta_azul_id           UUID NOT NULL,
    id_legado               BIGINT,
    numero                  BIGINT,
    data                    DATE NOT NULL,
    tipo                    VARCHAR(30) NOT NULL,
    origem                  VARCHAR(255),
    total                   NUMERIC(18,2) NOT NULL DEFAULT 0,
    situacao_nome           VARCHAR(50),
    situacao_descricao      VARCHAR(255),
    cliente_id              UUID,
    versao                  INTEGER NOT NULL DEFAULT 0,
    criado_em_origem        TIMESTAMPTZ,
    data_alteracao_origem   TIMESTAMPTZ,
    sincronizado_em         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ca_vendas_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_ca_vendas_cliente
        FOREIGN KEY (cliente_id) REFERENCES conta_azul_pessoas(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT uq_ca_vendas_empresa_ca_id
        UNIQUE (empresa_id, conta_azul_id),
    CONSTRAINT ck_ca_vendas_total  CHECK (total >= 0),
    CONSTRAINT ck_ca_vendas_versao CHECK (versao >= 0)
);

-- =========================================================
-- VENDA ITENS
-- =========================================================
CREATE TABLE IF NOT EXISTS conta_azul_venda_itens (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venda_id            UUID NOT NULL,
    conta_azul_item_id  UUID,
    produto_id          UUID,
    nome                VARCHAR(255),
    descricao           VARCHAR(500),
    tipo                VARCHAR(30),
    quantidade          NUMERIC(18,4) NOT NULL,
    valor_unitario      NUMERIC(18,4) NOT NULL,
    custo               NUMERIC(18,4),
    desconto            NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_total         NUMERIC(18,2) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ca_venda_itens_venda
        FOREIGN KEY (venda_id) REFERENCES conta_azul_vendas(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_ca_venda_itens_produto
        FOREIGN KEY (produto_id) REFERENCES conta_azul_produtos(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT ck_ca_venda_itens_tipo
        CHECK (tipo IS NULL OR tipo IN ('PRODUTO', 'SERVICO', 'ATIVOS_IMOBILIZADOS', 'FINANCEIRO', 'KIT_PRODUTOS')),
    CONSTRAINT ck_ca_venda_itens_valores
        CHECK (quantidade > 0 AND valor_unitario >= 0 AND desconto >= 0 AND valor_total >= 0)
);

-- =========================================================
-- EVENTOS FINANCEIROS
-- Camada real entre venda e parcelas na API Conta Azul.
-- referencia_origem: VENDA, COMPRA, DAS, FOLHA etc.
-- =========================================================
CREATE TABLE IF NOT EXISTS conta_azul_eventos_financeiros (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id          BIGINT NOT NULL,
    conta_azul_id       UUID NOT NULL,
    tipo                VARCHAR(20) NOT NULL,
    referencia_origem   VARCHAR(50),
    referencia_id       UUID,
    venda_id            UUID,
    data_competencia    DATE,
    qtd_parcelas        INTEGER,
    agendado            BOOLEAN,
    codigo_referencia   VARCHAR(100),
    sincronizado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ca_eventos_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_ca_eventos_venda
        FOREIGN KEY (venda_id) REFERENCES conta_azul_vendas(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT uq_ca_eventos_empresa_ca_id
        UNIQUE (empresa_id, conta_azul_id),
    CONSTRAINT ck_ca_eventos_tipo
        CHECK (tipo IN ('RECEITA', 'DESPESA')),
    CONSTRAINT ck_ca_eventos_origem
        CHECK (referencia_origem IS NULL OR referencia_origem IN (
            'LANCAMENTO_FINANCEIRO', 'DAS', 'FOLHA', 'TRANSFERENCIA',
            'SALDO_CONTA_BANCARIA', 'VENDA', 'COMPRA', 'VENDA_AGENDADA',
            'COMPRA_AGENDADA', 'IMPORTACAO_DOCUMENTO', 'IMPOSTO_RETIDO',
            'SIC', 'NOTA_COMPRA', 'ANTECIPACAO', 'RENEGOCIACAO', 'HONORARIOS_CONTABEIS'
        ))
);

COMMENT ON TABLE conta_azul_eventos_financeiros
    IS 'Camada intermediária entre vendas e parcelas. referencia_origem indica a origem do evento.';

-- Rateio por categoria dentro de um evento
CREATE TABLE IF NOT EXISTS conta_azul_evento_rateios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evento_id       UUID NOT NULL,
    categoria_id    UUID,
    nome_categoria  VARCHAR(255),
    valor           NUMERIC(18,2),
    valor_bruto     NUMERIC(18,2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ca_rateios_evento
        FOREIGN KEY (evento_id) REFERENCES conta_azul_eventos_financeiros(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_ca_rateios_categoria
        FOREIGN KEY (categoria_id) REFERENCES conta_azul_categorias(id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

-- =========================================================
-- PARCELAS
-- Substitui venda_pagamentos. Reflete o modelo real da API.
-- =========================================================
CREATE TABLE IF NOT EXISTS conta_azul_parcelas (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id                  BIGINT NOT NULL,
    conta_azul_id               UUID NOT NULL,
    evento_id                   UUID NOT NULL,
    indice                      INTEGER,
    status                      VARCHAR(30) NOT NULL DEFAULT 'PENDENTE',
    valor_bruto                 NUMERIC(18,2),
    valor_liquido               NUMERIC(18,2),
    valor_pago                  NUMERIC(18,2),
    nao_pago                    NUMERIC(18,2),
    multa                       NUMERIC(18,2),
    juros                       NUMERIC(18,2),
    desconto                    NUMERIC(18,2),
    taxa                        NUMERIC(18,2),
    metodo_pagamento            VARCHAR(60),
    data_vencimento             DATE,
    data_pagamento_previsto     DATE,
    descricao                   VARCHAR(500),
    nota                        TEXT,
    conciliado                  BOOLEAN,
    -- Referência à nota fiscal que originou/liquidou esta parcela
    fatura_numero               INTEGER,
    fatura_rps                  INTEGER,
    fatura_tipo                 VARCHAR(10),
    data_alteracao_origem       TIMESTAMPTZ,
    sincronizado_em             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ca_parcelas_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_ca_parcelas_evento
        FOREIGN KEY (evento_id) REFERENCES conta_azul_eventos_financeiros(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT uq_ca_parcelas_empresa_ca_id
        UNIQUE (empresa_id, conta_azul_id),
    CONSTRAINT ck_ca_parcelas_status
        CHECK (status IN (
            'PENDENTE', 'QUITADO', 'CANCELADO', 'RENEGOCIADO',
            'RECEBIDO_PARCIAL', 'ATRASADO', 'PERDIDO'
        )),
    CONSTRAINT ck_ca_parcelas_fatura_tipo
        CHECK (fatura_tipo IS NULL OR fatura_tipo IN ('NFE', 'NFSE', 'NFCE'))
);

COMMENT ON COLUMN conta_azul_parcelas.fatura_tipo
    IS 'Tipo da nota fiscal vinculada à parcela: NFE, NFSE ou NFCE.';

-- =========================================================
-- NOTAS FISCAIS (Conta Azul)
-- Nome intencional: conta_azul_notas_fiscais ≠ notas (NFe do SPED/XML)
-- Duplo vínculo: venda de origem + parcela de liquidação.
-- =========================================================
CREATE TABLE IF NOT EXISTS conta_azul_notas_fiscais (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id      BIGINT NOT NULL,
    conta_azul_id   UUID NOT NULL,
    venda_id        UUID,
    parcela_id      UUID,
    numero          INTEGER,
    rps             INTEGER,
    tipo            VARCHAR(10) NOT NULL,
    status          VARCHAR(50),
    emitido_em      TIMESTAMPTZ,
    sincronizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ca_nf_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_ca_nf_venda
        FOREIGN KEY (venda_id) REFERENCES conta_azul_vendas(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_ca_nf_parcela
        FOREIGN KEY (parcela_id) REFERENCES conta_azul_parcelas(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT uq_ca_nf_empresa_ca_id
        UNIQUE (empresa_id, conta_azul_id),
    CONSTRAINT ck_ca_nf_tipo
        CHECK (tipo IN ('NFE', 'NFSE', 'NFCE'))
);

COMMENT ON TABLE conta_azul_notas_fiscais
    IS 'NF-e, NFS-e e NFC-e gerenciadas pelo Conta Azul. Diferente de notas (NF-e de XML/SPED).';

-- =========================================================
-- INDICES
-- =========================================================

-- integracoes
CREATE INDEX IF NOT EXISTS idx_ca_integracoes_empresa
    ON conta_azul_integracoes (empresa_id);

-- sincronizacoes
CREATE INDEX IF NOT EXISTS idx_ca_sync_empresa_entidade_inicio
    ON conta_azul_sincronizacoes (empresa_id, entidade, inicio_em DESC);

-- payloads
CREATE INDEX IF NOT EXISTS idx_ca_payloads_empresa_entidade
    ON conta_azul_integracao_payloads (empresa_id, entidade);
CREATE INDEX IF NOT EXISTS idx_ca_payloads_jsonb
    ON conta_azul_integracao_payloads USING GIN (payload_jsonb);

-- pessoas
CREATE INDEX IF NOT EXISTS idx_ca_pessoas_empresa_nome
    ON conta_azul_pessoas (empresa_id, nome);
CREATE INDEX IF NOT EXISTS idx_ca_pessoas_empresa_doc
    ON conta_azul_pessoas (empresa_id, documento)
    WHERE documento IS NOT NULL AND documento <> '';

-- categorias
CREATE INDEX IF NOT EXISTS idx_ca_categorias_empresa_tipo
    ON conta_azul_categorias (empresa_id, tipo);
CREATE INDEX IF NOT EXISTS idx_ca_categorias_pai
    ON conta_azul_categorias (categoria_pai_id);

-- produtos
CREATE INDEX IF NOT EXISTS idx_ca_produtos_empresa_nome
    ON conta_azul_produtos (empresa_id, nome);
CREATE INDEX IF NOT EXISTS idx_ca_produtos_empresa_sku
    ON conta_azul_produtos (empresa_id, codigo_sku)
    WHERE codigo_sku IS NOT NULL AND codigo_sku <> '';
CREATE INDEX IF NOT EXISTS idx_ca_produtos_pai
    ON conta_azul_produtos (id_pai);
-- Busca por NCM (frequente no contexto fiscal — liga com ncm_catalogo)
CREATE INDEX IF NOT EXISTS idx_ca_produtos_ncm
    ON conta_azul_produtos (fiscal_ncm_codigo)
    WHERE fiscal_ncm_codigo IS NOT NULL;
-- Fila de enriquecimento fiscal: quais produtos ainda precisam do detalhe
CREATE INDEX IF NOT EXISTS idx_ca_produtos_nao_enriquecidos
    ON conta_azul_produtos (empresa_id, fiscal_enriquecido)
    WHERE fiscal_enriquecido = FALSE;

-- vendas
CREATE INDEX IF NOT EXISTS idx_ca_vendas_empresa_data
    ON conta_azul_vendas (empresa_id, data DESC);
CREATE INDEX IF NOT EXISTS idx_ca_vendas_cliente
    ON conta_azul_vendas (cliente_id);
CREATE INDEX IF NOT EXISTS idx_ca_vendas_situacao
    ON conta_azul_vendas (empresa_id, situacao_nome);

-- venda_itens
CREATE INDEX IF NOT EXISTS idx_ca_venda_itens_venda
    ON conta_azul_venda_itens (venda_id);
CREATE INDEX IF NOT EXISTS idx_ca_venda_itens_produto
    ON conta_azul_venda_itens (produto_id);

-- eventos_financeiros
CREATE INDEX IF NOT EXISTS idx_ca_eventos_empresa_tipo
    ON conta_azul_eventos_financeiros (empresa_id, tipo);
CREATE INDEX IF NOT EXISTS idx_ca_eventos_venda
    ON conta_azul_eventos_financeiros (venda_id);
CREATE INDEX IF NOT EXISTS idx_ca_eventos_origem
    ON conta_azul_eventos_financeiros (empresa_id, referencia_origem);

-- parcelas
CREATE INDEX IF NOT EXISTS idx_ca_parcelas_evento
    ON conta_azul_parcelas (evento_id);
CREATE INDEX IF NOT EXISTS idx_ca_parcelas_status_vencimento
    ON conta_azul_parcelas (empresa_id, status, data_vencimento);

-- notas_fiscais
CREATE INDEX IF NOT EXISTS idx_ca_nf_venda
    ON conta_azul_notas_fiscais (venda_id);
CREATE INDEX IF NOT EXISTS idx_ca_nf_parcela
    ON conta_azul_notas_fiscais (parcela_id);
CREATE INDEX IF NOT EXISTS idx_ca_nf_empresa_tipo
    ON conta_azul_notas_fiscais (empresa_id, tipo);

-- =========================================================
-- TRIGGERS DE updated_at
-- =========================================================
DROP TRIGGER IF EXISTS trg_ca_integracoes_upd ON conta_azul_integracoes;
CREATE TRIGGER trg_ca_integracoes_upd
BEFORE UPDATE ON conta_azul_integracoes
FOR EACH ROW EXECUTE FUNCTION ca_set_updated_at();

DROP TRIGGER IF EXISTS trg_ca_pessoas_upd ON conta_azul_pessoas;
CREATE TRIGGER trg_ca_pessoas_upd
BEFORE UPDATE ON conta_azul_pessoas
FOR EACH ROW EXECUTE FUNCTION ca_set_updated_at();

DROP TRIGGER IF EXISTS trg_ca_categorias_upd ON conta_azul_categorias;
CREATE TRIGGER trg_ca_categorias_upd
BEFORE UPDATE ON conta_azul_categorias
FOR EACH ROW EXECUTE FUNCTION ca_set_updated_at();

DROP TRIGGER IF EXISTS trg_ca_produtos_upd ON conta_azul_produtos;
CREATE TRIGGER trg_ca_produtos_upd
BEFORE UPDATE ON conta_azul_produtos
FOR EACH ROW EXECUTE FUNCTION ca_set_updated_at();

DROP TRIGGER IF EXISTS trg_ca_vendas_upd ON conta_azul_vendas;
CREATE TRIGGER trg_ca_vendas_upd
BEFORE UPDATE ON conta_azul_vendas
FOR EACH ROW EXECUTE FUNCTION ca_set_updated_at();

DROP TRIGGER IF EXISTS trg_ca_venda_itens_upd ON conta_azul_venda_itens;
CREATE TRIGGER trg_ca_venda_itens_upd
BEFORE UPDATE ON conta_azul_venda_itens
FOR EACH ROW EXECUTE FUNCTION ca_set_updated_at();

DROP TRIGGER IF EXISTS trg_ca_eventos_upd ON conta_azul_eventos_financeiros;
CREATE TRIGGER trg_ca_eventos_upd
BEFORE UPDATE ON conta_azul_eventos_financeiros
FOR EACH ROW EXECUTE FUNCTION ca_set_updated_at();

DROP TRIGGER IF EXISTS trg_ca_parcelas_upd ON conta_azul_parcelas;
CREATE TRIGGER trg_ca_parcelas_upd
BEFORE UPDATE ON conta_azul_parcelas
FOR EACH ROW EXECUTE FUNCTION ca_set_updated_at();

DROP TRIGGER IF EXISTS trg_ca_nf_upd ON conta_azul_notas_fiscais;
CREATE TRIGGER trg_ca_nf_upd
BEFORE UPDATE ON conta_azul_notas_fiscais
FOR EACH ROW EXECUTE FUNCTION ca_set_updated_at();

COMMIT;