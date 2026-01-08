import psycopg
from psycopg.types.json import Json

from app.services.postres_config import carregar_config_postgres

class NFeProcessamentosService:
    def __init__(self):
        config = carregar_config_postgres()
        self.conn_params = {
            "host": config["host"],
            "port": config["port"],
            "dbname": config["database"],
            "user": config["user"],
            "password": config["password"],
        }

    def registrar_processamento(
        self,
        empresa_id: int,
        cnpj_emitente: str,
        periodo_ano: int,
        periodo_mes: int,
        origem: str,
        pasta_xml: str,
        periodo_solicitado: str,
        periodos_encontrados: list,
        notas_processadas: int,
        itens_processados: int,
        status: str,
        data_processamento
    ) -> int:
        sql = """
            INSERT INTO public.nfe_processamentos (
                empresa_id,
                cnpj_emitente,
                periodo_ano,
                periodo_mes,
                origem,
                pasta_xml,
                periodo_solicitado,
                periodos_encontrados,
                notas_processadas,
                itens_processados,
                status,
                data_processamento
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id;
        """

        valores = (
            empresa_id,
            cnpj_emitente,
            periodo_ano,
            periodo_mes,
            origem,
            pasta_xml,
            periodo_solicitado,
            Json(periodos_encontrados),
            notas_processadas,
            itens_processados,
            status,
            data_processamento,
        )

        with psycopg.connect(**self.conn_params) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, valores)
                return cur.fetchone()[0]
