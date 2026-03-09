import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter(prefix="/geo", tags=["geo"])

_BASE_DIR = Path(__file__).resolve().parents[2]
_MUNICIPIOS_GEOJSON_FILE = _BASE_DIR / "services" / "Municipios" / "municipios.geojson"
_IBGE_GEOJSON_URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/estados/{uf}/municipios"
    "?formato=application/vnd.geo+json&qualidade=minima"
)

@router.get("/municipios")
def obter_geojson_municipios() -> FileResponse:
    """Serve um GeoJSON local de municípios, quando disponível."""
    if not _MUNICIPIOS_GEOJSON_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Arquivo de GeoJSON de municípios não encontrado no servidor.",
        )

    return FileResponse(
        _MUNICIPIOS_GEOJSON_FILE,
        media_type="application/geo+json",
        filename="municipios.geojson",
    )

@router.get("/municipios/{uf}")
def obter_geojson_municipios_por_uf(uf: str) -> JSONResponse:
    """Busca GeoJSON de municípios por UF via backend para reduzir bloqueios no navegador."""
    uf_normalizada = (uf or "").strip().upper()
    if len(uf_normalizada) != 2 or not uf_normalizada.isalpha():
        raise HTTPException(status_code=400, detail="UF inválida. Informe a sigla com 2 letras.")

    url = _IBGE_GEOJSON_URL.format(uf=uf_normalizada)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/geo+json, application/json"})

    try:
        with urlopen(req, timeout=20) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao carregar GeoJSON do IBGE (HTTP {exc.code}).") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail="Falha de conexão ao carregar GeoJSON do IBGE.") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Resposta inválida ao carregar GeoJSON do IBGE.") from exc

    return JSONResponse(content=data)