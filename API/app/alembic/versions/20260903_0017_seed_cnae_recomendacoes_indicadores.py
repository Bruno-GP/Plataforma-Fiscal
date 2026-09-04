"""semeia segmentos CNAE e recomendacoes iniciais de indicadores

Revision ID: 20260903_0017
Revises: 20260903_0016
Create Date: 2026-09-03

Os prefixos de CNAE seguem a estrutura oficial CNAE 2.0 do IBGE/CONCLA:
https://cnae.ibge.gov.br/?view=estrutura
"""

from alembic import op

revision = "20260903_0017"
down_revision = "20260903_0016"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute(
        """
        INSERT INTO public.segmentos_cnae
            (segmento_chave, segmento_nome, cnae_prefixo, prioridade)
        VALUES
            ('industria', 'Industria', '10', 100),
            ('industria', 'Industria', '11', 100),
            ('industria', 'Industria', '12', 100),
            ('industria', 'Industria', '13', 100),
            ('industria', 'Industria', '14', 100),
            ('industria', 'Industria', '15', 100),
            ('industria', 'Industria', '16', 100),
            ('industria', 'Industria', '17', 100),
            ('industria', 'Industria', '18', 100),
            ('industria', 'Industria', '19', 100),
            ('industria', 'Industria', '20', 100),
            ('industria', 'Industria', '21', 100),
            ('industria', 'Industria', '22', 100),
            ('industria', 'Industria', '23', 100),
            ('industria', 'Industria', '24', 100),
            ('industria', 'Industria', '25', 100),
            ('industria', 'Industria', '26', 100),
            ('industria', 'Industria', '27', 100),
            ('industria', 'Industria', '28', 100),
            ('industria', 'Industria', '29', 100),
            ('industria', 'Industria', '30', 100),
            ('industria', 'Industria', '31', 100),
            ('industria', 'Industria', '32', 100),
            ('industria', 'Industria', '33', 100),
            ('comercio_varejista', 'Comercio varejista', '47', 80),
            ('transporte_logistica', 'Transporte e logistica', '49', 90),
            ('transporte_logistica', 'Transporte e logistica', '50', 90),
            ('transporte_logistica', 'Transporte e logistica', '51', 90),
            ('transporte_logistica', 'Transporte e logistica', '52', 90),
            ('transporte_logistica', 'Transporte e logistica', '53', 90),
            ('servicos_profissionais', 'Servicos profissionais', '69', 100),
            ('servicos_profissionais', 'Servicos profissionais', '70', 100),
            ('servicos_profissionais', 'Servicos profissionais', '71', 100),
            ('servicos_profissionais', 'Servicos profissionais', '72', 100),
            ('servicos_profissionais', 'Servicos profissionais', '73', 100),
            ('servicos_profissionais', 'Servicos profissionais', '74', 100),
            ('servicos_profissionais', 'Servicos profissionais', '75', 100)
        ON CONFLICT (cnae_prefixo)
        WHERE cnae_prefixo IS NOT NULL
        DO UPDATE SET
            segmento_chave = EXCLUDED.segmento_chave,
            segmento_nome = EXCLUDED.segmento_nome,
            prioridade = EXCLUDED.prioridade,
            ativo = TRUE,
            atualizado_em = NOW();

        WITH recomendacoes(segmento_chave, indicador_chave, perfil, prioridade, motivo, obrigatorio) AS (
            VALUES
                ('comercio_varejista', 'faturamento', 'xml', 10, 'Indicador base para acompanhar volume de vendas e sazonalidade.', TRUE),
                ('comercio_varejista', 'ticket_medio', 'xml', 20, 'Ajuda a acompanhar variacao do valor medio das vendas.', FALSE),
                ('comercio_varejista', 'quantidade_notas', 'xml', 30, 'Mostra volume operacional e movimento de vendas.', FALSE),
                ('comercio_varejista', 'total_icms', 'xml', 40, 'Acompanha peso de ICMS nas operacoes de venda.', FALSE),
                ('comercio_varejista', 'total_pis_cofins', 'xml', 50, 'Acompanha carga de PIS e COFINS sobre faturamento.', FALSE),

                ('servicos_profissionais', 'faturamento', 'xml', 10, 'Indicador base para acompanhar receita recorrente e novos contratos.', TRUE),
                ('servicos_profissionais', 'ticket_medio', 'xml', 20, 'Ajuda a comparar o valor medio por nota ou contrato faturado.', FALSE),
                ('servicos_profissionais', 'quantidade_notas', 'xml', 30, 'Mostra volume de documentos emitidos no periodo.', FALSE),
                ('servicos_profissionais', 'total_pis_cofins', 'xml', 40, 'Acompanha tributos federais relevantes para prestadores de servico.', FALSE),
                ('servicos_profissionais', 'total_icms', 'xml', 90, 'Permite identificar eventual incidencia ou cadastro operacional fora do esperado.', FALSE),

                ('industria', 'faturamento', 'xml', 10, 'Indicador base para acompanhar volume de saidas industriais.', TRUE),
                ('industria', 'total_icms', 'xml', 20, 'Acompanha ICMS nas operacoes industriais.', FALSE),
                ('industria', 'total_ipi', 'xml', 30, 'Acompanha IPI, frequentemente relevante para industria.', FALSE),
                ('industria', 'total_pis_cofins', 'xml', 40, 'Acompanha tributos federais sobre as operacoes.', FALSE),
                ('industria', 'quantidade_notas', 'xml', 50, 'Mostra volume documental e atividade operacional.', FALSE),

                ('transporte_logistica', 'faturamento', 'xml', 10, 'Indicador base para acompanhar receita de fretes e operacoes logisticas.', TRUE),
                ('transporte_logistica', 'quantidade_notas', 'xml', 20, 'Mostra volume de documentos e operacoes no periodo.', FALSE),
                ('transporte_logistica', 'ticket_medio', 'xml', 30, 'Ajuda a acompanhar valor medio por documento ou operacao.', FALSE),
                ('transporte_logistica', 'total_icms', 'xml', 40, 'Acompanha ICMS relacionado as prestacoes de transporte.', FALSE),
                ('transporte_logistica', 'total_pis_cofins', 'xml', 50, 'Acompanha carga federal sobre faturamento.', FALSE)
        )
        INSERT INTO public.indicador_segmento_recomendacao
            (segmento_chave, indicador_id, perfil, prioridade, motivo, obrigatorio)
        SELECT
            r.segmento_chave,
            i.id,
            r.perfil,
            r.prioridade,
            r.motivo,
            r.obrigatorio
        FROM recomendacoes r
        JOIN public.indicadores i ON i.chave = r.indicador_chave
        ON CONFLICT (segmento_chave, indicador_id, perfil)
        DO UPDATE SET
            prioridade = EXCLUDED.prioridade,
            motivo = EXCLUDED.motivo,
            obrigatorio = EXCLUDED.obrigatorio,
            ativo = TRUE,
            atualizado_em = NOW();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM public.indicador_segmento_recomendacao
        WHERE segmento_chave IN (
            'comercio_varejista',
            'servicos_profissionais',
            'industria',
            'transporte_logistica'
        );

        DELETE FROM public.segmentos_cnae
        WHERE segmento_chave IN (
            'comercio_varejista',
            'servicos_profissionais',
            'industria',
            'transporte_logistica'
        );
        """
    )
