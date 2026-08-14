from __future__ import annotations

import psycopg

from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


class MetasEmpresasRepository:
    def __init__(self) -> None:
        self.config = carregar_config_postgres()

    def listar_empresas_xml_ativas(self) -> list[tuple[int, str]]:
        for options in opcoes_conexao_postgres(self.config):
            try:
                with psycopg.connect(**options) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT id, cnpj
                            FROM empresas
                            WHERE tem_xml = TRUE
                            ORDER BY id
                            """
                        )
                        return cur.fetchall()
            except psycopg.Error:
                continue
        return []
