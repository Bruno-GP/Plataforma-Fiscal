import psycopg

from app.services.nfe.empresa_service import normalizar_cnpj
from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


class CompanyProfileService:
    _required_empresas_columns = {
        "id",
        "cnpj",
        "nome",
        "tem_sped",
        "tem_conta_azul",
        "tem_xml",
        "estado",
        "cidade",
        "municipio_id",
        "codigo_ibge",
    }

    def __init__(self) -> None:
        config = carregar_config_postgres()
        self.conn_options = opcoes_conexao_postgres(config)
        self._validate_empresas_schema()

    def _connect(self):
        last_error: Exception | None = None
        for options in self.conn_options:
            try:
                return psycopg.connect(**options)
            except psycopg.Error as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("Configuracao PostgreSQL invalida.")

    def _validate_empresas_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'empresas';
                    """
                )
                existing_columns = {str(row[0]) for row in cur.fetchall()}

        missing_columns = sorted(self._required_empresas_columns - existing_columns)
        if missing_columns:
            raise RuntimeError(
                "Tabela public.empresas incompleta ou ausente. Execute as migrations Alembic. "
                f"Colunas ausentes: {', '.join(missing_columns)}."
            )

    def _get_company_flags(self, cnpj: str) -> tuple[bool, bool, bool]:
        cnpj_normalizado = normalizar_cnpj(cnpj)
        if not cnpj_normalizado:
            return False, False, False

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COALESCE(tem_sped, false),
                           COALESCE(tem_conta_azul, false),
                           COALESCE(tem_xml, false)
                    FROM public.empresas
                    WHERE regexp_replace(cnpj, '\\D', '', 'g') = %s
                    LIMIT 1;
                    """,
                    (cnpj_normalizado,),
                )
                row = cur.fetchone()

        if not row:
            return False, False, False

        return bool(row[0]), bool(row[1]), bool(row[2])

    def empresa_tem_sped(self, cnpj: str) -> bool:
        tem_sped, _, _ = self._get_company_flags(cnpj)
        return tem_sped

    def empresa_tem_conta_azul(self, cnpj: str) -> bool:
        _, tem_conta_azul, _ = self._get_company_flags(cnpj)
        return tem_conta_azul

    def empresa_tem_xml(self, cnpj: str) -> bool:
        _, _, tem_xml = self._get_company_flags(cnpj)
        return tem_xml

    def obter_empresa(self, cnpj: str) -> dict | None:
        cnpj_normalizado = normalizar_cnpj(cnpj)
        if not cnpj_normalizado:
            return None

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, cnpj, nome, tem_sped, tem_conta_azul, tem_xml, estado, cidade, municipio_id, codigo_ibge
                    FROM public.empresas
                    WHERE regexp_replace(cnpj, '\\D', '', 'g') = %s
                    LIMIT 1;
                    """,
                    (cnpj_normalizado,),
                )
                row = cur.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "cnpj": row[1],
            "nome": row[2],
            "tem_sped": bool(row[3]),
            "tem_conta_azul": bool(row[4]),
            "tem_xml": bool(row[5]),
            "estado": (row[6] or "").strip() if row[6] else "",
            "cidade": (row[7] or "").strip() if row[7] else "",
            "municipio_id": (row[8] or "").strip() if row[8] else "",
            "codigo_ibge": (row[9] or "").strip() if row[9] else "",
        }
