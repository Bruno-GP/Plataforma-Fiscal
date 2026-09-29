from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture
def conn_params(test_database_url) -> dict:
    from urllib.parse import unquote, urlparse

    parsed = urlparse(test_database_url.replace("postgresql+psycopg://", "postgresql://", 1))
    return {
        "host": parsed.hostname,
        "port": parsed.port,
        "dbname": parsed.path[1:] if parsed.path else None,
        "user": unquote(parsed.username) if parsed.username else None,
        "password": unquote(parsed.password) if parsed.password else None,
    }


@pytest.fixture
def empresa_id(migrated_db) -> int:
    with migrated_db.cursor() as cur:
        cur.execute(
            "INSERT INTO public.empresas (cnpj, nome) VALUES (%s, %s) RETURNING id",
            ("12345678000190", "Empresa Teste Conta Azul"),
        )
        new_id = cur.fetchone()[0]
    migrated_db.commit()
    return new_id


def test_get_by_empresa_sem_integracao_retorna_none(migrated_db, conn_params, empresa_id):
    from app.repositories.conta_azul.integracoes_repository import IntegracoesRepository

    assert IntegracoesRepository(conn_params).get_by_empresa(empresa_id) is None


def test_iniciar_autorizacao_e_validar_state(migrated_db, conn_params, empresa_id):
    from app.repositories.conta_azul.integracoes_repository import IntegracoesRepository

    repo = IntegracoesRepository(conn_params)
    expira_em = datetime.now(timezone.utc) + timedelta(minutes=10)
    repo.iniciar_autorizacao(empresa_id, "state-123", expira_em)

    integracao = repo.get_by_empresa(empresa_id)
    assert integracao["status"] == "PENDENTE"
    assert integracao["oauth_state"] == "state-123"

    assert repo.validar_state(empresa_id, "state-123") is not None
    assert repo.validar_state(empresa_id, "state-errado") is None


def test_salvar_tokens_marca_ativa_e_limpa_state(migrated_db, conn_params, empresa_id):
    from app.repositories.conta_azul.integracoes_repository import IntegracoesRepository

    repo = IntegracoesRepository(conn_params)
    repo.iniciar_autorizacao(empresa_id, "state-123", datetime.now(timezone.utc) + timedelta(minutes=10))

    token_expira_em = datetime.now(timezone.utc) + timedelta(hours=1)
    repo.salvar_tokens(empresa_id, "access-cifrado", "refresh-cifrado", token_expira_em)

    integracao = repo.get_by_empresa(empresa_id)
    assert integracao["status"] == "ATIVA"
    assert integracao["access_token_encrypted"] == "access-cifrado"
    assert integracao["oauth_state"] is None


def test_marcar_desconectada_limpa_tokens(migrated_db, conn_params, empresa_id):
    from app.repositories.conta_azul.integracoes_repository import IntegracoesRepository

    repo = IntegracoesRepository(conn_params)
    repo.salvar_tokens(
        empresa_id, "access-cifrado", "refresh-cifrado", datetime.now(timezone.utc) + timedelta(hours=1)
    )

    repo.marcar_desconectada(empresa_id)

    integracao = repo.get_by_empresa(empresa_id)
    assert integracao["status"] == "DESCONECTADA"
    assert integracao["access_token_encrypted"] is None


def test_marcar_expirada_e_marcar_erro(migrated_db, conn_params, empresa_id):
    from app.repositories.conta_azul.integracoes_repository import IntegracoesRepository

    repo = IntegracoesRepository(conn_params)
    repo.iniciar_autorizacao(empresa_id, "state-123", datetime.now(timezone.utc) + timedelta(minutes=10))

    repo.marcar_expirada(empresa_id)
    assert repo.get_by_empresa(empresa_id)["status"] == "EXPIRADA"

    repo.marcar_erro(empresa_id, "Falha ao autenticar")
    integracao = repo.get_by_empresa(empresa_id)
    assert integracao["status"] == "ERRO"
    assert integracao["erro_mensagem"] == "Falha ao autenticar"
