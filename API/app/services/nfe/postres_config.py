import os

def carregar_config_postgres() -> dict:
  return {
    "host": os.environ.get("POSTGRES_NFE_HOST", os.environ["POSTGRES_HOST"]),
    "port": int(os.environ.get("POSTGRES_NFE_PORT", os.environ["POSTGRES_PORT"])),
    "database": os.environ.get("POSTGRES_NFE_DB", os.environ.get("POSTGRES_DB_NFE", os.environ["POSTGRES_DB"])),
    "user": os.environ.get("POSTGRES_NFE_USER", os.environ["POSTGRES_USER"]),
    "password": os.environ.get("POSTGRES_NFE_PASSWORD", os.environ["POSTGRES_PASSWORD"]),
  }