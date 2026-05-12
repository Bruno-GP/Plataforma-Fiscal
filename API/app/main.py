try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - ambiente minimo sem python-dotenv instalado
    def load_dotenv(*args, **kwargs):
        return False
from pathlib import Path

# Carrega variáveis de ambiente locais para desenvolvimento e execução via scripts.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

import os

import psycopg
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import (
    get_cors_allow_credentials,
    get_cors_allow_origin_regex,
    get_cors_allow_origins,
    is_production,
)
from app.core.logger import configure_logging, log_request_cycle
from app.services.db_schema_service import (
    ensure_empresas_tem_sped_column,
    ensure_fiscal_analysis_indexes,
    ensure_municipios_catalogo_table,
    ensure_ncm_ibpt_tables,
    ensure_reforma_tributaria_base_schema,
    ensure_reforma_tributaria_creditos_debitos_memoria_schema,
    ensure_reforma_tributaria_documentos_itens_schema,
)

configure_logging()

app = FastAPI(
    title="API - Agente Extrator NFe",
    version="0.1.0",
    description="API para processar XML de NFe e preparar dados para relatórios executivos.",
)


def _normalizar_origem(origin: str) -> str:
    return origin.strip().strip('"\'').rstrip("/")


def _expandir_aliases_locais(origens: list[str]) -> list[str]:
    expandidas: set[str] = set()
    for origem in origens:
        expandidas.add(origem)
        if "localhost" in origem:
            expandidas.add(origem.replace("localhost", "127.0.0.1"))
        if "127.0.0.1" in origem:
            expandidas.add(origem.replace("127.0.0.1", "localhost"))
    return sorted(expandidas)


cors_origins_env = get_cors_allow_origins()
cors_origin_regex = get_cors_allow_origin_regex() or None

cors_origins = [
    _normalizar_origem(origin)
    for origin in cors_origins_env.split(",")
    if _normalizar_origem(origin)
]

allow_all_origins = "*" in cors_origins
if not allow_all_origins:
    cors_origins = _expandir_aliases_locais(cors_origins)

cors_allow_credentials = get_cors_allow_credentials()
if allow_all_origins and cors_allow_credentials:
    cors_allow_credentials = False

if is_production() and not cors_origins and not cors_origin_regex:
    raise RuntimeError("Defina CORS_ALLOW_ORIGINS ou CORS_ALLOW_ORIGIN_REGEX para produção.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins else ["*"],
    allow_origin_regex=cors_origin_regex,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(log_request_cycle)
app.include_router(api_router, prefix="/api")


@app.on_event("startup")
def ensure_database_schema() -> None:
    if os.getenv("ENABLE_STARTUP_SCHEMA_ENSURE", "false").strip().lower() not in {"1", "true", "yes"}:
        return
    ensure_empresas_tem_sped_column()
    ensure_ncm_ibpt_tables()
    ensure_municipios_catalogo_table()
    ensure_reforma_tributaria_base_schema()
    ensure_reforma_tributaria_documentos_itens_schema()
    ensure_reforma_tributaria_creditos_debitos_memoria_schema()
    ensure_fiscal_analysis_indexes()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def health_check_db():
    from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres

    config = carregar_config_postgres()
    last_error: Exception | None = None
    for options in opcoes_conexao_postgres(config):
        try:
            with psycopg.connect(**options) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return {"status": "ok"}
        except psycopg.Error as exc:
            last_error = exc

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="PostgreSQL indisponivel.",
    ) from last_error


@app.get("/health/redis")
def health_check_redis():
    import redis

    try:
        client = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            socket_connect_timeout=2,
        )
        client.ping()
    except redis.RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis indisponivel.",
        ) from exc

    return {"status": "ok"}
