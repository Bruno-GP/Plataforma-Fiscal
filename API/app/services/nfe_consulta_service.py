import logging
from typing import List, Optional

import psycopg

from app.models.schemas import NFeKPI, NFeKPIConsulta
from app.services.empresa_service import normalizar_cnpj
from app.services.postres_config import carregar_config_postgres

logger = logging.getLogger("NFeConsultaService")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

class NFeConsultaService:
    def __init__(self):
        logger.debug("Inicializando NFeConsultaService")

        config = carregar_config_postgres()
        logger.debug(f"Config PostgreSQL carregada: {config}")

        self.conn_params = {
            "host": config["host"],
            "port": config["port"],
            "dbname": config["database"],
            "user": config["user"],
            "password": config["password"],
            "connect_timeout": 5,
        }

    def listar_kpis(
        self,
        emitente_cnpj: Optional[str] = None,
        periodo_ano: Optional[int] = None,
        periodo_mes: Optional[int] = None,
        limite: int = 100,
        offset: int = 0,
    ) -> List[NFeKPIConsulta]:
        logger.debug("Iniciando listar_kpis")

        filtros = []
        parametros: List[object] = []

        if emitente_cnpj:
            filtros.append("p.cnpj_emitente = %s")
            parametros.append(normalizar_cnpj(emitente_cnpj))

        if periodo_ano:
            filtros.append("p.periodo_ano = %s")
            parametros.append(periodo_ano)

        if periodo_mes:
            filtros.append("p.periodo_mes = %s")
            parametros.append(periodo_mes)

        where_clause = " AND ".join(filtros)
        if where_clause:
            where_clause = f"WHERE {where_clause}"

        sql_kpis = f"""
            SELECT
                p.periodo_ano,
                p.periodo_mes,
                k.id,
                k.processamento_id,
                k.total_vendas,
                k.quantidade_notas,
                k.ticket_medio,
                k.maior_nota,
                k.menor_nota,
                k.total_icms,
                k.total_ipi,
                k.total_pis,
                k.total_cofins,
                k.top_clientes,
                k.top_produtos,
                k.top_cidades
            FROM public.nfe_processamentos AS p
            JOIN public.nfe_kpis AS k
                ON k.processamento_id = p.id
            {where_clause}
            ORDER BY p.data_processamento DESC NULLS LAST, p.id DESC
            LIMIT %s OFFSET %s;
        """
        parametros.extend([limite, offset])

        try:
            logger.debug("Abrindo conexão com PostgreSQL")
            with psycopg.connect(**self.conn_params) as conn:
                logger.debug("Conexão aberta com sucesso")
                with conn.cursor() as cur:
                    logger.debug("Consultando KPIs")
                    cur.execute(sql_kpis, parametros)
                    kpis_rows = cur.fetchall()

                    if not kpis_rows:
                        return []

            resultados = []
            for row in kpis_rows:
                resultados.append(
                    NFeKPIConsulta(
                        periodo_ano=row[0],
                        periodo_mes=row[1],
                        kpis=NFeKPI(
                            id=row[2],
                            processamento_id=row[3],
                            total_vendas=row[4] or 0,
                            quantidade_notas=row[5] or 0,
                            ticket_medio=row[6] or 0,
                            maior_nota=row[7] or 0,
                            menor_nota=row[8] or 0,
                            total_icms=row[9] or 0,
                            total_ipi=row[10] or 0,
                            total_pis=row[11] or 0,
                            total_cofins=row[12] or 0,
                            top_clientes=row[13] or [],
                            top_produtos=row[14] or [],
                            top_cidades=row[15] or [],
                        ),
                    )
                )

            return resultados
        except Exception:
            logger.exception("Erro ao consultar KPIs NFe")
            raise