from __future__ import annotations

import psycopg

from app.services.nfe.postres_config import carregar_config_postgres
from app.services.reforma_tributaria.reforma_tributaria_sync_service import (
  ReformaTributariaSyncService,
)


class ReformaTributariaBackfillRepository:
  """Executa backfill da Reforma com controle explicito de conexao/transacao."""

  def __init__(self) -> None:
    config = carregar_config_postgres()
    self.conn_params = {
      "host": config["host"],
      "port": config["port"],
      "dbname": config["database"],
      "user": config["user"],
      "password": config["password"],
    }

    if config.get("conninfo"):
      self.conn_params = {"conninfo": config["conninfo"]}
    if config.get("sslmode"):
      self.conn_params["sslmode"] = config["sslmode"]

  def executar(self, *, emitente_cnpj: str, origem: str) -> list[dict]:
    with psycopg.connect(**self.conn_params) as conn:
      sync_service = ReformaTributariaSyncService()
      if origem == "sped":
        resultados = sync_service.sincronizar_sped_todos_periodos(conn, emitente_cnpj)
      else:
        resultados = sync_service.sincronizar_nfe_todos_periodos(conn, emitente_cnpj)
      conn.commit()
      return resultados
