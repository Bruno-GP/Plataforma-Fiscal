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
