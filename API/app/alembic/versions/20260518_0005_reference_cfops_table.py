"""reference cfops table

Revision ID: 20260518_0005
Revises: 20260515_0004
Create Date: 2026-05-18
"""

from alembic import op


revision = "20260518_0005"
down_revision = "20260515_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.notas_cfops (
            codigo VARCHAR(10) PRIMARY KEY,
            descricao TEXT NOT NULL,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        ALTER TABLE public.notas_cfops
            ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW();

        ALTER TABLE public.notas_cfops
            ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW();

        CREATE INDEX IF NOT EXISTS idx_notas_cfops_descricao
        ON public.notas_cfops (descricao);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.notas_cfops;")
