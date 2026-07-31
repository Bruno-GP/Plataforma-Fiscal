"""adiciona indices funcionais faltantes para filtro normalizado de cnpj/cfop

Contexto: idx_notas_emitente_data, idx_notas_kpis_periodo, ux_sped_apuracao_icms_periodo
e a PK de notas_cfops sao todos sobre coluna crua, mas repositories/nfe e
repositories/reforma_tributaria filtram via
regexp_replace(UPPER(COALESCE(cnpj, '')), '[^0-9A-Z]', '', 'g') = %s
(ou regexp_replace(codigo, '\\D', '', 'g') para CFOP). Indice de coluna crua
nao cobre expressao funcional -> seq scan nessas queries.
sped_documentos_fiscais e documentos_fiscais_tributos ja foram cobertos na
migration 20260730_0009; esta migration fecha o gap em notas, notas_kpis,
notas_cfops e sped_apuracao_icms.

Revision ID: 20260731_0011
Revises: 20260730_0010
Create Date: 2026-07-31
"""

from alembic import op


revision = "20260731_0011"
down_revision = "20260730_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notas_emitente_data_alnum
            ON notas (
                (regexp_replace(UPPER(COALESCE(emitente_cnpj, '')), '[^0-9A-Z]', '', 'g')),
                data_emissao
            );

        CREATE INDEX IF NOT EXISTS idx_notas_processamento_id
            ON notas (processamento_id);

        CREATE INDEX IF NOT EXISTS idx_notas_kpis_emitente_alnum
            ON notas_kpis (
                (regexp_replace(UPPER(COALESCE(emitente_cnpj, '')), '[^0-9A-Z]', '', 'g')),
                periodo_ano DESC,
                periodo_mes DESC
            );

        CREATE INDEX IF NOT EXISTS idx_notas_cfops_codigo_alnum
            ON notas_cfops (
                (regexp_replace(COALESCE(codigo, ''), '\\D', '', 'g'))
            );

        CREATE INDEX IF NOT EXISTS idx_sped_apuracao_icms_empresa_alnum
            ON sped_apuracao_icms (
                (regexp_replace(UPPER(COALESCE(empresa_cnpj, '')), '[^0-9A-Z]', '', 'g')),
                periodo_ano,
                periodo_mes
            );

        CREATE INDEX IF NOT EXISTS idx_itens_doc_fiscais_tributos_nota_item
            ON itens_documentos_fiscais_tributos (nota_item_id)
            WHERE nota_item_id IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS public.idx_itens_doc_fiscais_tributos_nota_item;
        DROP INDEX IF EXISTS public.idx_sped_apuracao_icms_empresa_alnum;
        DROP INDEX IF EXISTS public.idx_notas_cfops_codigo_alnum;
        DROP INDEX IF EXISTS public.idx_notas_kpis_emitente_alnum;
        DROP INDEX IF EXISTS public.idx_notas_processamento_id;
        DROP INDEX IF EXISTS public.idx_notas_emitente_data_alnum;
        """
    )
