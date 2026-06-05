import logging
from typing import Iterable, Optional
from decimal import Decimal
from datetime import date

import psycopg

from app.domain.nfe.extractor import NotaExtraida, ItemNota
from app.services.fiscal.fiscal_sales import obter_cfops_faturamento_venda
from app.repositories.nfe.nfe_repository import NFeRepository
from app.services.nfe.postres_config import carregar_config_postgres
from app.services.nfe.empresa_service import normalizar_cnpj

logger = logging.getLogger("NFeNotasService")
logger.disabled = True

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
        self._nfe_repository = NFeRepository()

    def _obter_repositorio(self) -> NFeRepository:
        repo = getattr(self, "_nfe_repository", None)
        if repo is None:
            repo = NFeRepository()
            self._nfe_repository = repo
        return repo
        
    def _normalizar_cfop(self, cfop: Optional[str]) -> str:
        if not cfop:
            return ""
        return "".join(ch for ch in cfop if ch.isdigit())

    def obter_cfops_venda(self, conn) -> set[str]:
        rows = self._obter_repositorio().obter_cfops_venda(conn)

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

        total = 0
        notas_list = list(notas)
        batch_size = 500

        with conn.cursor() as cur:
            repository = self._obter_repositorio()
            for start in range(0, len(notas_list), batch_size):
                chunk = notas_list[start:start + batch_size]
                valores = []
                for nota in chunk:
                    emitente_cnpj = normalizar_cnpj(nota.emitente_cnpj)
                    valores.append((
                        processamento_id,
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
                        nota.modelo,
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
                    repository.registrar_notas(cur, valores)
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

        repository = self._obter_repositorio()
        notas_rows = repository.listar_notas_periodo_para_kpi(
            conn,
            cnpj_normalizado,
            periodo_ano,
            periodo_mes,
        )

        if not notas_rows:
            return []

        nota_ids = [row[0] for row in notas_rows]
        itens_rows = repository.listar_itens_por_nota_ids_para_kpi(
            conn,
            cnpj_normalizado,
            nota_ids,
        )

        return self._montar_notas_extraidas(
            notas_rows=notas_rows,
            itens_rows=itens_rows,
            cnpj_padrao=cnpj_normalizado,
        )

    def listar_notas_periodo_para_operacao(
        self,
        conn,
        cnpj_empresa: str,
        periodo_ano: int,
        periodo_mes: int | None,
        tipo_operacao: str,
    ) -> list[NotaExtraida]:
        cnpj_normalizado = normalizar_cnpj(cnpj_empresa)
        if not cnpj_normalizado:
            return []

        repository = self._obter_repositorio()
        notas_rows = repository.listar_notas_periodo_para_operacao(
            conn,
            cnpj_normalizado,
            periodo_ano,
            periodo_mes,
            tipo_operacao,
            obter_cfops_faturamento_venda() if tipo_operacao == "vendas" else None,
        )

        if not notas_rows:
            return []

        nota_ids = [row[0] for row in notas_rows]
        itens_rows = repository.listar_itens_por_nota_ids_para_operacao(conn, nota_ids)

        return self._montar_notas_extraidas(
            notas_rows=notas_rows,
            itens_rows=itens_rows,
            cnpj_padrao=cnpj_normalizado,
        )

    def _montar_notas_extraidas(
        self,
        notas_rows,
        itens_rows,
        cnpj_padrao: str,
    ) -> list[NotaExtraida]:
        itens_por_nota: dict[int, list[ItemNota]] = {}
        for row in itens_rows:
            item_id = row[0]
            nota_id = row[1]
            itens_por_nota.setdefault(nota_id, []).append(
                ItemNota(
                    id=item_id,
                    numero_item=int(row[2] or 0),
                    codigo_produto=row[3] or "",
                    descricao=row[4] or "",
                    ncm=row[5] or "",
                    cfop=row[6] or "",
                    unidade="",
                    quantidade=Decimal(row[7] or 0),
                    valor_unitario=Decimal(row[8] or 0),
                    valor_total=Decimal(row[9] or 0),
                )
            )

        notas: list[NotaExtraida] = []
        for row in notas_rows:
            nota_id = row[0]
            notas.append(
                NotaExtraida(
                    chave="",
                    numero_nf=int(row[1] or 0),
                    emitente_cnpj=row[2] or cnpj_padrao,
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
                    id=nota_id,
                )
            )

        return notas

    def listar_tributos_itens(
        self,
        conn,
        item_ids: list[int],
    ) -> dict[int, list[dict]]:
        if not item_ids:
            return {}

        rows = self._obter_repositorio().listar_tributos_itens(conn, item_ids)

        tributos_por_item: dict[int, list[dict]] = {}
        for row in rows:
            tributos_por_item.setdefault(row[0], []).append(
                {
                    "tributo_codigo": row[1],
                    "tributo_nome": row[2],
                    "base_calculo": Decimal(row[3] or 0),
                    "aliquota": Decimal(row[4]) if row[4] is not None else None,
                    "valor_debito": Decimal(row[5] or 0),
                    "valor_credito": Decimal(row[6] or 0),
                    "valor_tributo": Decimal(row[7] or 0),
                    "natureza": row[8],
                    "origem": row[9],
                    "status": row[10],
                }
            )

        return tributos_por_item
    
    def remover_notas_sem_cfop_venda(self, conn, processamento_id: int) -> int:
        logger.warning(
            "Removendo notas sem CFOP de venda para o processamento %s",
            processamento_id,
        )

        removidas = self._obter_repositorio().remover_notas_sem_cfop_venda(conn, processamento_id)

        logger.warning("Notas removidas: %s", removidas)
        return removidas

    def separar_notas_por_modelo(
        self,
        notas: Iterable[NotaExtraida],
    ) -> tuple[list[NotaExtraida], list[NotaExtraida]]:
        notas_list = list(notas)
        notas_nfse = [
            nota for nota in notas_list
            if (nota.modelo or "").strip().upper() == "NFSE"
        ]
        notas_demais_modelos = [
            nota for nota in notas_list
            if (nota.modelo or "").strip().upper() != "NFSE"
        ]
        return notas_nfse, notas_demais_modelos
