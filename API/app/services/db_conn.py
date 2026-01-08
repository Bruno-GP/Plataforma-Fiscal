import os
from typing import Dict
import psycopg

class ConnPostgresService:
    """Serviço simples para validar a conexão com o PostgreSQL."""

    def __init__(self):
      self.host = os.environ["POSTGRES_HOST"]
      self.port = int(os.environ["POSTGRES_PORT"])
      self.database = os.environ["POSTGRES_DB"]
      self.user = os.environ["POSTGRES_USER"]
      self.password = os.environ["POSTGRES_PASSWORD"]

    def executar(self) -> Dict:
      servidor = f"{self.host}:{self.port}/{self.database}"

      try:
        with psycopg.connect(
          host=self.host,
          port=self.port,
          dbname=self.database,
          user=self.user,
          password=self.password,
          connect_timeout=5
        ) as conn:
          with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()

        return {
          "sucesso": True,
          "detalhes": "Conexão com o PostgreSQL estabelecida com sucesso.",
          "servidor": servidor
        }

      except Exception as exc:
        return {
          "sucesso": False,
          "detalhes": f"Erro ao conectar ao PostgreSQL: {exc}",
          "servidor": servidor
        }
