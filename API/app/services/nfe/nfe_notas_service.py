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
        
    def _normalizar_cfop(self, cfop: Optional[str]) -> str:
        if not cfop:
            return ""
        return "".join(ch for ch in cfop if ch.isdigit())

    def obter_cfops_venda(self, conn) -> set[str]:
        sql = """
            SELECT c.codigo
            FROM public.notas_cfops AS c
            WHERE LEFT(
                    regexp_replace(COALESCE(c.codigo, ''), '\\D', '', 'g'),
                    1
                  ) IN ('5','6','7')
              AND COALESCE(c.descricao, '') ILIKE 'venda%%';
        """

        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

        return {
            self._normalizar_cfop(row[0])
            for row in rows
            if row and self._normalizar_cfop(row[0])
        }

    def filtrar_notas_com_cfop_venda(
        self,
        conn,
        notas: Iterable[NotaExtraida],
    ) -> list[NotaExtraida]:
        notas_list = list(notas)
        if not notas_list:
            return []

        cfops_venda = self.obter_cfops_venda(conn)
        if not cfops_venda:
            logger.warning(
                "Nenhum CFOP de venda encontrado na tabela de referência; "
                "usando fallback por prefixo (5/6/7)."
            )

        notas_filtradas: list[NotaExtraida] = []
        for nota in notas_list:
            tem_cfop_venda = False
            for item in nota.itens:
                cfop_normalizado = self._normalizar_cfop(item.cfop)
                if not cfop_normalizado:
                    continue

                if cfops_venda:
                    if cfop_normalizado in cfops_venda:
                        tem_cfop_venda = True
                        break
                elif cfop_normalizado[0] in {"5", "6", "7"}:
                    tem_cfop_venda = True
                    break

            if tem_cfop_venda:
                notas_filtradas.append(nota)

        return notas_filtradas

    def registrar_notas(self, conn, notas, processamento_id=None) -> int:
        logger.warning("📌 Registrando notas no banco (modo seguro)")

        if not notas:
            logger.warning("Nenhuma nota para registrar")
            return 0

        sql = """
            WITH atualizacao AS (
                UPDATE public.notas
                SET processamento_id = %s
                WHERE numero_nf = %s
                  AND emitente_cnpj = %s
                  AND data_emissao = %s
                RETURNING id
            )
            INSERT INTO public.notas (
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
            ) SELECT
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s
            WHERE NOT EXISTS (SELECT 1 FROM atualizacao);
        """

        total = 0
        notas_list = list(notas)
        batch_size = 500

        with conn.cursor() as cur:
            for start in range(0, len(notas_list), batch_size):
                chunk = notas_list[start:start + batch_size]
                valores = []
                for nota in chunk:
                    emitente_cnpj = normalizar_cnpj(nota.emitente_cnpj)
                    valores.append((
                        processamento_id,
                        str(nota.numero_nf),
                        emitente_cnpj,
                        nota.data_emissao,
                        
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
                    
                try:
                    cur.executemany(sql, valores)
                except psycopg.Error:
                    logger.exception(
                        "Erro ao registrar notas em lote %s-%s.",
                        start + 1,
                        min(start + batch_size, len(notas_list)),
                    )
                    raise
                
                total += len(chunk)
                logger.info(
                    "📌 Notas processadas até agora: %s/%s",
                    min(start + batch_size, len(notas_list)),
                    len(notas_list),
                )

        logger.warning(f"✅ Notas afetadas no banco: {total}")
        return total
    
    def remover_notas_sem_cfop_venda(self, conn, processamento_id: int) -> int:
        logger.warning(
            "🧹 Removendo notas sem CFOP de venda para o processamento %s",
            processamento_id,
        )

        sql = """
            DELETE FROM public.notas AS n
            WHERE n.processamento_id = %s
              AND NOT EXISTS (
                SELECT 1
                FROM public.notas_itens AS i
                LEFT JOIN public.notas_cfops AS c
                  ON regexp_replace(COALESCE(c.codigo, ''), '\\D', '', 'g')
                     = regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g')
                WHERE i.nota_id = n.id
                  AND (
                        (
                          LEFT(
                            regexp_replace(COALESCE(c.codigo, ''), '\\D', '', 'g'),
                            1
                          ) IN ('5','6','7')
                          AND COALESCE(c.descricao, '') ILIKE '%%venda%%'
                        )
                        OR LEFT(
                          regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'),
                          1
                        ) IN ('5','6','7')
                      )
              );
        """

        with conn.cursor() as cur:
            cur.execute(sql, (processamento_id,))
            removidas = cur.rowcount

        logger.warning("🧹 Notas removidas: %s", removidas)
        return removidas