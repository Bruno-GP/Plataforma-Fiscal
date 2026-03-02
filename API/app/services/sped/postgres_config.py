import os

def carregar_config_postgres_sped() -> dict:
  return {
    "host": os.environ.get("POSTGRES_SPED_HOST", os.environ["POSTGRES_HOST"]),
    "port": int(os.environ.get("POSTGRES_SPED_PORT", os.environ["POSTGRES_PORT"])),
    "database": os.environ.get("POSTGRES_SPED_DB", os.environ.get("POSTGRES_DB_SPED", os.environ["POSTGRES_DB"])),
    "user": os.environ.get("POSTGRES_SPED_USER", os.environ["POSTGRES_USER"]),
    "password": os.environ.get("POSTGRES_SPED_PASSWORD", os.environ["POSTGRES_PASSWORD"]),
  }