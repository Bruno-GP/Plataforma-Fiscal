"""add dashboard performance indexes

Revision ID: 20260511_0003
Revises: 20260507_0002
Create Date: 2026-05-11
"""

from pathlib import Path

from alembic import op


revision = "20260511_0003"
down_revision = "20260507_0002"
branch_labels = None
depends_on = None


def _migration_sql(name: str) -> str:
    migrations_dir = Path(__file__).resolve().parents[3] / "SQL" / "migrations"
    return (migrations_dir / name).read_text(encoding="utf-8")


def upgrade() -> None:
    op.execute(_migration_sql("008_add_dashboard_performance_indexes.sql"))


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS public.idx_documentos_fiscais_tributos_sped_empresa_tipo_periodo;
        DROP INDEX IF EXISTS public.idx_documentos_fiscais_tributos_sped_dashboard_periodo;
        DROP INDEX IF EXISTS public.idx_documentos_fiscais_tributos_nfe_empresa_tipo_periodo;
        DROP INDEX IF EXISTS public.idx_documentos_fiscais_tributos_nfe_dashboard_periodo;
        DROP INDEX IF EXISTS public.idx_documentos_fiscais_tributos_empresa_tipo_periodo;
        """
    )
