import json

from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.core.http_client import ExternalServiceError, get_json

router = APIRouter(prefix="/geo", tags=["geo"])

_BASE_DIR = Path(__file__).resolve().parents[2]
_MUNICIPIOS_GEOJSON_FILE = _BASE_DIR / "services" / "Municipios" / "municipios.geojson"
_MUNICIPIOS_LL_GEOJSON_FILE = _BASE_DIR / "services" / "Municipios" / "LL-municipios.json"
_IBGE_GEOJSON_URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/estados/{uf}/municipios"
    "?formato=application/vnd.geo+json&qualidade=minima"
)

_UF_TO_IBGE_PREFIX = {
    "RO": "11",
    "AC": "12",
    "AM": "13",
    "RR": "14",
    "PA": "15",
    "AP": "16",
    "TO": "17",
    "MA": "21",
    "PI": "22",
    "CE": "23",
    "RN": "24",
    "PB": "25",
    "PE": "26",
    "AL": "27",
    "SE": "28",
    "BA": "29",
    "MG": "31",
    "ES": "32",
    "RJ": "33",
    "SP": "35",
    "PR": "41",
    "SC": "42",
    "RS": "43",
    "MS": "50",
    "MT": "51",
    "GO": "52",
    "DF": "53",
}


@lru_cache(maxsize=1)
def _load_local_municipios_geojson() -> dict | None:
    if not _MUNICIPIOS_LL_GEOJSON_FILE.exists():
        return None

    with _MUNICIPIOS_LL_GEOJSON_FILE.open("r", encoding="utf-8") as geojson_file:
        data = json.load(geojson_file)

    if data.get("type") != "FeatureCollection":
        raise HTTPException(status_code=500, detail="Arquivo LL-municipios.json inválido.")

    return data

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
    """Busca GeoJSON de municípios por UF priorizando o arquivo local LL-municipios.json."""
    uf_normalizada = (uf or "").strip().upper()
    if len(uf_normalizada) != 2 or not uf_normalizada.isalpha():
        raise HTTPException(status_code=400, detail="UF inválida. Informe a sigla com 2 letras.")
    
    geojson_local = _load_local_municipios_geojson()
    prefixo_ibge = _UF_TO_IBGE_PREFIX.get(uf_normalizada)

    if geojson_local and prefixo_ibge:
        features_filtradas = [
            feature
            for feature in geojson_local.get("features", [])
            if str((feature.get("properties") or {}).get("id", "")).startswith(prefixo_ibge)
        ]

        return JSONResponse(content={"type": "FeatureCollection", "features": features_filtradas})

    try:
        data = get_json(
            _IBGE_GEOJSON_URL.format(uf=uf_normalizada),
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/geo+json, application/json"},
            timeout_seconds=20.0,
            service_name="IBGE",
        )
    except ExternalServiceError as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao carregar GeoJSON do IBGE: {exc}") from exc

    return JSONResponse(content=data)
