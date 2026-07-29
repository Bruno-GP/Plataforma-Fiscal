from __future__ import annotations

from app.models.conta_azul.schemas import ContaAzulKpiMensal
from app.repositories.conta_azul.conta_azul_repository import ContaAzulRepository
from app.services.conta_azul.postgres_config import carregar_config_postgres_conta_azul


class ContaAzulConsultaService:
  def __init__(self) -> None:
    config = carregar_config_postgres_conta_azul()
    conn_params = {
      "host": config["host"],
      "port": config["port"],
      "dbname": config["database"],
      "user": config["user"],
      "password": config["password"],
      "connect_timeout": 5,
      **({"sslmode": config["sslmode"]} if config.get("sslmode") else {}),
    }
    self.repository = ContaAzulRepository(conn_params)

  def listar_kpis(self, empresa_id: int, limite: int = 12) -> list[ContaAzulKpiMensal]:
    rows = self.repository.listar_kpis(empresa_id, limite)
    return [
      ContaAzulKpiMensal(
        mes=row[0],
        total_pedidos=row[1],
        clientes_ativos=row[2],
        receita_total=row[3],
        ticket_medio=row[4],
      )
      for row in rows
    ]
