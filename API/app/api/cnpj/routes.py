from functools import lru_cache

from fastapi import APIRouter, HTTPException, status

from app.core.http_client import ExternalServiceError
from app.models.cnpj.schemas import CnpjEnriquecimentoResponse
from app.services.cnpj.cnpj_enrichment_service import CnpjEnrichmentService

router = APIRouter(prefix="/cnpj", tags=["cnpj"])


@lru_cache(maxsize=1)
def get_cnpj_enrichment_service() -> CnpjEnrichmentService:
    return CnpjEnrichmentService()


@router.get("/{cnpj}/enriquecer", response_model=CnpjEnriquecimentoResponse)
def enriquecer_cnpj(cnpj: str):
    try:
        dados = get_cnpj_enrichment_service().consultar(cnpj)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ExternalServiceError as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="CNPJ nao encontrado.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao consultar dados do CNPJ.",
        ) from exc

    return CnpjEnriquecimentoResponse(status="ok", **dados)
