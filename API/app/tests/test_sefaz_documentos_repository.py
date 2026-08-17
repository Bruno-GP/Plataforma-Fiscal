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


def _inserir_documento(repo, empresa_id, chave_acesso="3526081234567800019055001000000001", **overrides):
    dados = {
        "empresa_id": empresa_id,
        "chave_acesso": chave_acesso,
        "tipo_documento": "resNFe",
        "direcao": "recebida",
        "cnpj_emitente": "98765432000199",
        "cnpj_destinatario": "12345678000190",
        "nsu": "000000000000001",
        "data_emissao": datetime.now(timezone.utc),
        "valor_total": "1234.56",
        "situacao": "autorizada",
        "xml_armazenado": None,
        "manifestacao_status": "pendente",
    }
    dados.update(overrides)
    return repo.inserir_se_novo(**dados)


def test_inserir_se_novo_primeira_vez_retorna_true(migrated_db, empresa_id):
    from app.repositories.sefaz.documentos_repository import DocumentosRepository

    repo = DocumentosRepository()
    assert _inserir_documento(repo, empresa_id) is True


def test_inserir_se_novo_repetido_e_idempotente(migrated_db, empresa_id):
    from app.repositories.sefaz.documentos_repository import DocumentosRepository

    repo = DocumentosRepository()
    assert _inserir_documento(repo, empresa_id) is True
    assert _inserir_documento(repo, empresa_id) is False

    total, _ = repo.listar(empresa_id=empresa_id)
    assert total == 1


def test_obter_por_chave_e_por_id(migrated_db, empresa_id):
    from app.repositories.sefaz.documentos_repository import DocumentosRepository

    repo = DocumentosRepository()
    _inserir_documento(repo, empresa_id, chave_acesso="1111111111111111111111111111111111111111")

    por_chave = repo.obter_por_chave(empresa_id, "1111111111111111111111111111111111111111")
    assert por_chave is not None

    por_id = repo.obter_por_id(empresa_id, por_chave["id"])
    assert por_id["chave_acesso"] == "1111111111111111111111111111111111111111"

    assert repo.obter_por_id(empresa_id, por_chave["id"] + 999) is None


def test_atualizar_manifestacao(migrated_db, empresa_id):
    from app.repositories.sefaz.documentos_repository import DocumentosRepository

    repo = DocumentosRepository()
    _inserir_documento(repo, empresa_id, chave_acesso="2222222222222222222222222222222222222222")
    documento = repo.obter_por_chave(empresa_id, "2222222222222222222222222222222222222222")

    repo.atualizar_manifestacao(documento["id"], "ciencia")

    atualizado = repo.obter_por_id(empresa_id, documento["id"])
    assert atualizado["manifestacao_status"] == "ciencia"


def test_listar_filtra_por_direcao_situacao_e_manifestacao_pendente(migrated_db, empresa_id):
    from app.repositories.sefaz.documentos_repository import DocumentosRepository

    repo = DocumentosRepository()
    _inserir_documento(
        repo,
        empresa_id,
        chave_acesso="3333333333333333333333333333333333333333",
        direcao="recebida",
        manifestacao_status="pendente",
    )
    _inserir_documento(
        repo,
        empresa_id,
        chave_acesso="4444444444444444444444444444444444444444",
        direcao="emitida",
        manifestacao_status=None,
    )

    total, rows = repo.listar(empresa_id=empresa_id, direcao="recebida")
    assert total == 1
    assert rows[0]["chave_acesso"] == "3333333333333333333333333333333333333333"

    total, rows = repo.listar(empresa_id=empresa_id, manifestacao_pendente=True)
    assert total == 1
    assert rows[0]["manifestacao_status"] == "pendente"


def test_listar_pagina_com_limit_e_offset(migrated_db, empresa_id):
    from app.repositories.sefaz.documentos_repository import DocumentosRepository

    repo = DocumentosRepository()
    for indice in range(3):
        _inserir_documento(
            repo,
            empresa_id,
            chave_acesso=f"555555555555555555555555555555555555555{indice}",
        )

    total, pagina_1 = repo.listar(empresa_id=empresa_id, limit=2, offset=0)
    total_2, pagina_2 = repo.listar(empresa_id=empresa_id, limit=2, offset=2)

    assert total == 3
    assert total_2 == 3
    assert len(pagina_1) == 2
    assert len(pagina_2) == 1

