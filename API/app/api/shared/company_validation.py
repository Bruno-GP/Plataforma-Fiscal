from __future__ import annotations

from fastapi import HTTPException, status

from app.services.company_profile_service import CompanyProfileService


def validar_empresa_xml(cnpj: str) -> None:
    if CompanyProfileService().empresa_tem_sped(cnpj):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta empresa esta configurada para SPED Fiscal e nao para XML.",
        )


def validar_empresa_sped(cnpj: str) -> None:
    if not CompanyProfileService().empresa_tem_sped(cnpj):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta empresa esta configurada para XML e nao para SPED Fiscal.",
        )
