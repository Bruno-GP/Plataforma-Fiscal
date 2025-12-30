from fastapi import FastAPI

from app.api.routes import router as api_router

app = FastAPI(
    title="API - Agente Extrator NFe",
    version="0.1.0",
    description="API para processar XML de NFe e preparar dados para relatórios executivos."
)

app.include_router(api_router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok"}