import logging
from typing import Iterable

import psycopg

from app.domain.nfe.extractor import NotaExtraida
from app.services.nfe.empresa_service import normalizar_cnpj
from app.services.nfe.postres_config import carregar_config_postgres

logger = logging.getLogger("NFeItensService")
logger.disabled = True

def _limitar_texto(valor: str | None, limite: int) -> str:
    if valor is None:
        return ""

    texto = str(valor).strip()
    if len(texto) <= limite:
        return texto

    logger.warning(
        "Campo textual truncado de %s para %s caracteres",
        len(texto),
        limite,
    )
    return texto[:limite]

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

    def registrar_itens(
        self,
        conn, 
        notas: Iterable[NotaExtraida]
    ) -> int:
        logger.debug("Iniciando registrar_itens")

        notas_list = list(notas)
        if not notas_list:
            logger.info("Nenhuma nota para registrar itens")
            return 0

        sql_buscar_nota = """
            SELECT
                n.id,
                p.empresa_id,
                p.cnpj_emitente
            FROM public.notas AS n
            JOIN public.notas_processamentos AS p
              ON p.id = n.processamento_id
            WHERE n.numero_nf = %s
              AND n.emitente_cnpj = %s
              AND COALESCE(n.modelo, '') = COALESCE(%s, '')
              AND n.data_emissao = %s
            LIMIT 1;
        """

        sql_insert_item = """
            INSERT INTO public.notas_itens (
                nota_id,
                empresa_id,
                cnpj,
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
                %s, %s, %s, %s, %s, 
                %s
            WHERE NOT EXISTS (
                SELECT 1
                FROM public.notas_itens
                WHERE nota_id = %s
                  AND item_numero = %s
                  AND produto_codigo = %s
            );
        """

        try:
            #logger.debug("Abrindo conexão com PostgreSQL")
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
                            nota.modelo,
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

                    nota_id, empresa_id, cnpj = resultado
                    for item in nota.itens:
                        
                        codigo_produto = _limitar_texto(item.codigo_produto, 120)
                        descricao = _limitar_texto(item.descricao, 255)
                        ncm = _limitar_texto(item.ncm, 20)
                        cfop = _limitar_texto(item.cfop, 10)
                    
                        cur.execute(
                            sql_insert_item,
                            (
                                nota_id,
                                empresa_id,
                                cnpj,
                                item.numero_item,
                                codigo_produto,
                                descricao,
                                ncm,
                                cfop,
                                item.quantidade,
                                item.valor_unitario,
                                item.valor_total,
                                nota_id,
                                item.numero_item,
                                codigo_produto,
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
