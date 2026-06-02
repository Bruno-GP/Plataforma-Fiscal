"""add login security columns

Revision ID: 20260515_0004
Revises: 20260511_0003
Create Date: 2026-05-15
"""

from alembic import op


revision = "20260515_0004"
down_revision = "20260511_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.login
        ADD COLUMN IF NOT EXISTS tentativas_falhas INTEGER NOT NULL DEFAULT 0;

        ALTER TABLE public.login
        ADD COLUMN IF NOT EXISTS bloqueado_ate TIMESTAMPTZ;

        ALTER TABLE public.login
        ADD COLUMN IF NOT EXISTS ultimo_login_em TIMESTAMPTZ;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.login
        DROP COLUMN IF EXISTS ultimo_login_em;

        ALTER TABLE public.login
        DROP COLUMN IF EXISTS bloqueado_ate;

        ALTER TABLE public.login
        DROP COLUMN IF EXISTS tentativas_falhas;
        """
    )
