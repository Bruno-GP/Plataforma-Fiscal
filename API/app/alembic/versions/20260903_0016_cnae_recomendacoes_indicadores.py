"""cria tabelas de recomendacoes de indicadores por CNAE

Revision ID: 20260903_0016
Revises: 20260819_0015
Create Date: 2026-09-03
"""

from alembic import op


revision = "20260903_0016"
down_revision = "20260819_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.segmentos_cnae (
            id              BIGSERIAL       PRIMARY KEY,
            segmento_chave  VARCHAR(80)     NOT NULL,
            segmento_nome   VARCHAR(120)    NOT NULL,
            cnae_prefixo    VARCHAR(7),
            cnae_codigo     VARCHAR(7),
            prioridade      INTEGER         NOT NULL DEFAULT 100,
            ativo           BOOLEAN         NOT NULL DEFAULT TRUE,
            criado_em       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            atualizado_em   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_segmentos_cnae_alvo
                CHECK (
                    (cnae_codigo IS NOT NULL AND BTRIM(cnae_codigo) <> '')
                    OR (cnae_prefixo IS NOT NULL AND BTRIM(cnae_prefixo) <> '')
                )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS uq_segmentos_cnae_codigo
            ON public.segmentos_cnae (cnae_codigo)
            WHERE cnae_codigo IS NOT NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_segmentos_cnae_prefixo
            ON public.segmentos_cnae (cnae_prefixo)
            WHERE cnae_prefixo IS NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_segmentos_cnae_lookup
            ON public.segmentos_cnae (ativo, prioridade, cnae_codigo, cnae_prefixo);

        CREATE TABLE IF NOT EXISTS public.indicador_segmento_recomendacao (
            id              BIGSERIAL       PRIMARY KEY,
            segmento_chave  VARCHAR(80)     NOT NULL,
            indicador_id    BIGINT          NOT NULL REFERENCES public.indicadores(id) ON DELETE CASCADE,
            perfil          VARCHAR(10)     NOT NULL DEFAULT 'xml',
            prioridade      INTEGER         NOT NULL DEFAULT 100,
            motivo          TEXT,
            obrigatorio     BOOLEAN         NOT NULL DEFAULT FALSE,
            ativo           BOOLEAN         NOT NULL DEFAULT TRUE,
            criado_em       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            atualizado_em   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_indicador_segmento_recomendacao_perfil
                CHECK (perfil IN ('xml', 'sped', 'ambos')),
            CONSTRAINT uq_indicador_segmento_recomendacao
                UNIQUE (segmento_chave, indicador_id, perfil)
        );

        CREATE INDEX IF NOT EXISTS idx_indicador_segmento_recomendacao_busca
            ON public.indicador_segmento_recomendacao (segmento_chave, perfil, ativo, prioridade);

        CREATE INDEX IF NOT EXISTS idx_indicador_segmento_recomendacao_indicador
            ON public.indicador_segmento_recomendacao (indicador_id);

        CREATE TABLE IF NOT EXISTS public.empresa_indicador_recomendado (
            id              BIGSERIAL       PRIMARY KEY,
            empresa_id      BIGINT          NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
            indicador_id    BIGINT          NOT NULL REFERENCES public.indicadores(id) ON DELETE CASCADE,
            segmento_chave  VARCHAR(80),
            origem          VARCHAR(20)     NOT NULL DEFAULT 'cnae',
            status          VARCHAR(20)     NOT NULL DEFAULT 'sugerido',
            score           NUMERIC(6,3)    NOT NULL DEFAULT 0,
            motivo          TEXT,
            criado_em       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            atualizado_em   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_empresa_indicador_recomendado_origem
                CHECK (origem IN ('cnae', 'usuario', 'sistema', 'dados_reais')),
            CONSTRAINT ck_empresa_indicador_recomendado_status
                CHECK (status IN ('sugerido', 'aceito', 'ocultado')),
            CONSTRAINT ck_empresa_indicador_recomendado_score
                CHECK (score >= 0 AND score <= 100),
            CONSTRAINT uq_empresa_indicador_recomendado
                UNIQUE (empresa_id, indicador_id)
        );

        CREATE INDEX IF NOT EXISTS idx_empresa_indicador_recomendado_empresa_status
            ON public.empresa_indicador_recomendado (empresa_id, status);

        CREATE INDEX IF NOT EXISTS idx_empresa_indicador_recomendado_segmento
            ON public.empresa_indicador_recomendado (segmento_chave);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS public.empresa_indicador_recomendado;
        DROP TABLE IF EXISTS public.indicador_segmento_recomendacao;
        DROP TABLE IF EXISTS public.segmentos_cnae;
        """
    )
