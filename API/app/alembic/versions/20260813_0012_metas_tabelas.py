"""cria tabelas do modulo Metas: indicadores, indicador_historico, metas

Revision ID: 20260813_0012
Revises: 20260731_0011
Create Date: 2026-08-13
"""

from alembic import op


revision = "20260813_0012"
down_revision = "20260731_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS indicadores (
            id              BIGSERIAL       PRIMARY KEY,
            chave           VARCHAR(50)     NOT NULL UNIQUE,
            nome            VARCHAR(120)    NOT NULL,
            unidade         VARCHAR(20)     NOT NULL CHECK (unidade IN ('moeda','percentual','numero','dias')),
            fonte           VARCHAR(50)     NOT NULL DEFAULT 'notas_kpis',
            direcao_boa     VARCHAR(20)     NOT NULL CHECK (direcao_boa IN ('maior_melhor','menor_melhor')),
            perfil          VARCHAR(10)     NOT NULL DEFAULT 'xml' CHECK (perfil IN ('xml','sped')),
            ativo           BOOLEAN         NOT NULL DEFAULT TRUE,
            criado_em       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS indicador_historico (
            id                  BIGSERIAL       PRIMARY KEY,
            empresa_id          BIGINT          NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            indicador_id        BIGINT          NOT NULL REFERENCES indicadores(id) ON DELETE CASCADE,
            periodo_referencia  DATE            NOT NULL,
            valor               NUMERIC(18,2)   NOT NULL,
            calculado_em        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            UNIQUE (empresa_id, indicador_id, periodo_referencia)
        );

        CREATE INDEX IF NOT EXISTS idx_indicador_historico_busca
            ON indicador_historico (empresa_id, indicador_id, periodo_referencia);

        CREATE TABLE IF NOT EXISTS metas (
            id              BIGSERIAL       PRIMARY KEY,
            empresa_id      BIGINT          NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            indicador_id    BIGINT          NOT NULL REFERENCES indicadores(id),
            titulo          VARCHAR(200)    NOT NULL,
            descricao       TEXT,
            valor_alvo      NUMERIC(18,2)   NOT NULL,
            tipo_meta       VARCHAR(20)     NOT NULL CHECK (tipo_meta IN ('crescimento','reducao','manutencao')),
            periodo_tipo    VARCHAR(20)     NOT NULL CHECK (periodo_tipo IN ('mensal','trimestral','anual','custom')),
            periodo_inicio  DATE            NOT NULL,
            periodo_fim     DATE            NOT NULL,
            status          VARCHAR(20)     NOT NULL DEFAULT 'ativa' CHECK (status IN ('ativa','atingida','nao_atingida','cancelada')),
            criado_por      BIGINT          NOT NULL REFERENCES login(id),
            criado_em       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            atualizado_em   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            CHECK (periodo_fim >= periodo_inicio)
        );

        CREATE INDEX IF NOT EXISTS idx_metas_empresa_status ON metas (empresa_id, status);

        INSERT INTO indicadores (chave, nome, unidade, fonte, direcao_boa, perfil) VALUES
            ('faturamento', 'Faturamento', 'moeda', 'notas_kpis', 'maior_melhor', 'xml'),
            ('ticket_medio', 'Ticket medio', 'moeda', 'notas_kpis', 'maior_melhor', 'xml'),
            ('quantidade_notas', 'Quantidade de notas', 'numero', 'notas_kpis', 'maior_melhor', 'xml'),
            ('total_icms', 'ICMS pago', 'moeda', 'notas_kpis', 'menor_melhor', 'xml'),
            ('total_ipi', 'IPI pago', 'moeda', 'notas_kpis', 'menor_melhor', 'xml'),
            ('total_pis_cofins', 'PIS+COFINS pago', 'moeda', 'notas_kpis', 'menor_melhor', 'xml')
        ON CONFLICT (chave) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS metas;
        DROP TABLE IF EXISTS indicador_historico;
        DROP TABLE IF EXISTS indicadores;
        """
    )
