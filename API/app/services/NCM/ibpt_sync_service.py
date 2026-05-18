from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import logging

import psycopg

from app.core.cache import ttl_cache
from app.core.http_client import get_json
from app.services.nfe.postres_config import carregar_config_postgres


logger = logging.getLogger("IBPTSyncService")

IBPT_BASE_URL = "https://api-ibpt.seunegocionanuvem.com.br"
TODAS_UFS = (
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
    "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
    "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
)


@dataclass(frozen=True)
class SyncUFResultado:
    uf: str
    registros_recebidos: int
    catalogo_sincronizado: int
    tributacao_sincronizada: int


class IBPTSyncService:
    _required_columns_by_table = {
        "ncm_catalogo": {
            "codigo",
            "descricao",
            "codigo_formatado",
            "vigencia",
            "fonte_arquivo",
            "criado_em",
            "atualizado_em",
        },
        "ncm_tributacao": {
            "id",
            "ncm_codigo",
            "uf",
            "nacional_federal",
            "importados_federal",
            "estadual",
            "municipal",
            "vigencia_inicio",
            "vigencia_fim",
            "versao",
            "fonte",
            "criado_em",
            "atualizado_em",
        },
    }

    def __init__(self) -> None:
        config = carregar_config_postgres()
        self.conn_params = {
            "host": config["host"],
            "port": config["port"],
            "dbname": config["database"],
            "user": config["user"],
            "password": config["password"],
            "connect_timeout": 10,
            **({"sslmode": config["sslmode"]} if config.get("sslmode") else {}),
        }

    def _validate_ibpt_schema(self, conn: psycopg.Connection) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = ANY(%s)
                """,
                (list(self._required_columns_by_table),),
            )
            existing_columns: dict[str, set[str]] = {
                table_name: set()
                for table_name in self._required_columns_by_table
            }
            for table_name, column_name in cur.fetchall():
                existing_columns[str(table_name)].add(str(column_name))

        missing_parts = []
        for table_name, required_columns in self._required_columns_by_table.items():
            missing_columns = sorted(required_columns - existing_columns[table_name])
            if missing_columns:
                missing_parts.append(f"{table_name}: {', '.join(missing_columns)}")

        if missing_parts:
            raise RuntimeError(
                "Schema IBPT/NCM incompleto. Execute as migrations Alembic. "
                f"Colunas ausentes em public: {'; '.join(missing_parts)}."
            )

    @staticmethod
    def _normalizar_ncm(valor: str | None) -> str:
        return "".join(ch for ch in str(valor or "") if ch.isdigit())[:8]

    @staticmethod
    def _formatar_ncm(codigo: str) -> str:
        codigo_normalizado = codigo.zfill(8)
        if len(codigo_normalizado) != 8:
            return codigo
        return f"{codigo_normalizado[:4]}.{codigo_normalizado[4:6]}.{codigo_normalizado[6:]}"

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None

        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

        return None

    @staticmethod
    def _to_decimal(value: object) -> Decimal:
        if value in (None, ""):
            return Decimal("0.00")
        return Decimal(str(value))

    def _buscar_todos_ncm_uf(self, uf: str) -> list[dict]:
        payload = get_json(
            f"{IBPT_BASE_URL}/api_ibpt_json.php",
            params={"uf": uf},
            timeout_seconds=60.0,
            service_name="IBPT",
        )

        registros = payload.get("ncm", [])
        if not isinstance(registros, list):
            return []
        return registros

    def _buscar_ncm_especifico(self, ncm: str, uf: str) -> list[dict]:
        payload = get_json(
            f"{IBPT_BASE_URL}/api_ibpt.php",
            params={"codigo": ncm, "uf": uf},
            timeout_seconds=30.0,
            service_name="IBPT",
        )

        if isinstance(payload, dict) and payload.get("codigo"):
            return [payload]
        return []

    def _upsert_catalogo(self, conn: psycopg.Connection, registros: list[dict]) -> int:
        dados: list[dict] = []
        for registro in registros:
            codigo = self._normalizar_ncm(registro.get("codigo"))
            if len(codigo) != 8:
                continue

            dados.append(
                {
                    "codigo": codigo,
                    "descricao": str(registro.get("descricao") or "").strip(),
                    "codigo_formatado": self._formatar_ncm(codigo),
                    "vigencia": self._parse_date(registro.get("vigenciainicio")),
                    "fonte_arquivo": str(registro.get("fonte") or "IBPT").strip()[:255],
                }
            )

        if not dados:
            return 0

        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO public.ncm_catalogo (
                    codigo,
                    descricao,
                    codigo_formatado,
                    vigencia,
                    fonte_arquivo,
                    atualizado_em
                )
                VALUES (
                    %(codigo)s,
                    %(descricao)s,
                    %(codigo_formatado)s,
                    %(vigencia)s,
                    %(fonte_arquivo)s,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (codigo) DO UPDATE
                SET
                    descricao = EXCLUDED.descricao,
                    codigo_formatado = EXCLUDED.codigo_formatado,
                    vigencia = COALESCE(EXCLUDED.vigencia, public.ncm_catalogo.vigencia),
                    fonte_arquivo = EXCLUDED.fonte_arquivo,
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE
                    public.ncm_catalogo.descricao IS DISTINCT FROM EXCLUDED.descricao
                    OR public.ncm_catalogo.codigo_formatado IS DISTINCT FROM EXCLUDED.codigo_formatado
                    OR public.ncm_catalogo.vigencia IS DISTINCT FROM EXCLUDED.vigencia
                    OR public.ncm_catalogo.fonte_arquivo IS DISTINCT FROM EXCLUDED.fonte_arquivo;
                """,
                dados,
            )

        return len(dados)

    def _upsert_tributacao(self, conn: psycopg.Connection, registros: list[dict], uf: str) -> int:
        dados: list[dict] = []
        for registro in registros:
            codigo = self._normalizar_ncm(registro.get("codigo"))
            if len(codigo) != 8:
                continue

            dados.append(
                {
                    "ncm_codigo": codigo,
                    "uf": uf,
                    "nacional_federal": self._to_decimal(registro.get("nacionalfederal")),
                    "importados_federal": self._to_decimal(registro.get("importadosfederal")),
                    "estadual": self._to_decimal(registro.get("estadual")),
                    "municipal": self._to_decimal(registro.get("municipal")),
                    "vigencia_inicio": self._parse_date(registro.get("vigenciainicio")),
                    "vigencia_fim": self._parse_date(registro.get("vigenciafim")),
                    "versao": str(registro.get("versao") or "").strip()[:20],
                    "fonte": str(registro.get("fonte") or "IBPT").strip()[:100],
                }
            )

        if not dados:
            return 0

        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO public.ncm_tributacao (
                    ncm_codigo,
                    uf,
                    nacional_federal,
                    importados_federal,
                    estadual,
                    municipal,
                    vigencia_inicio,
                    vigencia_fim,
                    versao,
                    fonte,
                    atualizado_em
                )
                VALUES (
                    %(ncm_codigo)s,
                    %(uf)s,
                    %(nacional_federal)s,
                    %(importados_federal)s,
                    %(estadual)s,
                    %(municipal)s,
                    %(vigencia_inicio)s,
                    %(vigencia_fim)s,
                    %(versao)s,
                    %(fonte)s,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (ncm_codigo, uf) DO UPDATE
                SET
                    nacional_federal = EXCLUDED.nacional_federal,
                    importados_federal = EXCLUDED.importados_federal,
                    estadual = EXCLUDED.estadual,
                    municipal = EXCLUDED.municipal,
                    vigencia_inicio = EXCLUDED.vigencia_inicio,
                    vigencia_fim = EXCLUDED.vigencia_fim,
                    versao = EXCLUDED.versao,
                    fonte = EXCLUDED.fonte,
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE
                    public.ncm_tributacao.nacional_federal IS DISTINCT FROM EXCLUDED.nacional_federal
                    OR public.ncm_tributacao.importados_federal IS DISTINCT FROM EXCLUDED.importados_federal
                    OR public.ncm_tributacao.estadual IS DISTINCT FROM EXCLUDED.estadual
                    OR public.ncm_tributacao.municipal IS DISTINCT FROM EXCLUDED.municipal
                    OR public.ncm_tributacao.vigencia_inicio IS DISTINCT FROM EXCLUDED.vigencia_inicio
                    OR public.ncm_tributacao.vigencia_fim IS DISTINCT FROM EXCLUDED.vigencia_fim
                    OR public.ncm_tributacao.versao IS DISTINCT FROM EXCLUDED.versao
                    OR public.ncm_tributacao.fonte IS DISTINCT FROM EXCLUDED.fonte;
                """,
                dados,
            )

        return len(dados)

    def sincronizar(self, uf: str = "SC", todas_ufs: bool = False, ncm: str | None = None) -> list[SyncUFResultado]:
        ufs = TODAS_UFS if todas_ufs else (str(uf or "SC").strip().upper(),)
        resultados: list[SyncUFResultado] = []

        with psycopg.connect(**self.conn_params) as conn:
            self._validate_ibpt_schema(conn)

            for uf_atual in ufs:
                if uf_atual not in TODAS_UFS:
                    raise ValueError(f"UF invalida para sincronizacao IBPT: {uf_atual}")

                registros = (
                    self._buscar_ncm_especifico(ncm=ncm, uf=uf_atual)
                    if ncm
                    else self._buscar_todos_ncm_uf(uf=uf_atual)
                )

                if not registros:
                    resultados.append(
                        SyncUFResultado(
                            uf=uf_atual,
                            registros_recebidos=0,
                            catalogo_sincronizado=0,
                            tributacao_sincronizada=0,
                        )
                    )
                    continue

                catalogo_sincronizado = self._upsert_catalogo(conn, registros)
                tributacao_sincronizada = self._upsert_tributacao(conn, registros, uf_atual)
                conn.commit()

                logger.info(
                    "IBPT sincronizado para %s: %s registros, %s catalogo, %s tributacao.",
                    uf_atual,
                    len(registros),
                    catalogo_sincronizado,
                    tributacao_sincronizada,
                )

                resultados.append(
                    SyncUFResultado(
                        uf=uf_atual,
                        registros_recebidos=len(registros),
                        catalogo_sincronizado=catalogo_sincronizado,
                        tributacao_sincronizada=tributacao_sincronizada,
                    )
                )

        return resultados

    @ttl_cache(ttl_seconds=30, maxsize=256)
    def obter_tributacao(self, codigo_ncm: str, uf: str) -> dict | None:
        codigo_normalizado = self._normalizar_ncm(codigo_ncm)
        uf_normalizada = str(uf or "").strip().upper()

        if len(codigo_normalizado) != 8:
            raise ValueError("Informe um codigo NCM com 8 digitos.")

        if uf_normalizada not in TODAS_UFS:
            raise ValueError("Informe uma UF valida.")

        with psycopg.connect(**self.conn_params) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        t.ncm_codigo,
                        c.descricao,
                        t.uf,
                        t.nacional_federal,
                        t.importados_federal,
                        t.estadual,
                        t.municipal,
                        t.vigencia_inicio,
                        t.vigencia_fim,
                        t.versao,
                        t.fonte,
                        t.atualizado_em
                    FROM public.ncm_tributacao AS t
                    LEFT JOIN public.ncm_catalogo AS c
                      ON c.codigo = t.ncm_codigo
                    WHERE t.ncm_codigo = %s
                      AND t.uf = %s
                    LIMIT 1;
                    """,
                    (codigo_normalizado, uf_normalizada),
                )
                row = cur.fetchone()

        if not row:
            return None

        return {
            "ncm_codigo": row[0],
            "descricao": row[1],
            "uf": row[2],
            "nacional_federal": row[3],
            "importados_federal": row[4],
            "estadual": row[5],
            "municipal": row[6],
            "vigencia_inicio": row[7],
            "vigencia_fim": row[8],
            "versao": row[9],
            "fonte": row[10],
            "atualizado_em": row[11],
        }
