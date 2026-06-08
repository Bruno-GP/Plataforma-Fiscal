from __future__ import annotations

from dataclasses import dataclass
import logging

import psycopg

from app.core.cache import ttl_cache
from app.core.http_client import get_json
from app.repositories.NCM.ibpt_sync_repository import IBPTSyncRepository
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
        self._ibpt_sync_repository = IBPTSyncRepository()

    def _validate_ibpt_schema(self, conn: psycopg.Connection) -> None:
        self._ibpt_sync_repository.validate_ibpt_schema(conn)

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
        return self._ibpt_sync_repository.upsert_catalogo(conn, registros)

    def _upsert_tributacao(self, conn: psycopg.Connection, registros: list[dict], uf: str) -> int:
        return self._ibpt_sync_repository.upsert_tributacao(conn, registros, uf)

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
        with psycopg.connect(**self.conn_params) as conn:
            return self._ibpt_sync_repository.obter_tributacao(conn, codigo_ncm, uf)
