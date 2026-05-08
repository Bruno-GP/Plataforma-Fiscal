"""add reforma tributaria tables

Revision ID: 20260507_0002
Revises: 20260505_0001
Create Date: 2026-05-07
"""

from pathlib import Path

from alembic import op


revision = "20260507_0002"
down_revision = "20260505_0001"
branch_labels = None
depends_on = None


def _migration_sql(name: str) -> str:
    migrations_dir = Path(__file__).resolve().parents[3] / "SQL" / "migrations"
    return (migrations_dir / name).read_text(encoding="utf-8")


def upgrade() -> None:
    op.execute(_migration_sql("004_add_reforma_tributaria_base.sql"))
    op.execute(_migration_sql("005_add_reforma_tributaria_documentos_itens.sql"))
    op.execute(_migration_sql("006_add_reforma_tributaria_creditos_debitos_memoria.sql"))


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS public.memoria_calculo_tributaria CASCADE;
        DROP TABLE IF EXISTS public.debitos_tributarios CASCADE;
        DROP TABLE IF EXISTS public.creditos_tributarios CASCADE;
        DROP TABLE IF EXISTS public.itens_documentos_fiscais_tributos CASCADE;
        DROP TABLE IF EXISTS public.documentos_fiscais_tributos CASCADE;
        DROP TABLE IF EXISTS public.ajustes_tributarios CASCADE;
        DROP TABLE IF EXISTS public.apuracao_tributaria CASCADE;
        DROP TABLE IF EXISTS public.aliquotas_tributarias CASCADE;
        DROP TABLE IF EXISTS public.regras_tributarias_vigencias CASCADE;
        DROP TABLE IF EXISTS public.regras_tributarias CASCADE;
        DROP TABLE IF EXISTS public.tributos CASCADE;
        """
    )
