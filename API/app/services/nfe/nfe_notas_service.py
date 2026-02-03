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

    def registrar_notas(self, conn, notas, processamento_id=None) -> int:
        logger.warning("📌 Registrando notas no banco (modo seguro)")

        if not notas:
            logger.warning("Nenhuma nota para registrar")
            return 0

        sql = """
            INSERT INTO public.nfe_notas (
                processamento_id,
                numero_nf,
                emitente_cnpj,
                modelo,
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
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            ON CONFLICT (numero_nf, emitente_cnpj, data_emissao)
            DO UPDATE SET
                processamento_id = EXCLUDED.processamento_id;
        """

        total = 0

        with conn.cursor() as cur:
            for nota in notas:
                emitente_cnpj = normalizar_cnpj(nota.emitente_cnpj)
                cur.execute(sql, (
                    processamento_id,
                    str(nota.numero_nf),
                    emitente_cnpj,
                    nota.modelo,
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
                ))
                total += cur.rowcount

        logger.warning(f"✅ Notas afetadas no banco: {total}")
        return total
    
    def remover_notas_sem_cfop_venda(self, conn, processamento_id: int) -> int:
        logger.warning(
            "🧹 Removendo notas sem CFOP de venda para o processamento %s",
            processamento_id,
        )

        sql = """
            DELETE FROM public.nfe_notas AS n
            WHERE n.processamento_id = %s
              AND NOT EXISTS (
                SELECT 1
                FROM public.nfe_itens AS i
                JOIN public.cfops AS c
                  ON regexp_replace(COALESCE(c.codigo, ''), '\\D', '', 'g')
                     = regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g')
                WHERE i.nota_id = n.id
                  AND LEFT(
                        regexp_replace(COALESCE(c.codigo, ''), '\\D', '', 'g'),
                        1
                      ) IN ('5','6','7')
                  AND COALESCE(c.descricao, '') ILIKE 'venda%%'
              );
        """

        with conn.cursor() as cur:
            cur.execute(sql, (processamento_id,))
            removidas = cur.rowcount

        logger.warning("🧹 Notas removidas: %s", removidas)
        return removidas