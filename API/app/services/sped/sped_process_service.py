from psycopg import connect

from app.domain.sped.reader import resumir_registros_sped
from app.models.sped.schemas import (
  ProcessarSpedFiscalRequest,
  ProcessarSpedFiscalResponse,
  RegistroSpedResumo,
)
from app.services.sped.postgres_config import carregar_config_postgres_sped


class ProcessarSpedFiscalService:
  def __init__(self):
    self.config = carregar_config_postgres_sped()

  def _conn_params(self) -> dict:
    return {
      "host": self.config["host"],
      "port": self.config["port"],
      "dbname": self.config["database"],
      "user": self.config["user"],
      "password": self.config["password"],
      **({"sslmode": self.config["sslmode"]} if self.config.get("sslmode") else {}),
    }
  
  def executar(self, request: ProcessarSpedFiscalRequest) -> ProcessarSpedFiscalResponse:
    config = self.config

    # Validação rápida da conexão do banco SPED antes do processamento completo.
    with connect(**self._conn_params()) as conn:
      with conn.cursor() as cur:
        cur.execute("SELECT 1")

    registros, total_linhas = resumir_registros_sped(request.arquivo_sped)
    resumo_ordenado = sorted(registros.items(), key=lambda item: (-item[1], item[0]))

    return ProcessarSpedFiscalResponse(
      status="processado",
      arquivo_sped=request.arquivo_sped,
      total_linhas=total_linhas,
      total_registros_identificados=sum(registros.values()),
      resumo_registros=[
        RegistroSpedResumo(registro=registro, quantidade=quantidade)
        for registro, quantidade in resumo_ordenado
      ],
      banco_sped=config["database"],
    )
