"""cria schema sefaz (certificados, nsu_controle, documentos, eventos, sync_log)

Revision ID: 20260814_0013
Revises: 20260813_0012
Create Date: 2026-08-14
"""

from alembic import op


revision = "20260814_0013"
down_revision = "20260813_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS sefaz;

        CREATE TABLE IF NOT EXISTS sefaz.certificados (
            id BIGSERIAL PRIMARY KEY,
            empresa_id BIGINT NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
            arquivo_certificado BYTEA NOT NULL,
            senha_criptografada TEXT NOT NULL,
            cnpj_titular VARCHAR(20) NOT NULL,
            data_validade DATE NOT NULL,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE UNIQUE INDEX IF NOT EXISTS uq_sefaz_certificados_empresa_ativo
            ON sefaz.certificados (empresa_id) WHERE ativo;

        CREATE TABLE IF NOT EXISTS sefaz.nsu_controle (
            id BIGSERIAL PRIMARY KEY,
            empresa_id BIGINT NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
            ambiente SMALLINT NOT NULL,
            ultimo_nsu VARCHAR(15) NOT NULL DEFAULT '000000000000000',
            ultima_execucao_em TIMESTAMPTZ,
            status_ultima_execucao VARCHAR(20),
            CONSTRAINT uq_sefaz_nsu_controle_empresa_ambiente UNIQUE (empresa_id, ambiente)
        );

        CREATE TABLE IF NOT EXISTS sefaz.documentos (
            id BIGSERIAL PRIMARY KEY,
            empresa_id BIGINT NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
            chave_acesso VARCHAR(44) NOT NULL,
            tipo_documento VARCHAR(20) NOT NULL,
            direcao VARCHAR(10) NOT NULL,
            cnpj_emitente VARCHAR(20) NOT NULL,
            cnpj_destinatario VARCHAR(20),
            nsu VARCHAR(15) NOT NULL,
            data_emissao TIMESTAMPTZ,
            valor_total NUMERIC(18,2),
            situacao VARCHAR(20),
            xml_armazenado BYTEA,
            manifestacao_status VARCHAR(20),
            criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_sefaz_documentos_empresa_chave UNIQUE (empresa_id, chave_acesso)
        );

        CREATE INDEX IF NOT EXISTS ix_sefaz_documentos_empresa_situacao
            ON sefaz.documentos (empresa_id, situacao);

        CREATE INDEX IF NOT EXISTS ix_sefaz_documentos_manifestacao_pendente
            ON sefaz.documentos (empresa_id) WHERE manifestacao_status = 'pendente';

        CREATE TABLE IF NOT EXISTS sefaz.eventos (
            id BIGSERIAL PRIMARY KEY,
            documento_id BIGINT NOT NULL REFERENCES sefaz.documentos(id) ON DELETE CASCADE,
            empresa_id BIGINT NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
            tipo_evento VARCHAR(30) NOT NULL,
            protocolo VARCHAR(20),
            status VARCHAR(20) NOT NULL,
            payload_xml TEXT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS ix_sefaz_eventos_documento ON sefaz.eventos (documento_id);

        CREATE TABLE IF NOT EXISTS sefaz.sync_log (
            id BIGSERIAL PRIMARY KEY,
            empresa_id BIGINT NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
            iniciado_em TIMESTAMPTZ NOT NULL,
            finalizado_em TIMESTAMPTZ,
            documentos_novos INT NOT NULL DEFAULT 0,
            nsu_inicial VARCHAR(15),
            nsu_final VARCHAR(15),
            status VARCHAR(20) NOT NULL,
            erro_detalhe TEXT
        );

        CREATE INDEX IF NOT EXISTS ix_sefaz_sync_log_empresa
            ON sefaz.sync_log (empresa_id, iniciado_em DESC);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP SCHEMA IF EXISTS sefaz CASCADE;
        """
    )
