"""adiciona processado_fiscal_em em sefaz.documentos

Revision ID: 20260818_0014
Revises: 20260814_0013
Create Date: 2026-08-18
"""

from alembic import op


revision = "20260818_0014"
down_revision = "20260814_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE sefaz.documentos
            ADD COLUMN processado_fiscal_em TIMESTAMPTZ NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE sefaz.documentos
            DROP COLUMN IF EXISTS processado_fiscal_em;
        """
    )
