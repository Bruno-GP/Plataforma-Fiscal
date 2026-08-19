"""adiciona cnae_fiscal e cnae_fiscal_descricao em empresas

Revision ID: 20260819_0015
Revises: 20260818_0014
Create Date: 2026-08-19
"""

from alembic import op


revision = "20260819_0015"
down_revision = "20260818_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE empresas
            ADD COLUMN IF NOT EXISTS cnae_fiscal VARCHAR(10),
            ADD COLUMN IF NOT EXISTS cnae_fiscal_descricao TEXT;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE empresas
            DROP COLUMN IF EXISTS cnae_fiscal_descricao,
            DROP COLUMN IF EXISTS cnae_fiscal;
        """
    )
