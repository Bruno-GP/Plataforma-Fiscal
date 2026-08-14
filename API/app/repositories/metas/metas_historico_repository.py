from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


class MetasHistoricoRepository:
    def __init__(self) -> None:
        self.config = carregar_config_postgres()

    def _connect(self):
        last_error: Exception | None = None
        for options in opcoes_conexao_postgres(self.config):
            try:
                return psycopg.connect(**options, row_factory=dict_row)
            except psycopg.Error as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("Configuracao PostgreSQL invalida.")

    def agregar_por_empresa(self, cnpj_normalizado: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        DATE_TRUNC('month', MAKE_DATE(periodo_ano, periodo_mes, 1))::date AS periodo_referencia,
                        COALESCE(SUM(total_vendas), 0) AS faturamento,
                        COALESCE(SUM(quantidade_notas), 0) AS quantidade_notas,
                        CASE
                            WHEN COALESCE(SUM(quantidade_notas), 0) > 0
                                THEN COALESCE(SUM(total_vendas), 0) / COALESCE(SUM(quantidade_notas), 0)
                            ELSE 0
                        END AS ticket_medio,
                        COALESCE(SUM(total_icms), 0) AS total_icms,
                        COALESCE(SUM(total_ipi), 0) AS total_ipi,
                        COALESCE(SUM(total_pis), 0) + COALESCE(SUM(total_cofins), 0) AS total_pis_cofins
                    FROM notas_kpis
                    WHERE regexp_replace(UPPER(COALESCE(emitente_cnpj, '')), '[^0-9A-Z]', '', 'g') = %s
                      AND periodo_ano IS NOT NULL
                      AND periodo_mes IS NOT NULL
                    GROUP BY periodo_ano, periodo_mes
                    ORDER BY periodo_ano, periodo_mes
                    """,
                    (cnpj_normalizado,),
                )
                return [dict(row) for row in cur.fetchall()]

    def upsert_historico(
        self,
        empresa_id: int,
        indicador_id_por_chave: dict[str, int],
        linhas: list[dict[str, Any]],
    ) -> int:
        if not linhas or not indicador_id_por_chave:
            return 0

        valores: list[tuple[Any, ...]] = []
        for linha in linhas:
            for chave, indicador_id in indicador_id_por_chave.items():
                if chave not in linha:
                    continue
                valores.append((empresa_id, indicador_id, linha["periodo_referencia"], linha[chave]))

        if not valores:
            return 0

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO indicador_historico (empresa_id, indicador_id, periodo_referencia, valor)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (empresa_id, indicador_id, periodo_referencia)
                    DO UPDATE SET valor = EXCLUDED.valor, calculado_em = NOW()
                    """,
                    valores,
                )
            conn.commit()
        return len(valores)
