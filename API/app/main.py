from dotenv import load_dotenv
from pathlib import Path

import os

# Carrega variáveis de ambiente locais para desenvolvimento e execução via scripts.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.logger import configure_logging, log_request_cycle

# Instância principal da API (metadados aparecem no /docs automaticamente).
configure_logging()

app = FastAPI(
    title="API - Agente Extrator NFe",
    version="0.1.0",
    description="API para processar XML de NFe e preparar dados para relatórios executivos."
)

# Configuração de CORS por ENV para permitir múltiplos ambientes (local/homolog/prod).
def _normalizar_origem(origin: str) -> str:
    """Normaliza origem removendo aspas e barra final para evitar mismatch no preflight."""
    return origin.strip().strip('"\'').rstrip("/")


def _expandir_aliases_locais(origens: list[str]) -> list[str]:
    """Expande localhost/127.0.0.1 para reduzir falhas comuns de CORS no desenvolvimento."""
    expandidas: set[str] = set()
    for origem in origens:
        expandidas.add(origem)
        if "localhost" in origem:
            expandidas.add(origem.replace("localhost", "127.0.0.1"))
        if "127.0.0.1" in origem:
            expandidas.add(origem.replace("127.0.0.1", "localhost"))
    return sorted(expandidas)


cors_origins_env = os.getenv("CORS_ALLOW_ORIGINS", "*")
cors_origin_regex_env = os.getenv("CORS_ALLOW_ORIGIN_REGEX", "").strip()

cors_origins = [
    _normalizar_origem(origin)
    for origin in cors_origins_env.split(",")
    if _normalizar_origem(origin)
]

allow_all_origins = "*" in cors_origins
if not allow_all_origins:
    cors_origins = _expandir_aliases_locais(cors_origins)
    
# Regex padrão para ambiente local: evita 400 no preflight quando a porta do front muda.
# Pode ser sobrescrito por CORS_ALLOW_ORIGIN_REGEX.
default_local_origin_regex = r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"
cors_origin_regex = (
    cors_origin_regex_env
    or (default_local_origin_regex if not allow_all_origins else None)
)

cors_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
if allow_all_origins and cors_allow_credentials:
    cors_allow_credentials = False

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

@app.get("/health")
def health_check():
    """Endpoint simples de observabilidade para monitoramento."""
    return {"status": "ok"}
