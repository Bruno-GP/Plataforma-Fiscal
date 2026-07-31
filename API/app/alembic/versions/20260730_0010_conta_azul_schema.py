"""conta azul schema (integracoes por empresa)

Revision ID: 20260730_0010
Revises: 20260730_0009
Create Date: 2026-07-30
"""

from alembic import op


revision = "20260730_0010"
down_revision = "20260730_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS conta_azul;

        CREATE TABLE IF NOT EXISTS conta_azul.integracoes (
            id BIGSERIAL PRIMARY KEY,
            empresa_id BIGINT NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
            access_token_encrypted TEXT,
            refresh_token_encrypted TEXT,
            token_expira_em TIMESTAMPTZ,
            oauth_state VARCHAR(255),
            oauth_state_expira_em TIMESTAMPTZ,
            erro_mensagem TEXT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_conta_azul_integracoes_empresa UNIQUE (empresa_id)
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS conta_azul.integracoes;
        DROP SCHEMA IF EXISTS conta_azul;
        """
    )
