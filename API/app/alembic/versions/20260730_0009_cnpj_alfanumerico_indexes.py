"""recria indices funcionais de cnpj para suportar cnpj alfanumerico

Revision ID: 20260730_0009
Revises: 20260612_0008
Create Date: 2026-07-30
"""

from alembic import op


revision = "20260730_0009"
down_revision = "20260612_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS public.idx_sped_documentos_empresa_tipo_data_normalizado;
        CREATE INDEX IF NOT EXISTS idx_sped_documentos_empresa_tipo_data_normalizado_alnum
            ON sped_documentos_fiscais ((regexp_replace(UPPER(COALESCE(empresa_cnpj, '')), '[^0-9A-Z]', '', 'g')), tipo_operacao, data_emissao);

        DROP INDEX IF EXISTS public.idx_documentos_fiscais_tributos_nfe_dashboard_periodo;
        CREATE INDEX IF NOT EXISTS idx_documentos_fiscais_tributos_nfe_dashboard_periodo_alnum
            ON public.documentos_fiscais_tributos (
              (regexp_replace(UPPER(COALESCE(empresa_cnpj, '')), '[^0-9A-Z]', '', 'g')),
              tipo_operacao,
              (COALESCE(periodo_ano, EXTRACT(YEAR FROM data_emissao)::int)),
              (COALESCE(periodo_mes, EXTRACT(MONTH FROM data_emissao)::int))
            )
            WHERE nota_id IS NOT NULL;

        DROP INDEX IF EXISTS public.idx_documentos_fiscais_tributos_sped_dashboard_periodo;
        CREATE INDEX IF NOT EXISTS idx_documentos_fiscais_tributos_sped_dashboard_periodo_alnum
            ON public.documentos_fiscais_tributos (
              (regexp_replace(UPPER(COALESCE(empresa_cnpj, '')), '[^0-9A-Z]', '', 'g')),
              tipo_operacao,
              (COALESCE(periodo_ano, EXTRACT(YEAR FROM data_emissao)::int)),
              (COALESCE(periodo_mes, EXTRACT(MONTH FROM data_emissao)::int))
            )
            WHERE sped_documento_id IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS public.idx_documentos_fiscais_tributos_sped_dashboard_periodo_alnum;
        CREATE INDEX IF NOT EXISTS idx_documentos_fiscais_tributos_sped_dashboard_periodo
            ON public.documentos_fiscais_tributos (
              (regexp_replace(COALESCE(empresa_cnpj, ''), '\\D', '', 'g')),
              tipo_operacao,
              (COALESCE(periodo_ano, EXTRACT(YEAR FROM data_emissao)::int)),
              (COALESCE(periodo_mes, EXTRACT(MONTH FROM data_emissao)::int))
            )
            WHERE sped_documento_id IS NOT NULL;

        DROP INDEX IF EXISTS public.idx_documentos_fiscais_tributos_nfe_dashboard_periodo_alnum;
        CREATE INDEX IF NOT EXISTS idx_documentos_fiscais_tributos_nfe_dashboard_periodo
            ON public.documentos_fiscais_tributos (
              (regexp_replace(COALESCE(empresa_cnpj, ''), '\\D', '', 'g')),
              tipo_operacao,
              (COALESCE(periodo_ano, EXTRACT(YEAR FROM data_emissao)::int)),
              (COALESCE(periodo_mes, EXTRACT(MONTH FROM data_emissao)::int))
            )
            WHERE nota_id IS NOT NULL;

        DROP INDEX IF EXISTS public.idx_sped_documentos_empresa_tipo_data_normalizado_alnum;
        CREATE INDEX IF NOT EXISTS idx_sped_documentos_empresa_tipo_data_normalizado
            ON sped_documentos_fiscais ((regexp_replace(COALESCE(empresa_cnpj, ''), '\\D', '', 'g')), tipo_operacao, data_emissao);
        """
    )
