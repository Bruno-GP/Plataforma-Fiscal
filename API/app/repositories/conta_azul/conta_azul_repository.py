from __future__ import annotations

import psycopg


class ContaAzulRepository:
  def __init__(self, conn_params: dict) -> None:
    self.conn_params = conn_params

  def listar_kpis(self, empresa_id: int, limite: int = 12) -> list[tuple]:
    sql = """
      SELECT mes, total_pedidos, clientes_ativos, receita_total, ticket_medio
      FROM conta_azul_kpis
      WHERE empresa_id = %s
      ORDER BY mes DESC
      LIMIT %s
    """
    try:
      with psycopg.connect(**self.conn_params) as conn:
        with conn.cursor() as cur:
          cur.execute(sql, (empresa_id, limite))
          return cur.fetchall()
    except psycopg.errors.UndefinedTable:
      return []
