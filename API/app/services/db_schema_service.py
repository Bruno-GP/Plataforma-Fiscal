import logging

import psycopg

from app.services.nfe.postres_config import carregar_config_postgres

logger = logging.getLogger("DbSchemaService")


DDL_NCM_CATALOGO = """
CREATE TABLE IF NOT EXISTS public.ncm_catalogo (
    codigo CHAR(8) PRIMARY KEY,
    descricao TEXT NOT NULL,
    codigo_formatado VARCHAR(20),
    vigencia DATE,
    fonte_arquivo VARCHAR(255),
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ncm_catalogo_descricao
ON public.ncm_catalogo (descricao);

CREATE INDEX IF NOT EXISTS idx_ncm_catalogo_vigencia
ON public.ncm_catalogo (vigencia);
"""

DDL_NCM_TRIBUTACAO = """
CREATE TABLE IF NOT EXISTS public.ncm_tributacao (
    id BIGSERIAL PRIMARY KEY,
    ncm_codigo CHAR(8) NOT NULL,
    uf CHAR(2) NOT NULL,
    nacional_federal NUMERIC(6,2),
    importados_federal NUMERIC(6,2),
    estadual NUMERIC(6,2),
    municipal NUMERIC(6,2),
    vigencia_inicio DATE,
    vigencia_fim DATE,
    versao VARCHAR(20),
    fonte VARCHAR(100),
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ncm_tributacao_ncm_uf UNIQUE (ncm_codigo, uf),
    CONSTRAINT fk_ncm_tributacao_catalogo
        FOREIGN KEY (ncm_codigo)
        REFERENCES public.ncm_catalogo (codigo)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ncm_tributacao_codigo
ON public.ncm_tributacao (ncm_codigo);

CREATE INDEX IF NOT EXISTS idx_ncm_tributacao_uf
ON public.ncm_tributacao (uf);
"""

DDL_FISCAL_ANALISE_INDEXES = r"""
CREATE INDEX IF NOT EXISTS idx_notas_emitente_cnpj_normalizado
ON public.notas ((regexp_replace(COALESCE(emitente_cnpj, ''), '\D', '', 'g')));

CREATE INDEX IF NOT EXISTS idx_notas_emitente_cnpj_data_normalizado
ON public.notas ((regexp_replace(COALESCE(emitente_cnpj, ''), '\D', '', 'g')), data_emissao);

CREATE INDEX IF NOT EXISTS idx_notas_destinatario_uf_normalizado
ON public.notas ((UPPER(COALESCE(NULLIF(TRIM(destinatario_uf), ''), 'Sem UF'))));

CREATE INDEX IF NOT EXISTS idx_notas_destinatario_cidade_normalizada
ON public.notas ((UPPER(COALESCE(NULLIF(TRIM(destinatario_cidade), ''), 'Cidade nao identificada'))));

CREATE INDEX IF NOT EXISTS idx_notas_itens_nota_cfop_tipo
ON public.notas_itens (nota_id, (LEFT(regexp_replace(COALESCE(cfop, ''), '\D', '', 'g'), 1)));

CREATE INDEX IF NOT EXISTS idx_notas_itens_ncm_normalizado
ON public.notas_itens ((regexp_replace(COALESCE(ncm, ''), '\D', '', 'g')));

CREATE INDEX IF NOT EXISTS idx_notas_itens_produto_codigo_normalizado
ON public.notas_itens ((COALESCE(NULLIF(TRIM(produto_codigo), ''), 'SEM-CODIGO')));

CREATE INDEX IF NOT EXISTS idx_sped_documentos_empresa_tipo_data_normalizado
ON public.sped_documentos_fiscais ((regexp_replace(COALESCE(empresa_cnpj, ''), '\D', '', 'g')), tipo_operacao, data_emissao);

CREATE INDEX IF NOT EXISTS idx_sped_documento_itens_documento
ON public.sped_documento_itens (documento_id);

CREATE INDEX IF NOT EXISTS idx_sped_documento_itens_produto
ON public.sped_documento_itens (produto_id);

CREATE INDEX IF NOT EXISTS idx_sped_produtos_codigo_normalizado
ON public.sped_produtos ((COALESCE(NULLIF(TRIM(codigo), ''), 'SEM-CODIGO')));

CREATE INDEX IF NOT EXISTS idx_sped_produtos_ncm_normalizado
ON public.sped_produtos ((regexp_replace(COALESCE(ncm, ''), '\D', '', 'g')));

CREATE INDEX IF NOT EXISTS idx_sped_participantes_uf_normalizada
ON public.sped_participantes ((UPPER(COALESCE(NULLIF(TRIM(uf), ''), 'Sem UF'))));

CREATE INDEX IF NOT EXISTS idx_sped_participantes_cidade_normalizada
ON public.sped_participantes ((UPPER(COALESCE(NULLIF(TRIM(municipio_nome), ''), NULLIF(TRIM(municipio), ''), 'Cidade nao identificada'))));
"""


def _conn_params() -> dict:
    config = carregar_config_postgres()
    conn_params: dict = {
        "connect_timeout": 5,
    }

    if config.get("conninfo"):
        conn_params["conninfo"] = config["conninfo"]
    else:
        conn_params.update(
            {
                "host": config["host"],
                "port": config["port"],
                "dbname": config["database"],
                "user": config["user"],
                "password": config["password"],
            }
        )

    if config.get("sslmode"):
        conn_params["sslmode"] = config["sslmode"]

    return conn_params


def ensure_empresas_tem_sped_column() -> None:
    with psycopg.connect(**_conn_params()) as conn:
        with conn.cursor() as cur:
            # Mantem a API compatível com bancos que ainda não receberam a migration.
            cur.execute(
                """
                ALTER TABLE public.empresas
                ADD COLUMN IF NOT EXISTS tem_sped BOOLEAN NOT NULL DEFAULT FALSE;
                """
            )

    logger.info("Schema verificado: coluna public.empresas.tem_sped pronta para uso.")


def ensure_ncm_ibpt_tables() -> None:
    with psycopg.connect(**_conn_params()) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL_NCM_CATALOGO)
            cur.execute(DDL_NCM_TRIBUTACAO)

    logger.info("Schema verificado: tabelas public.ncm_catalogo e public.ncm_tributacao prontas para uso.")


def ensure_fiscal_analysis_indexes() -> None:
    with psycopg.connect(**_conn_params()) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL_FISCAL_ANALISE_INDEXES)

    logger.info("Schema verificado: indices funcionais da analise fiscal prontos para uso.")
