from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture
def empresa_id(migrated_db) -> int:
    with migrated_db.cursor() as cur:
        cur.execute(
            "INSERT INTO public.empresas (cnpj, nome) VALUES (%s, %s) RETURNING id",
            ("12345678000190", "Empresa Teste SEFAZ"),
        )
        new_id = cur.fetchone()[0]
    migrated_db.commit()
    return new_id


def test_registrar_e_listar(migrated_db, empresa_id):
    from app.repositories.sefaz.sync_log_repository import SyncLogRepository

    repo = SyncLogRepository()
    inicio = datetime.now(timezone.utc)
    repo.registrar(
        empresa_id=empresa_id,
        iniciado_em=inicio,
        finalizado_em=inicio + timedelta(seconds=5),
        documentos_novos=3,
        nsu_inicial="000000000000000",
        nsu_final="000000000000050",
        status="sucesso",
        erro_detalhe=None,
    )

    total, rows = repo.listar(empresa_id, limit=10, offset=0)
    assert total == 1
    assert rows[0]["status"] == "sucesso"
    assert rows[0]["documentos_novos"] == 3


def test_listar_ordena_mais_recente_primeiro(migrated_db, empresa_id):
    from app.repositories.sefaz.sync_log_repository import SyncLogRepository

    repo = SyncLogRepository()
    base = datetime.now(timezone.utc)
    repo.registrar(
        empresa_id=empresa_id,
        iniciado_em=base - timedelta(days=1),
        finalizado_em=base - timedelta(days=1),
        documentos_novos=1,
        nsu_inicial="0",
        nsu_final="1",
        status="sucesso",
        erro_detalhe=None,
    )
    repo.registrar(
        empresa_id=empresa_id,
        iniciado_em=base,
        finalizado_em=base,
        documentos_novos=2,
        nsu_inicial="1",
        nsu_final="2",
        status="sucesso",
        erro_detalhe=None,
    )

    _, rows = repo.listar(empresa_id, limit=10, offset=0)
    assert rows[0]["documentos_novos"] == 2
    assert rows[1]["documentos_novos"] == 1


def test_obter_ultimo_sucesso_com_documentos_ignora_erro_e_zero_documentos(migrated_db, empresa_id):
    from app.repositories.sefaz.sync_log_repository import SyncLogRepository

    repo = SyncLogRepository()
    base = datetime.now(timezone.utc)
    repo.registrar(
        empresa_id=empresa_id,
        iniciado_em=base - timedelta(hours=3),
        finalizado_em=base - timedelta(hours=3),
        documentos_novos=2,
        nsu_inicial="0",
        nsu_final="2",
        status="sucesso",
        erro_detalhe=None,
    )
    repo.registrar(
        empresa_id=empresa_id,
        iniciado_em=base - timedelta(hours=2),
        finalizado_em=base - timedelta(hours=2),
        documentos_novos=0,
        nsu_inicial="2",
        nsu_final="2",
        status="sucesso",
        erro_detalhe=None,
    )
    repo.registrar(
        empresa_id=empresa_id,
        iniciado_em=base - timedelta(hours=1),
        finalizado_em=base - timedelta(hours=1),
        documentos_novos=5,
        nsu_inicial="2",
        nsu_final="7",
        status="erro",
        erro_detalhe="Falha SEFAZ",
    )

    row = repo.obter_ultimo_sucesso_com_documentos(empresa_id)

    assert row is not None
    assert row["documentos_novos"] == 2
    assert row["status"] == "sucesso"
