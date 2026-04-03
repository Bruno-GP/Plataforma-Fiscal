import logging

import psycopg

from app.services.nfe.postres_config import carregar_config_postgres

logger = logging.getLogger("DbSchemaService")


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
