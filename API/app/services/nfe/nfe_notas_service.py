import logging
from typing import Iterable, Optional
from decimal import Decimal
from datetime import date

import psycopg

from app.domain.nfe.extractor import NotaExtraida, ItemNota
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
    
    def listar_notas_periodo_para_kpi(
        self,
        conn,
        cnpj_emitente: str,
        periodo_ano: int,
        periodo_mes: int,
    ) -> list[NotaExtraida]:
        cnpj_normalizado = normalizar_cnpj(cnpj_emitente)
        if not cnpj_normalizado:
            return []

        sql_notas = """
            SELECT
                id,
                numero_nf,
                emitente_cnpj,
                modelo,
                data_emissao,
                natureza_operacao,
                destinatario_documento,
                destinatario_nome,
                destinatario_cidade,
                destinatario_uf,
                valor_total_nf,
                valor_icms,
                valor_ipi,
                valor_pis,
                valor_cofins,
                valor_produtos,
                valor_desconto,
                valor_frete
            FROM public.notas
            WHERE emitente_cnpj = %s
              AND EXTRACT(YEAR FROM data_emissao) = %s
              AND EXTRACT(MONTH FROM data_emissao) = %s
            ORDER BY data_emissao, numero_nf;
        """

        sql_itens = """
            SELECT
                nota_id,
                item_numero,
                produto_codigo,
                descricao,
                ncm,
                cfop,
                quantidade,
                valor_unitario,
                valor_total
            FROM public.notas_itens
            WHERE cnpj = %s
              AND nota_id = ANY(%s)
            ORDER BY nota_id, item_numero;
        """

        with conn.cursor() as cur:
            cur.execute(sql_notas, (cnpj_normalizado, periodo_ano, periodo_mes))
            notas_rows = cur.fetchall()

            if not notas_rows:
                return []

            nota_ids = [row[0] for row in notas_rows]

            cur.execute(sql_itens, (cnpj_normalizado, nota_ids))
            itens_rows = cur.fetchall()

        itens_por_nota: dict[int, list[ItemNota]] = {}
        for row in itens_rows:
            nota_id = row[0]
            itens_por_nota.setdefault(nota_id, []).append(
                ItemNota(
                    numero_item=int(row[1] or 0),
                    codigo_produto=row[2] or "",
                    descricao=row[3] or "",
                    ncm=row[4] or "",
                    cfop=row[5] or "",
                    unidade="",
                    quantidade=Decimal(row[6] or 0),
                    valor_unitario=Decimal(row[7] or 0),
                    valor_total=Decimal(row[8] or 0),
                )
            )

        notas: list[NotaExtraida] = []
        for row in notas_rows:
            nota_id = row[0]
            notas.append(
                NotaExtraida(
                    chave="",
                    numero_nf=int(row[1] or 0),
                    emitente_cnpj=row[2] or cnpj_normalizado,
                    modelo=row[3] or "",
                    data_emissao=row[4] if isinstance(row[4], date) else date.today(),
                    natureza_operacao=row[5] or "",
                    destinatario_documento=row[6] or "",
                    destinatario_nome=row[7] or "",
                    destinatario_cidade=row[8] or "",
                    destinatario_uf=row[9] or "",
                    valor_total_nf=Decimal(row[10] or 0),
                    valor_icms=Decimal(row[11] or 0),
                    valor_ipi=Decimal(row[12] or 0),
                    valor_pis=Decimal(row[13] or 0),
                    valor_cofins=Decimal(row[14] or 0),
                    valor_produtos=Decimal(row[15] or 0),
                    valor_desconto=Decimal(row[16] or 0),
                    valor_frete=Decimal(row[17] or 0),
                    itens=itens_por_nota.get(nota_id, []),
                )
            )

        return notas
    
    def remover_notas_sem_cfop_venda(self, conn, processamento_id: int) -> int:
        logger.warning(
            "🧹 Removendo notas sem CFOP de venda para o processamento %s",
            processamento_id,
        )

        sql = """
            DELETE FROM public.notas AS n
            WHERE n.processamento_id = %s
              AND COALESCE(n.modelo, '') <> 'NFSE'
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