from __future__ import annotations

import psycopg

from app.services.nfe.nfe_notas_service import NFeNotasService


class NFeNotasRepository:
  """Consulta notas NFe e tributos de itens com uma unica conexao."""

  def __init__(self, notas_service: NFeNotasService | None = None) -> None:
    self.notas_service = notas_service or NFeNotasService()

  def listar_notas_detalhadas(
    self,
    *,
    cnpj_empresa: str,
    periodo_ano: int,
    periodo_mes: int | None,
    tipo_operacao: str,
    limite: int,
    offset: int,
  ) -> tuple[int, list, dict[int, list[dict]]]:
    with psycopg.connect(**self.notas_service.conn_params) as conn:
      notas = self.notas_service.listar_notas_periodo_para_operacao(
        conn=conn,
        cnpj_empresa=cnpj_empresa,
        periodo_ano=periodo_ano,
        periodo_mes=periodo_mes,
        tipo_operacao=tipo_operacao,
      )
      notas_slice = notas[offset:offset + limite]
      item_ids = [
        item.id
        for nota in notas_slice
        for item in nota.itens
        if getattr(item, "id", None) is not None
      ]
      tributos_por_item = self.notas_service.listar_tributos_itens(conn, item_ids)

    return len(notas), notas_slice, tributos_por_item
