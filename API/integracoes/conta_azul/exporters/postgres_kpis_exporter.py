"""Exportador Postgres para conta_azul_kpis. Mesma interface espiritual dos
outros exporters (recebe dado ja calculado, grava), mas assinatura propria
porque o destino e' uma tabela agregada por empresa, nao um arquivo por
recurso.
"""

from __future__ import annotations

from psycopg2.extensions import connection as PgConnection

from contaazul.kpis import KpiMensal

_UPSERT_SQL = """
    INSERT INTO conta_azul_kpis
        (empresa_id, mes, total_pedidos, clientes_ativos, receita_total, ticket_medio, atualizado_em)
    VALUES (%s, %s, %s, %s, %s, %s, now())
    ON CONFLICT (empresa_id, mes) DO UPDATE SET
        total_pedidos   = EXCLUDED.total_pedidos,
        clientes_ativos = EXCLUDED.clientes_ativos,
        receita_total   = EXCLUDED.receita_total,
        ticket_medio    = EXCLUDED.ticket_medio,
        atualizado_em   = now()
"""


class PostgresKpisExporter:
    def export(self, empresa_id: int, kpis_por_mes: dict, conn: PgConnection) -> int:
        with conn.cursor() as cur:
            for kpi in kpis_por_mes.values():
                kpi: KpiMensal
                cur.execute(
                    _UPSERT_SQL,
                    (
                        empresa_id,
                        kpi.mes,
                        kpi.total_pedidos,
                        kpi.clientes_ativos,
                        kpi.receita_total,
                        kpi.ticket_medio,
                    ),
                )
        conn.commit()
        return len(kpis_por_mes)
