from __future__ import annotations

from fastapi import HTTPException, status

from app.services.company_profile_service import CompanyProfileService


def validar_empresa_xml(cnpj: str) -> None:
    service = CompanyProfileService()
    if service.empresa_tem_sped(cnpj) or service.empresa_tem_conta_azul(cnpj):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta empresa esta configurada para outra origem fiscal e nao para XML/NFe.",
        )


def validar_empresa_sped(cnpj: str) -> None:
    service = CompanyProfileService()
    if not service.empresa_tem_sped(cnpj) or service.empresa_tem_conta_azul(cnpj):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta empresa esta configurada para outra origem fiscal e nao para SPED Fiscal.",
        )
