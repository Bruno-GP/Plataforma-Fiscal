"""add municipio reference columns to empresas

Revision ID: 20260609_0007
Revises: 20260608_0006
Create Date: 2026-06-09
"""

from alembic import op


revision = "20260609_0007"
down_revision = "20260608_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.empresas
        ADD COLUMN IF NOT EXISTS municipio_id CHAR(7);

        ALTER TABLE public.empresas
        ADD COLUMN IF NOT EXISTS codigo_ibge CHAR(7);

        ALTER TABLE public.empresas
        ADD CONSTRAINT empresas_municipio_id_fkey
        FOREIGN KEY (municipio_id)
        REFERENCES public.municipios_catalogo (codigo_ibge)
        ON UPDATE CASCADE
        ON DELETE SET NULL;

        ALTER TABLE public.empresas
        ADD CONSTRAINT empresas_codigo_ibge_fkey
        FOREIGN KEY (codigo_ibge)
        REFERENCES public.municipios_catalogo (codigo_ibge)
        ON UPDATE CASCADE
        ON DELETE SET NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.empresas
        DROP CONSTRAINT IF EXISTS empresas_codigo_ibge_fkey;

        ALTER TABLE public.empresas
        DROP CONSTRAINT IF EXISTS empresas_municipio_id_fkey;

        ALTER TABLE public.empresas
        DROP COLUMN IF EXISTS codigo_ibge;

        ALTER TABLE public.empresas
        DROP COLUMN IF EXISTS municipio_id;
        """
    )
