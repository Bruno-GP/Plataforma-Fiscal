from __future__ import annotations

import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

_CONTA_AZUL_DIR = Path(__file__).resolve().parents[2] / "integracoes" / "conta_azul"
if str(_CONTA_AZUL_DIR) not in sys.path:
    sys.path.insert(0, str(_CONTA_AZUL_DIR))

from contaazul.auth import AuthError, ContaAzulAuth  # noqa: E402
from contaazul.client import ApiError, ContaAzulClient, DEFAULT_PAGE_SIZE  # noqa: E402
from contaazul.db import conectar  # noqa: E402
from contaazul.kpis import agregar_kpis_mensais  # noqa: E402
from exporters.postgres_kpis_exporter import PostgresKpisExporter  # noqa: E402

from app.repositories.conta_azul.conta_azul_repository import ContaAzulRepository
from app.repositories.conta_azul.integracoes_repository import IntegracoesRepository
from app.services.conta_azul.postgres_config import carregar_config_postgres_conta_azul
from app.services.conta_azul.postgres_token_store import PostgresTokenStore, conn_params_conta_azul
from app.workers.celery_app import celery_app

logger = logging.getLogger("workers.conta_azul")


def _repositorio_empresas() -> ContaAzulRepository:
    config = carregar_config_postgres_conta_azul()
    conn_params = {
        "host": config["host"],
        "port": config["port"],
        "dbname": config["database"],
        "user": config["user"],
        "password": config["password"],
        "connect_timeout": 5,
        **({"sslmode": config["sslmode"]} if config.get("sslmode") else {}),
    }
    return ContaAzulRepository(conn_params)


def _repositorio_integracoes() -> IntegracoesRepository:
    return IntegracoesRepository(conn_params_conta_azul())


def _periodo_sincronizacao() -> tuple[date, date]:
    hoje = date.today()
    primeiro_dia_mes_atual = hoje.replace(day=1)
    mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
    inicio = mes_anterior.replace(day=1)
    return inicio, hoje


def _coletar_todas_paginas(client: ContaAzulClient, inicio: date, fim: date) -> list:
    todos = []
    pagina = 1
    while True:
        pagina_atual = client.listar_vendas(inicio, fim, pagina)
        todos.extend(pagina_atual)
        if len(pagina_atual) < DEFAULT_PAGE_SIZE:
            break
        pagina += 1
    return todos


def _sincronizar_empresa(empresa_id: int, inicio: date, fim: date) -> int:
    auth_client = ContaAzulAuth(
        client_id=os.environ.get("CONTAAZUL_CLIENT_ID"),
        client_secret=os.environ.get("CONTAAZUL_CLIENT_SECRET"),
        redirect_uri=os.environ.get("CONTAAZUL_REDIRECT_URI"),
        token_store=PostgresTokenStore(empresa_id),
    )
    client = ContaAzulClient(auth_client)
    try:
        vendas = _coletar_todas_paginas(client, inicio, fim)
    finally:
        client.close()

    kpis_por_mes = agregar_kpis_mensais(vendas)

    conn = conectar()
    try:
        return PostgresKpisExporter().export(empresa_id, kpis_por_mes, conn)
    finally:
        conn.close()


@celery_app.task(name="sincronizar_kpis_conta_azul_task")
def sincronizar_kpis_conta_azul_task() -> dict:
    """Roda diariamente (via beat_schedule em celery_app.py): busca vendas dos
    ultimos ~2 meses de cada empresa com integracao Conta Azul ATIVA (token por
    empresa em conta_azul.integracoes, ver app/repositories/conta_azul) e faz
    upsert dos KPIs mensais em conta_azul_kpis. Empresas com tem_conta_azul=true
    mas sem OAuth2 concluido (ou expirado) sao puladas, nao contam como falha.
    """
    client_id = os.environ.get("CONTAAZUL_CLIENT_ID")
    client_secret = os.environ.get("CONTAAZUL_CLIENT_SECRET")
    redirect_uri = os.environ.get("CONTAAZUL_REDIRECT_URI")
    if not all([client_id, client_secret, redirect_uri]):
        logger.error("conta_azul_credenciais_ausentes: faltam CONTAAZUL_CLIENT_ID/SECRET/REDIRECT_URI no ambiente")
        return {"status": "FAILED", "erro": "credenciais ausentes"}

    inicio, fim = _periodo_sincronizacao()

    empresas = _repositorio_empresas().listar_empresas_ativas()
    integracoes_repo = _repositorio_integracoes()
    resultado = {"empresas_ok": 0, "empresas_falha": 0, "empresas_puladas": 0}

    for empresa_id, cnpj in empresas:
        integracao = integracoes_repo.get_by_empresa(empresa_id)
        if not integracao or integracao["status"] != "ATIVA":
            resultado["empresas_puladas"] += 1
            logger.info(
                "conta_azul_empresa_sem_integracao_ativa",
                extra={"empresa_id": empresa_id, "cnpj": cnpj},
            )
            continue

        try:
            meses_gravados = _sincronizar_empresa(empresa_id, inicio, fim)
            resultado["empresas_ok"] += 1
            logger.info(
                "conta_azul_kpis_sincronizados",
                extra={"empresa_id": empresa_id, "cnpj": cnpj, "meses_gravados": meses_gravados},
            )
        except (AuthError, ApiError) as exc:
            resultado["empresas_falha"] += 1
            logger.warning(
                "conta_azul_sync_falhou",
                extra={"empresa_id": empresa_id, "cnpj": cnpj, "erro": str(exc)},
            )
        except Exception:
            resultado["empresas_falha"] += 1
            logger.exception("conta_azul_sync_erro_inesperado", extra={"empresa_id": empresa_id, "cnpj": cnpj})

    return {"status": "SUCCESS", **resultado}
