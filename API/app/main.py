from dotenv import load_dotenv
from pathlib import Path

import os

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router

app = FastAPI(
    title="API - Agente Extrator NFe",
    version="0.1.0",
    description="API para processar XML de NFe e preparar dados para relatórios executivos."
)

cors_origins_env = os.getenv("CORS_ALLOW_ORIGINS", "*")
cors_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
allow_all_origins = cors_origins == ["*"]

cors_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
if allow_all_origins and cors_allow_credentials:
    cors_allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins else ["*"],
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok"}