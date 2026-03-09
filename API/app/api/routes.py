from fastapi import APIRouter

from app.api.auth.routes import router as auth_router
from app.api.geo.routes import router as geo_router
from app.api.nfe.routes import router as nfe_router
from app.api.sped.routes import router as sped_router

router = APIRouter()

router.include_router(nfe_router)
router.include_router(auth_router)
router.include_router(sped_router)
router.include_router(geo_router)