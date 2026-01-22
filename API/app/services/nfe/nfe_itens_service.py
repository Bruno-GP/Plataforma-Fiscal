import logging
from typing import Iterable

import psycopg

from app.domain.nfe.extractor import NotaExtraida
from app.services.nfe.empresa_service import normalizar_cnpj
from app.services.nfe.postres_config import carregar_config_postgres

logger = logging.getLogger("NFeItensService")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


class NFeItensService:
    def __init__(self):
        logger.debug("Inicializando NFeItensService")

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

    def registrar_itens(self, notas: Iterable[NotaExtraida]) -> int:
        logger.debug("Iniciando registrar_itens")

        notas_list = list(notas)
        if not notas_list:
            logger.info("Nenhuma nota para registrar itens")
            return 0

        sql_buscar_nota = """
            SELECT id
            FROM public.nfe_notas
            WHERE numero_nf = %s
              AND emitente_cnpj = %s
              AND data_emissao = %s
            LIMIT 1;
        """

        sql_insert_item = """
            INSERT INTO public.nfe_itens (
                nota_id,
                item_numero,
                produto_codigo,
                descricao,
                ncm,
                cfop,
                quantidade,
                valor_unitario,
                valor_total
            )
            SELECT
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1
                FROM public.nfe_itens
                WHERE nota_id = %s
                  AND item_numero = %s
                  AND produto_codigo = %s
            );
        """

        try:
            #logger.debug("Abrindo conexão com PostgreSQL")
            with psycopg.connect(**self.conn_params) as conn:
                #logger.debug("Conexão aberta com sucesso")
                with conn.cursor() as cur:
                    inseridos = 0
                    for nota in notas_list:
                        emitente_cnpj = normalizar_cnpj(nota.emitente_cnpj)
                        cur.execute(
                            sql_buscar_nota,
                            (
                                str(nota.numero_nf),
                                emitente_cnpj,
                                nota.data_emissao,
                            ),
                        )
                        resultado = cur.fetchone()
                        if not resultado:
                            logger.warning(
                                "Nota não encontrada para itens: %s/%s/%s",
                                nota.numero_nf,
                                emitente_cnpj,
                                nota.data_emissao,
                            )
                            continue

                        nota_id = resultado[0]
                        for item in nota.itens:
                            cur.execute(
                                sql_insert_item,
                                (
                                    nota_id,
                                    item.numero_item,
                                    item.codigo_produto,
                                    item.descricao,
                                    item.ncm,
                                    item.cfop,
                                    item.quantidade,
                                    item.valor_unitario,
                                    item.valor_total,
                                    nota_id,
                                    item.numero_item,
                                    item.codigo_produto,
                                ),
                            )
                            inseridos += cur.rowcount

                    logger.info(
                        "Itens registrados com sucesso: %s",
                        inseridos,
                    )

            return inseridos
        except Exception:
            logger.exception("Erro ao registrar itens NFe")
            raise