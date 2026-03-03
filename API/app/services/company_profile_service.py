import psycopg

from app.services.nfe.empresa_service import normalizar_cnpj
from app.services.nfe.postres_config import carregar_config_postgres


class CompanyProfileService:
  def __init__(self) -> None:
    config = carregar_config_postgres()
    self.conn_params = {
      "host": config["host"],
      "port": config["port"],
      "dbname": config["database"],
      "user": config["user"],
      "password": config["password"],
      "connect_timeout": 5,
    }

  def _has_tem_sped_column(self, cur) -> bool:
    cur.execute(
      """
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = 'public'
        AND table_name = 'empresas'
        AND column_name = 'tem_sped'
      LIMIT 1;
      """
    )
    return cur.fetchone() is not None

  def empresa_tem_sped(self, cnpj: str) -> bool:
    cnpj_normalizado = normalizar_cnpj(cnpj)
    if not cnpj_normalizado:
      return False

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        if not self._has_tem_sped_column(cur):
          return False

        cur.execute(
          """
          SELECT COALESCE(tem_sped, false)
          FROM public.empresas
          WHERE regexp_replace(cnpj, '\\D', '', 'g') = %s
          LIMIT 1;
          """,
          (cnpj_normalizado,),
        )
        row = cur.fetchone()

    if not row:
      return False

    return bool(row[0])