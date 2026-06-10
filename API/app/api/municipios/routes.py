from fastapi import APIRouter, Query

from app.models.municipios.schemas import MunicipioCatalogoItem, UFCatalogoItem
from app.services.Municipios.municipios_catalog_service import MunicipiosCatalogService

router = APIRouter(prefix="/municipios", tags=["municipios"])


@router.get("/ufs", response_model=list[UFCatalogoItem])
def listar_ufs(busca: str | None = Query(default=None, max_length=50)):
    return MunicipiosCatalogService.listar_ufs(busca=busca)


@router.get("/cidades", response_model=list[MunicipioCatalogoItem])
def listar_cidades(
    uf: str | None = Query(default=None, max_length=2),
    busca: str | None = Query(default=None, max_length=100),
):
    return MunicipiosCatalogService.listar_municipios_por_uf(uf=uf, busca=busca)
