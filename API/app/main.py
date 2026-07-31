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
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import (
    get_cors_allow_credentials,
    get_cors_allow_origin_regex,
    get_cors_allow_origins,
    is_production,
    validate_production_config,
)
from app.core.logger import configure_logging, log_request_cycle
from app.core.security import AuthenticatedUser, get_current_user
from app.repositories.conta_azul.integracoes_repository import IntegracoesRepository
from app.services.conta_azul.postgres_token_store import PostgresTokenStore, conn_params_conta_azul

configure_logging()
validate_production_config()

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
    raise RuntimeError(
        "ENABLE_STARTUP_SCHEMA_ENSURE foi descontinuado. "
        "Aplique as migrations Alembic antes de iniciar a API."
    )


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


@app.get("/callback")
def conta_azul_oauth_callback(
    code: str,
    state: str | None = None,
    error: str | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Redirect URI fixo do Conta Azul (cadastrado no portal deles): recebe o
    'code' apos o usuario autorizar e troca por tokens, salvos por empresa em
    conta_azul.integracoes (cifrados com Fernet). Path sem prefixo /api porque o
    Conta Azul exige exatamente http://<host>/callback."""
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Autorizacao Conta Azul negada: {error}",
        )

    if not current_user.tem_conta_azul:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario nao pertence a uma empresa com Conta Azul habilitado.",
        )

    integracoes_repo = IntegracoesRepository(conn_params_conta_azul())
    if not state or not integracoes_repo.validar_state(current_user.empresa_id, state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State OAuth ausente, invalido ou expirado. Reinicie o fluxo em /api/conta-azul/oauth/iniciar.",
        )

    import sys

    conta_azul_dir = Path(__file__).resolve().parents[1] / "integracoes" / "conta_azul"
    if str(conta_azul_dir) not in sys.path:
        sys.path.insert(0, str(conta_azul_dir))

    from contaazul.auth import AuthError, ContaAzulAuth

    client_id = os.environ.get("CONTAAZUL_CLIENT_ID")
    client_secret = os.environ.get("CONTAAZUL_CLIENT_SECRET")
    redirect_uri = os.environ.get("CONTAAZUL_REDIRECT_URI")
    if not all([client_id, client_secret, redirect_uri]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credenciais Conta Azul nao configuradas (CONTAAZUL_CLIENT_ID/SECRET/REDIRECT_URI).",
        )

    auth_client = ContaAzulAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        token_store=PostgresTokenStore(current_user.empresa_id),
    )
    try:
        auth_client.exchange_code_for_token(code)
    except AuthError as exc:
        integracoes_repo.marcar_erro(current_user.empresa_id, str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"status": "ok"}
