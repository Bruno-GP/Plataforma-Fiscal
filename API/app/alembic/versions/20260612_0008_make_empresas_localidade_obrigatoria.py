"""make empresas localidade obrigatoria

Revision ID: 20260612_0008
Revises: 20260609_0007
Create Date: 2026-06-12
"""

from alembic import op


revision = "20260612_0008"
down_revision = "20260609_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            unresolved_count INTEGER;
        BEGIN
            WITH resolved AS (
                SELECT
                    e.id,
                    mc.codigo_ibge,
                    mc.uf,
                    mc.nome
                FROM public.empresas AS e
                JOIN public.municipios_catalogo AS mc
                  ON (
                        (
                            e.municipio_id IS NOT NULL
                            AND regexp_replace(e.municipio_id, '\\D', '', 'g') = regexp_replace(mc.codigo_ibge, '\\D', '', 'g')
                        )
                        OR (
                            e.codigo_ibge IS NOT NULL
                            AND regexp_replace(e.codigo_ibge, '\\D', '', 'g') = regexp_replace(mc.codigo_ibge, '\\D', '', 'g')
                        )
                        OR (
                            e.estado IS NOT NULL
                            AND e.cidade IS NOT NULL
                            AND UPPER(TRIM(e.estado)) = UPPER(mc.uf)
                            AND UPPER(TRIM(e.cidade)) = UPPER(mc.nome)
                        )
                  )
            )
            UPDATE public.empresas AS e
            SET estado = resolved.uf,
                cidade = resolved.nome,
                municipio_id = resolved.codigo_ibge,
                codigo_ibge = resolved.codigo_ibge
            FROM resolved
            WHERE e.id = resolved.id;

            SELECT COUNT(*)
            INTO unresolved_count
            FROM public.empresas AS e
            WHERE e.estado IS NULL
               OR e.cidade IS NULL
               OR e.municipio_id IS NULL
               OR e.codigo_ibge IS NULL
               OR NOT EXISTS (
                    SELECT 1
                    FROM public.municipios_catalogo AS mc
                    WHERE (
                        (
                            e.municipio_id IS NOT NULL
                            AND regexp_replace(e.municipio_id, '\\D', '', 'g') = regexp_replace(mc.codigo_ibge, '\\D', '', 'g')
                        )
                        OR (
                            e.codigo_ibge IS NOT NULL
                            AND regexp_replace(e.codigo_ibge, '\\D', '', 'g') = regexp_replace(mc.codigo_ibge, '\\D', '', 'g')
                        )
                        OR (
                            e.estado IS NOT NULL
                            AND e.cidade IS NOT NULL
                            AND UPPER(TRIM(e.estado)) = UPPER(mc.uf)
                            AND UPPER(TRIM(e.cidade)) = UPPER(mc.nome)
                        )
                    )
               );

            IF unresolved_count > 0 THEN
                RAISE EXCEPTION
                    'Nao foi possivel normalizar % registros da tabela public.empresas antes de tornar a localidade obrigatoria.',
                    unresolved_count;
            END IF;
        END $$;

        ALTER TABLE public.empresas
            ALTER COLUMN estado SET NOT NULL,
            ALTER COLUMN cidade SET NOT NULL,
            ALTER COLUMN municipio_id SET NOT NULL,
            ALTER COLUMN codigo_ibge SET NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.empresas
            ALTER COLUMN codigo_ibge DROP NOT NULL,
            ALTER COLUMN municipio_id DROP NOT NULL,
            ALTER COLUMN cidade DROP NOT NULL,
            ALTER COLUMN estado DROP NOT NULL;
        """
    )
