import psycopg
import logging
from app.services.postres_config import carregar_config_postgres

# =========================
# LOG CONFIG
# =========================
logger = logging.getLogger("EmpresaService")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# =========================
# UTILS
# =========================
def normalizar_cnpj(cnpj: str) -> str:
    return "".join(filter(str.isdigit, cnpj))

# =========================
# SERVICE
# =========================
class EmpresaService:
    def __init__(self):
        logger.debug("Inicializando EmpresaService")

        config = carregar_config_postgres()
        #logger.debug(f"Config PostgreSQL carregada: {config}")

        self.conn_params = {
            "host": config["host"],
            "port": config["port"],
            "dbname": config["database"],
            "user": config["user"],
            "password": config["password"],
            "connect_timeout": 5,
        }

    def obter_ou_criar(self, cnpj_emitente: str, nome_emitente: str) -> int:
        logger.debug("Iniciando obter_ou_criar")

        cnpj = normalizar_cnpj(cnpj_emitente)
        #logger.debug(f"CNPJ recebido: {cnpj_emitente}")
        #logger.debug(f"CNPJ normalizado: {cnpj}")
        #logger.debug(f"Nome emitente: {nome_emitente}")

        try:
            #logger.debug("Abrindo conexão com PostgreSQL")
            with psycopg.connect(**self.conn_params) as conn:
                #logger.debug("Conexão aberta com sucesso")

                with conn.cursor() as cur:
                    #logger.debug("Cursor criado")

                    sql_insert = """
                        INSERT INTO public.empresas (cnpj, nome)
                        VALUES (%s, %s)
                        ON CONFLICT (cnpj)
                        DO UPDATE SET nome = EXCLUDED.nome
                        RETURNING id;
                    """

                    logger.debug("Executando SQL INSERT/UPDATE")
                    #logger.debug(f"SQL: {sql_insert.strip()}")
                    #logger.debug(f"Params: {(cnpj, nome_emitente)}")

                    cur.execute(sql_insert, (cnpj, nome_emitente))

                    #logger.debug("SQL executado, buscando RETURNING id")
                    row = cur.fetchone()
                    #logger.debug(f"Resultado RETURNING: {row}")

                    if row:
                        #logger.info(f"Empresa obtida/criada com ID={row[0]}")
                        return row[0]

                    #logger.warning("RETURNING não retornou ID, executando SELECT fallback")

                    sql_select = """
                        SELECT id
                        FROM public.empresas
                        WHERE cnpj = %s;
                    """

                    #logger.debug(f"SQL fallback: {sql_select.strip()}")
                    cur.execute(sql_select, (cnpj,))
                    row = cur.fetchone()
                    #logger.debug(f"Resultado SELECT fallback: {row}")

                    if not row:
                        logger.error("Empresa não encontrada nem após fallback")
                        raise RuntimeError(
                            f"Falha crítica ao obter ou criar empresa. CNPJ={cnpj}"
                        )

                    logger.info(f"Empresa encontrada via fallback ID={row[0]}")
                    return row[0]

        except Exception as exc:
            logger.exception("ERRO AO OBTER OU CRIAR EMPRESA")
            raise