from __future__ import annotations

from app.core.http_client import get_json
from app.services.Municipios.municipios_catalog_service import MunicipiosCatalogService

BRASILAPI_CNPJ_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"


def normalizar_cnpj(valor: str) -> str:
    return "".join(ch for ch in (valor or "").upper() if ch.isalnum())


class CnpjEnrichmentService:
    def consultar(self, cnpj: str) -> dict:
        cnpj_normalizado = normalizar_cnpj(cnpj)
        if len(cnpj_normalizado) != 14:
            raise ValueError("CNPJ invalido. Informe 14 caracteres.")

        payload = get_json(
            BRASILAPI_CNPJ_URL.format(cnpj=cnpj_normalizado),
            timeout_seconds=10.0,
            service_name="BrasilAPI",
        )

        cnae_fiscal = payload.get("cnae_fiscal")

        municipio_catalogo = MunicipiosCatalogService.resolver_municipio(
            uf=payload.get("uf"),
            nome=payload.get("municipio"),
        )

        return {
            "cnpj": payload.get("cnpj") or cnpj_normalizado,
            "razao_social": payload.get("razao_social"),
            "cnae_fiscal": str(cnae_fiscal) if cnae_fiscal is not None else None,
            "cnae_fiscal_descricao": payload.get("cnae_fiscal_descricao"),
            "estado": municipio_catalogo["uf"] if municipio_catalogo else None,
            "cidade": municipio_catalogo["nome"] if municipio_catalogo else None,
            "municipio_id": municipio_catalogo["municipio_id"] if municipio_catalogo else None,
            "codigo_ibge": municipio_catalogo["codigo_ibge"] if municipio_catalogo else None,
        }
