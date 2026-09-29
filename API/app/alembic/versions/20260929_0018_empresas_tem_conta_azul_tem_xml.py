"""garante tem_conta_azul e tem_xml em empresas

Revision ID: 20260929_0018
Revises: 20260903_0017
Create Date: 2026-09-29

As colunas foram adicionadas retroativamente em 20260505_0001, que nao roda
de novo em bancos ja migrados. Esta revision cobre esses bancos; e idempotente
onde as colunas ja existem.
"""

from alembic import op


revision = "20260929_0018"
down_revision = "20260903_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE empresas
            ADD COLUMN IF NOT EXISTS tem_conta_azul BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS tem_xml BOOLEAN NOT NULL DEFAULT FALSE;
        """
    )


def downgrade() -> None:
    # As colunas pertencem ao schema inicial (20260505_0001); nao remover aqui.
    pass
