from typing import Dict
import psycopg

from app.services.nfe.postres_config import carregar_config_postgres

class ConnPostgresService:
  """Serviço simples para validar a conexão com o PostgreSQL."""

  def __init__(self):
    config = carregar_config_postgres()
    
    self.host = config["host"]
    self.port = config["port"]
    self.database = config["database"]
    self.user = config["user"]
    self.password = config["password"]

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
