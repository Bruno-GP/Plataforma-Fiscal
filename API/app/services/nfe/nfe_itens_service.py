import logging
from typing import Iterable
from decimal import Decimal

import psycopg

from app.domain.nfe.extractor import NotaExtraida
from app.services.NCM.ibpt_sync_service import IBPTSyncService
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
        self._ncm_fallback_cache: set[str] = set()

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
            WITH atualizacao AS (
                UPDATE public.notas_itens
                SET
                    empresa_id = %s,
                    cnpj = %s,
                    descricao = %s,
                    ncm = %s,
                    cfop = %s,
                    quantidade = %s,
                    valor_unitario = %s,
                    valor_total = %s
                WHERE nota_id = %s
                  AND item_numero = %s
                  AND produto_codigo = %s
                RETURNING id
            ),
            insercao AS (
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
            WHERE NOT EXISTS (SELECT 1 FROM atualizacao)
            RETURNING id
            )
            SELECT id FROM atualizacao
            UNION ALL
            SELECT id FROM insercao
            LIMIT 1;
        """

        try:
            #logger.debug("Abrindo conexão com PostgreSQL")
            #logger.debug("Conexão aberta com sucesso")
            with conn.cursor() as cur:
                inseridos = 0
                nota_ids_processadas: set[int] = set()
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
                    nota_ids_processadas.add(int(nota_id))
                    for item in nota.itens:
                        
                        codigo_produto = _limitar_texto(item.codigo_produto, 120)
                        descricao = _limitar_texto(item.descricao, 255)
                        ncm = _limitar_texto(item.ncm, 20)
                        cfop = _limitar_texto(item.cfop, 10)
                    
                        cur.execute(
                            sql_insert_item,
                            (
                                empresa_id,
                                cnpj,
                                descricao,
                                ncm,
                                cfop,
                                item.quantidade,
                                item.valor_unitario,
                                item.valor_total,
                                nota_id,
                                item.numero_item,
                                codigo_produto,
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
                            ),
                        )
                        item_row = cur.fetchone()
                        item_id = int(item_row[0]) if item_row else None
                        if item_id and getattr(item, "reforma_tributos", None):
                            self._registrar_tributos_reforma_item(
                                cur=cur,
                                nota_item_id=item_id,
                                empresa_cnpj=cnpj,
                                periodo_ano=nota.data_emissao.year,
                                periodo_mes=nota.data_emissao.month,
                                item=item,
                            )
                        inseridos += cur.rowcount

                if nota_ids_processadas:
                    self._registrar_documentos_reforma_agregados(cur, sorted(nota_ids_processadas))

                logger.info(
                    "Itens registrados com sucesso: %s",
                    inseridos,
                )

            return inseridos
        except Exception:
            logger.exception("Erro ao registrar itens NFe")
            raise

    def _registrar_tributos_reforma_item(
        self,
        cur,
        nota_item_id: int,
        empresa_cnpj: str,
        periodo_ano: int,
        periodo_mes: int,
        item,
    ) -> None:
        ncm_codigo = self._garantir_ncm_catalogo(cur, item.ncm)

        cur.execute(
            """
            DELETE FROM public.itens_documentos_fiscais_tributos it
            USING public.tributos t
            WHERE it.tributo_id = t.id
              AND it.nota_item_id = %s
              AND t.codigo = ANY(%s)
            """,
            (nota_item_id, ["CBS", "IBS", "IBS_UF", "IBS_MUN", "IS"]),
        )

        for tributo in item.reforma_tributos:
            valor_tributo = Decimal(tributo.get("valor_tributo") or 0)
            if valor_tributo == 0:
                continue

            cur.execute(
                """
                INSERT INTO public.itens_documentos_fiscais_tributos (
                    nota_item_id,
                    tributo_id,
                    empresa_cnpj,
                    periodo_ano,
                    periodo_mes,
                    numero_item,
                    produto_codigo,
                    ncm_codigo,
                    cfop,
                    cst_codigo,
                    classificacao_tributaria,
                    base_calculo,
                    aliquota,
                    valor_debito,
                    valor_credito,
                    valor_tributo,
                    natureza,
                    origem,
                    status,
                    observacoes
                )
                SELECT
                    %s,
                    t.id,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s::char(8),
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    0,
                    %s,
                    'debito',
                    'xml',
                    'ativo',
                    'Tributo da Reforma Tributaria extraido do XML.'
                FROM public.tributos t
                WHERE t.codigo = %s
                """,
                (
                    nota_item_id,
                    empresa_cnpj,
                    periodo_ano,
                    periodo_mes,
                    item.numero_item,
                    item.codigo_produto,
                    ncm_codigo,
                    item.cfop,
                    tributo.get("cst_codigo"),
                    tributo.get("classificacao_tributaria"),
                    tributo.get("base_calculo") or Decimal("0"),
                    tributo.get("aliquota") or Decimal("0"),
                    valor_tributo,
                    valor_tributo,
                    tributo.get("tributo_codigo"),
                ),
            )

    def _garantir_ncm_catalogo(self, cur, codigo_ncm: str | None) -> str | None:
        codigo = "".join(ch for ch in str(codigo_ncm or "") if ch.isdigit())[:8]
        if len(codigo) != 8:
            return None

        cur.execute("SELECT 1 FROM public.ncm_catalogo WHERE codigo = %s LIMIT 1", (codigo,))
        if cur.fetchone():
            return codigo

        if codigo not in self._ncm_fallback_cache:
            self._ncm_fallback_cache.add(codigo)
            try:
                IBPTSyncService().sincronizar(uf="SC", ncm=codigo)
            except Exception as exc:
                logger.warning("Fallback IBPT falhou para NCM %s: %s", codigo, exc)

        cur.execute("SELECT 1 FROM public.ncm_catalogo WHERE codigo = %s LIMIT 1", (codigo,))
        if cur.fetchone():
            return codigo

        logger.warning("NCM %s nao encontrado no catalogo; item sera gravado sem FK de NCM.", codigo)
        return None

    def _registrar_documentos_reforma_agregados(self, cur, nota_ids: list[int]) -> None:
        codigos_reforma = ["CBS", "IBS", "IBS_UF", "IBS_MUN", "IS"]

        cur.execute(
            """
            DELETE FROM public.documentos_fiscais_tributos dt
            USING public.tributos t
            WHERE dt.tributo_id = t.id
              AND dt.nota_id = ANY(%s)
              AND t.codigo = ANY(%s)
            """,
            (nota_ids, codigos_reforma),
        )

        cur.execute(
            """
            WITH agregados AS (
                SELECT
                    i.nota_id,
                    it.tributo_id,
                    it.empresa_cnpj,
                    it.periodo_ano,
                    it.periodo_mes,
                    SUM(COALESCE(it.base_calculo, 0)) AS base_calculo,
                    SUM(COALESCE(it.valor_debito, 0)) AS valor_debito,
                    SUM(COALESCE(it.valor_credito, 0)) AS valor_credito,
                    SUM(COALESCE(it.valor_tributo, 0)) AS valor_tributo
                FROM public.itens_documentos_fiscais_tributos it
                JOIN public.notas_itens i ON i.id = it.nota_item_id
                JOIN public.tributos t ON t.id = it.tributo_id
                WHERE i.nota_id = ANY(%s)
                  AND t.codigo = ANY(%s)
                GROUP BY 1, 2, 3, 4, 5
            ),
            documentos AS (
                INSERT INTO public.documentos_fiscais_tributos (
                    nota_id,
                    tributo_id,
                    empresa_cnpj,
                    periodo_ano,
                    periodo_mes,
                    modelo_documento,
                    chave_acesso,
                    tipo_operacao,
                    data_emissao,
                    base_calculo,
                    valor_debito,
                    valor_credito,
                    valor_tributo,
                    natureza,
                    origem,
                    status,
                    observacoes
                )
                SELECT
                    a.nota_id,
                    a.tributo_id,
                    a.empresa_cnpj,
                    a.periodo_ano,
                    a.periodo_mes,
                    n.modelo,
                    n.numero_nf::varchar,
                    CASE
                      WHEN EXISTS (
                        SELECT 1 FROM public.notas_itens ni
                        WHERE ni.nota_id = n.id
                          AND LEFT(regexp_replace(COALESCE(ni.cfop, ''), '\\D', '', 'g'), 1) IN ('1','2','3')
                      ) THEN 'entrada'
                      ELSE 'saida'
                    END,
                    n.data_emissao,
                    a.base_calculo,
                    a.valor_debito,
                    a.valor_credito,
                    a.valor_tributo,
                    'debito',
                    'xml',
                    'ativo',
                    'Tributo da Reforma Tributaria extraido do XML.'
                FROM agregados a
                JOIN public.notas n ON n.id = a.nota_id
                WHERE COALESCE(a.valor_tributo, 0) <> 0
                RETURNING id, nota_id, tributo_id
            )
            UPDATE public.itens_documentos_fiscais_tributos it
            SET documento_tributo_id = d.id
            FROM documentos d
            JOIN public.notas_itens ni ON ni.nota_id = d.nota_id
            WHERE it.nota_item_id = ni.id
              AND it.tributo_id = d.tributo_id
              AND ni.nota_id = ANY(%s)
            """,
            (nota_ids, codigos_reforma, nota_ids),
        )
