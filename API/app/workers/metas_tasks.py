from __future__ import annotations

import logging

from app.repositories.metas.empresas_repository import MetasEmpresasRepository
from app.services.metas.metas_historico_service import MetasHistoricoService
from app.workers.celery_app import celery_app


logger = logging.getLogger(__name__)


def _repositorio_empresas() -> MetasEmpresasRepository:
    return MetasEmpresasRepository()


def _materializar_empresa(empresa_id: int, cnpj: str) -> int:
    return MetasHistoricoService().materializar_empresa(empresa_id, cnpj)


@celery_app.task(name="materializar_indicadores_historico_task")
def materializar_indicadores_historico_task() -> dict:
    empresas = _repositorio_empresas().listar_empresas_xml_ativas()
    resultado = {"empresas_processadas": 0, "empresas_falha": 0, "linhas_gravadas": 0}

    for empresa_id, cnpj in empresas:
        try:
            linhas_gravadas = _materializar_empresa(empresa_id, cnpj)
            resultado["empresas_processadas"] += 1
            resultado["linhas_gravadas"] += linhas_gravadas
        except Exception:
            resultado["empresas_falha"] += 1
            logger.exception(
                "metas_historico_materializacao_falhou",
                extra={"empresa_id": empresa_id, "cnpj": cnpj},
            )

    resultado["status"] = "SUCCESS"
    return resultado
