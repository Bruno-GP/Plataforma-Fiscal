import logging

import psycopg

from app.services.Municipios.municipios_catalog_service import MunicipiosCatalogService
from app.services.nfe.postres_config import carregar_config_postgres

# =========================
# LOG CONFIG
# =========================
logger = logging.getLogger("EmpresaService")
logger.disabled = True

# =========================
# UTILS
# =========================
def normalizar_cnpj(cnpj: str) -> str:
    return "".join(ch for ch in (cnpj or "").upper() if ch.isalnum())


def _normalizar_localidade(valor: str | None) -> str | None:
    texto = (valor or "").strip()
    return texto or None


def _normalizar_codigo_municipio(valor: str | None) -> str | None:
    codigo = MunicipiosCatalogService.normalizar_codigo_ibge(valor)
    return codigo or None


# =========================
# SERVICE
# =========================
class EmpresaService:
    def __init__(self):
        logger.debug("Inicializando EmpresaService")

        config = carregar_config_postgres()
        self.conn_params = {
            "host": config["host"],
            "port": config["port"],
            "dbname": config["database"],
            "user": config["user"],
            "password": config["password"],
            "connect_timeout": 5,
        }

    def _resolver_localidade(
        self,
        estado: str | None = None,
        cidade: str | None = None,
        municipio_id: str | None = None,
        codigo_ibge: str | None = None,
    ) -> tuple[str | None, str | None, str | None, str | None]:
        estado_normalizado = MunicipiosCatalogService.normalizar_uf(estado) or _normalizar_localidade(estado)
        cidade_normalizada = _normalizar_localidade(cidade)
        municipio_id_normalizado = _normalizar_codigo_municipio(municipio_id)
        codigo_ibge_normalizado = _normalizar_codigo_municipio(codigo_ibge)

        municipio_catalogo = MunicipiosCatalogService.resolver_municipio(
            uf=estado_normalizado,
            nome=cidade_normalizada,
            municipio_id=municipio_id_normalizado,
            codigo_ibge=codigo_ibge_normalizado,
        )

        if municipio_catalogo:
            estado_normalizado = municipio_catalogo["uf"]
            cidade_normalizada = municipio_catalogo["nome"]
            municipio_id_normalizado = municipio_catalogo["municipio_id"]
            codigo_ibge_normalizado = municipio_catalogo["codigo_ibge"]

        return (
            estado_normalizado,
            cidade_normalizada,
            municipio_id_normalizado,
            codigo_ibge_normalizado,
        )

    def obter_ou_criar(
        self,
        cnpj_emitente: str,
        nome_emitente: str,
        estado: str | None = None,
        cidade: str | None = None,
        municipio_id: str | None = None,
        codigo_ibge: str | None = None,
    ) -> int:
        logger.debug("Iniciando obter_ou_criar")

        cnpj = normalizar_cnpj(cnpj_emitente)
        (
            estado_normalizado,
            cidade_normalizada,
            municipio_id_normalizado,
            codigo_ibge_normalizado,
        ) = self._resolver_localidade(estado, cidade, municipio_id, codigo_ibge)

        try:
            with psycopg.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    sql_insert = """
                        INSERT INTO public.empresas (cnpj, nome, estado, cidade, municipio_id, codigo_ibge)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (cnpj)
                        DO UPDATE SET
                            nome = EXCLUDED.nome,
                            estado = COALESCE(EXCLUDED.estado, public.empresas.estado),
                            cidade = COALESCE(EXCLUDED.cidade, public.empresas.cidade),
                            municipio_id = COALESCE(EXCLUDED.municipio_id, public.empresas.municipio_id),
                            codigo_ibge = COALESCE(EXCLUDED.codigo_ibge, public.empresas.codigo_ibge)
                        RETURNING id;
                    """

                    cur.execute(
                        sql_insert,
                        (
                            cnpj,
                            nome_emitente,
                            estado_normalizado,
                            cidade_normalizada,
                            municipio_id_normalizado,
                            codigo_ibge_normalizado,
                        ),
                    )

                    row = cur.fetchone()
                    if row:
                        return row[0]

                    cur.execute(
                        """
                        SELECT id
                        FROM public.empresas
                        WHERE cnpj = %s;
                        """,
                        (cnpj,),
                    )
                    row = cur.fetchone()

                    if not row:
                        logger.error("Empresa não encontrada nem após fallback")
                        raise RuntimeError(
                            f"Falha crítica ao obter ou criar empresa. CNPJ={cnpj}"
                        )

                    return row[0]

        except Exception:
            logger.exception("ERRO AO OBTER OU CRIAR EMPRESA")
            raise

    def atualizar_localidade(
        self,
        cnpj_emitente: str,
        estado: str | None = None,
        cidade: str | None = None,
        municipio_id: str | None = None,
        codigo_ibge: str | None = None,
    ) -> None:
        cnpj = normalizar_cnpj(cnpj_emitente)
        (
            estado_normalizado,
            cidade_normalizada,
            municipio_id_normalizado,
            codigo_ibge_normalizado,
        ) = self._resolver_localidade(estado, cidade, municipio_id, codigo_ibge)

        if not (estado_normalizado or cidade_normalizada or municipio_id_normalizado or codigo_ibge_normalizado):
            return

        with psycopg.connect(**self.conn_params) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.empresas
                    SET estado = COALESCE(%s, estado),
                        cidade = COALESCE(%s, cidade),
                        municipio_id = COALESCE(%s, municipio_id),
                        codigo_ibge = COALESCE(%s, codigo_ibge)
                    WHERE regexp_replace(UPPER(cnpj), '[^0-9A-Z]', '', 'g') = %s;
                    """,
                    (
                        estado_normalizado,
                        cidade_normalizada,
                        municipio_id_normalizado,
                        codigo_ibge_normalizado,
                        cnpj,
                    ),
                )
            conn.commit()

    def atualizar_cnae(
        self,
        cnpj_emitente: str,
        cnae_fiscal: str | None = None,
        cnae_fiscal_descricao: str | None = None,
    ) -> None:
        cnpj = normalizar_cnpj(cnpj_emitente)

        if not (cnae_fiscal or cnae_fiscal_descricao):
            return

        with psycopg.connect(**self.conn_params) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.empresas
                    SET cnae_fiscal = COALESCE(%s, cnae_fiscal),
                        cnae_fiscal_descricao = COALESCE(%s, cnae_fiscal_descricao)
                    WHERE regexp_replace(UPPER(cnpj), '[^0-9A-Z]', '', 'g') = %s;
                    """,
                    (
                        cnae_fiscal,
                        cnae_fiscal_descricao,
                        cnpj,
                    ),
                )
            conn.commit()
