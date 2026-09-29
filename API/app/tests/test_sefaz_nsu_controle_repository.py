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


def test_obter_sem_registro_retorna_none(migrated_db, empresa_id):
    from app.repositories.sefaz.nsu_controle_repository import NsuControleRepository

    assert NsuControleRepository().obter(empresa_id, ambiente=1) is None


def test_upsert_execucao_cria_e_atualiza(migrated_db, empresa_id):
    from app.repositories.sefaz.nsu_controle_repository import NsuControleRepository

    repo = NsuControleRepository()
    repo.upsert_execucao(
        empresa_id,
        ambiente=1,
        ultimo_nsu="000000000000010",
        status_ultima_execucao="sucesso",
    )

    cursor = repo.obter(empresa_id, ambiente=1)
    assert cursor["ultimo_nsu"] == "000000000000010"
    assert cursor["status_ultima_execucao"] == "sucesso"

    repo.upsert_execucao(
        empresa_id,
        ambiente=1,
        ultimo_nsu="000000000000025",
        status_ultima_execucao="sucesso",
    )
    cursor = repo.obter(empresa_id, ambiente=1)
    assert cursor["ultimo_nsu"] == "000000000000025"


def test_ambientes_diferentes_tem_cursores_independentes(migrated_db, empresa_id):
    from app.repositories.sefaz.nsu_controle_repository import NsuControleRepository

    repo = NsuControleRepository()
    repo.upsert_execucao(
        empresa_id,
        ambiente=1,
        ultimo_nsu="000000000000001",
        status_ultima_execucao="sucesso",
    )
    repo.upsert_execucao(
        empresa_id,
        ambiente=2,
        ultimo_nsu="000000000000099",
        status_ultima_execucao="sucesso",
    )

    assert repo.obter(empresa_id, ambiente=1)["ultimo_nsu"] == "000000000000001"
    assert repo.obter(empresa_id, ambiente=2)["ultimo_nsu"] == "000000000000099"

