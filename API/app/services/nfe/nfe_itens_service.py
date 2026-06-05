import logging
from typing import Iterable
from decimal import Decimal

import psycopg

from app.domain.nfe.extractor import NotaExtraida
from app.repositories.nfe.itens_repository import NFeItensRepository
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
        self.itens_repository = NFeItensRepository(self.conn_params)
        self._ncm_fallback_cache: set[str] = set()

    def _itens_repository(self) -> NFeItensRepository:
        repository = getattr(self, "itens_repository", None)
        if repository is None:
            repository = NFeItensRepository(self.conn_params)
            self.itens_repository = repository

        return repository

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

        try:
            #logger.debug("Abrindo conexão com PostgreSQL")
            #logger.debug("Conexão aberta com sucesso")
            with conn.cursor() as cur:
                inseridos = 0
                nota_ids_processadas: set[int] = set()
                repository = self._itens_repository()
                for nota in notas_list:
                    emitente_cnpj = normalizar_cnpj(nota.emitente_cnpj)
                    resultado = repository.obter_nota_para_registrar_itens(
                        cur,
                        str(nota.numero_nf),
                        emitente_cnpj,
                        nota.modelo,
                        nota.data_emissao,
                    )
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

                        item_row = repository.upsert_item_nota(
                            cur,
                            nota_id=nota_id,
                            empresa_id=empresa_id,
                            cnpj=cnpj,
                            item_numero=item.numero_item,
                            produto_codigo=codigo_produto,
                            descricao=descricao,
                            ncm=ncm,
                            cfop=cfop,
                            quantidade=item.quantidade,
                            valor_unitario=item.valor_unitario,
                            valor_total=item.valor_total,
                        )
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
        repository = self._itens_repository()
        ncm_codigo = self._garantir_ncm_catalogo(cur, item.ncm)

        repository.remover_tributos_reforma_item(cur, nota_item_id)

        for tributo in item.reforma_tributos:
            valor_tributo = Decimal(tributo.get("valor_tributo") or 0)
            if valor_tributo == 0:
                continue

            repository.inserir_tributo_reforma_item(
                cur,
                nota_item_id=nota_item_id,
                empresa_cnpj=empresa_cnpj,
                periodo_ano=periodo_ano,
                periodo_mes=periodo_mes,
                numero_item=item.numero_item,
                produto_codigo=item.codigo_produto,
                ncm_codigo=ncm_codigo,
                cfop=item.cfop,
                tributo=tributo,
            )

    def _garantir_ncm_catalogo(self, cur, codigo_ncm: str | None) -> str | None:
        codigo = "".join(ch for ch in str(codigo_ncm or "") if ch.isdigit())[:8]
        if len(codigo) != 8:
            return None

        repository = self._itens_repository()
        if repository.ncm_catalogo_existe(cur, codigo):
            return codigo

        if codigo not in self._ncm_fallback_cache:
            self._ncm_fallback_cache.add(codigo)
            try:
                IBPTSyncService().sincronizar(uf="SC", ncm=codigo)
            except Exception as exc:
                logger.warning("Fallback IBPT falhou para NCM %s: %s", codigo, exc)

        if repository.ncm_catalogo_existe(cur, codigo):
            return codigo

        logger.warning("NCM %s nao encontrado no catalogo; item sera gravado sem FK de NCM.", codigo)
        return None

    def _registrar_documentos_reforma_agregados(self, cur, nota_ids: list[int]) -> None:
        repository = self._itens_repository()
        repository.registrar_documentos_reforma_agregados(
            cur,
            nota_ids,
            ["CBS", "IBS", "IBS_UF", "IBS_MUN", "IS"],
        )
