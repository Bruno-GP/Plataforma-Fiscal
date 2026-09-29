from fastapi import APIRouter

from app.api.municipios.routes import router as municipios_router
from app.api.auth.routes import router as auth_router
from app.api.cnpj.routes import router as cnpj_router
from app.api.metas.routes import router as metas_router
from app.api.metas.indicadores_routes import router as indicadores_router
from app.api.conta_azul.routes import router as conta_azul_router
from app.api.empresas.recomendacoes_routes import router as empresas_recomendacoes_router
from app.api.geo.routes import router as geo_router
from app.api.jobs.routes import router as jobs_router
from app.api.ncm.routes import router as ncm_router
from app.api.nfe.routes import router as nfe_router
from app.api.sefaz.routes import router as sefaz_router
from app.api.reforma_tributaria.routes import router as reforma_tributaria_router
from app.api.sped.routes import router as sped_router

router = APIRouter()

router.include_router(nfe_router)
router.include_router(jobs_router)
router.include_router(auth_router)
router.include_router(cnpj_router)
router.include_router(municipios_router)
router.include_router(empresas_recomendacoes_router)
router.include_router(metas_router)
router.include_router(indicadores_router)
router.include_router(sped_router)
router.include_router(conta_azul_router)
router.include_router(geo_router)
router.include_router(ncm_router)
router.include_router(reforma_tributaria_router)
router.include_router(sefaz_router)
