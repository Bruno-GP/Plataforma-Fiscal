import logging
from typing import Iterable, Optional

import psycopg

from app.domain.nfe.extractor import NotaExtraida
from app.services.nfe.postres_config import carregar_config_postgres
from app.services.nfe.empresa_service import normalizar_cnpj

logger = logging.getLogger("NFeNotasService")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

class NFeNotasService:
    def __init__(self):
        logger.debug("Inicializando NFeNotasService")

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

    def registrar_notas(
        self,
        notas: Iterable[NotaExtraida],
        processamento_id: Optional[int] = None
    ) -> int:
        logger.debug("Iniciando registrar_notas")

        notas_list = list(notas)
        if not notas_list:
            logger.info("Nenhuma nota para registrar")
            return 0

        sql_insert = """
            INSERT INTO public.nfe_notas (
                processamento_id,
                numero_nf,
                emitente_cnpj,
                data_emissao,
                natureza_operacao,
                destinatario_documento,
                destinatario_nome,
                destinatario_cidade,
                destinatario_uf,
                valor_produtos,
                valor_desconto,
                valor_frete,
                valor_icms,
                valor_ipi,
                valor_pis,
                valor_cofins,
                valor_total_nf
            )
            SELECT
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1
                FROM public.nfe_notas
                WHERE numero_nf = %s
                  AND emitente_cnpj = %s
                  AND data_emissao = %s
            );
        """
        
        sql_atualizar_processamento = """
            UPDATE public.nfe_notas
            SET processamento_id = %s
            WHERE numero_nf = %s
              AND emitente_cnpj = %s
              AND data_emissao = %s
              AND processamento_id IS NULL;
        """

        valores = []
        for nota in notas_list:
            emitente_cnpj = normalizar_cnpj(nota.emitente_cnpj)
            valores.append(
                (
                    processamento_id,
                    str(nota.numero_nf),
                    emitente_cnpj,
                    nota.data_emissao,
                    nota.natureza_operacao,
                    nota.destinatario_documento,
                    nota.destinatario_nome,
                    nota.destinatario_cidade,
                    nota.destinatario_uf,
                    nota.valor_produtos,
                    nota.valor_desconto,
                    nota.valor_frete,
                    nota.valor_icms,
                    nota.valor_ipi,
                    nota.valor_pis,
                    nota.valor_cofins,
                    nota.valor_total_nf,
                    str(nota.numero_nf),
                    emitente_cnpj,
                    nota.data_emissao,
                )
            )

        try:
            #logger.debug("Abrindo conexão com PostgreSQL")
            with psycopg.connect(**self.conn_params) as conn:
                #logger.debug("Conexão aberta com sucesso")
                with conn.cursor() as cur:
                    #logger.debug("Executando INSERT em nfe_notas")
                    inseridos = 0
                    for valor in valores:
                        cur.execute(sql_insert, valor)
                        inseridos += cur.rowcount
                        if cur.rowcount == 0 and processamento_id is not None:
                            cur.execute(
                                sql_atualizar_processamento,
                                (
                                    processamento_id,
                                    valor[1],
                                    valor[2],
                                    valor[3],
                                ),
                            )
                            inseridos += cur.rowcount
                    logger.info(
                        "Notas registradas com sucesso: %s",
                        inseridos
                    )
            return inseridos
        except Exception:
            logger.exception("Erro ao registrar notas NFe")
            raise