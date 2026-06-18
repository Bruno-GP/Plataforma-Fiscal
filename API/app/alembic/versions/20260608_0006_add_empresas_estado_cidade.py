"""add estado and cidade to empresas

Revision ID: 20260608_0006
Revises: 20260518_0005
Create Date: 2026-06-08
"""

from alembic import op


revision = "20260608_0006"
down_revision = "20260518_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.empresas
        ADD COLUMN IF NOT EXISTS estado CHAR(2);

        ALTER TABLE public.empresas
        ADD COLUMN IF NOT EXISTS cidade VARCHAR(120);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.empresas
        DROP COLUMN IF EXISTS cidade;

        ALTER TABLE public.empresas
        DROP COLUMN IF EXISTS estado;
        """
    )
