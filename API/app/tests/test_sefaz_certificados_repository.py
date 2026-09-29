from datetime import date, timedelta

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


def test_get_ativo_sem_certificado_retorna_none(migrated_db, empresa_id):
    from app.repositories.sefaz.certificados_repository import CertificadosRepository

    assert CertificadosRepository().get_ativo(empresa_id) is None


def test_inserir_certificado_fica_ativo(migrated_db, empresa_id):
    from app.repositories.sefaz.certificados_repository import CertificadosRepository

    repo = CertificadosRepository()
    validade = date.today() + timedelta(days=365)
    repo.inserir(
        empresa_id=empresa_id,
        arquivo_certificado=b"conteudo-cifrado",
        senha_criptografada="senha-cifrada",
        cnpj_titular="12345678000190",
        data_validade=validade,
    )

    ativo = repo.get_ativo(empresa_id)
    assert ativo["cnpj_titular"] == "12345678000190"
    assert ativo["ativo"] is True
    assert ativo["data_validade"] == validade


def test_inserir_novo_certificado_desativa_o_anterior(migrated_db, empresa_id):
    from app.repositories.sefaz.certificados_repository import CertificadosRepository

    repo = CertificadosRepository()
    validade = date.today() + timedelta(days=365)
    primeiro_id = repo.inserir(
        empresa_id=empresa_id,
        arquivo_certificado=b"primeiro",
        senha_criptografada="senha-1",
        cnpj_titular="12345678000190",
        data_validade=validade,
    )
    repo.inserir(
        empresa_id=empresa_id,
        arquivo_certificado=b"segundo",
        senha_criptografada="senha-2",
        cnpj_titular="12345678000190",
        data_validade=validade,
    )

    ativo = repo.get_ativo(empresa_id)
    assert ativo["arquivo_certificado"].tobytes() == b"segundo"

    with migrated_db.cursor() as cur:
        cur.execute("SELECT ativo FROM sefaz.certificados WHERE id = %s", (primeiro_id,))
        assert cur.fetchone()[0] is False


def test_listar_ativos_com_validade(migrated_db, empresa_id):
    from app.repositories.sefaz.certificados_repository import CertificadosRepository

    repo = CertificadosRepository()
    validade = date.today() + timedelta(days=30)
    repo.inserir(
        empresa_id=empresa_id,
        arquivo_certificado=b"conteudo",
        senha_criptografada="senha",
        cnpj_titular="12345678000190",
        data_validade=validade,
    )

    ativos = repo.listar_ativos_com_validade()
    assert len(ativos) == 1
    assert ativos[0]["empresa_id"] == empresa_id
    assert ativos[0]["cnpj_titular"] == "12345678000190"
    assert ativos[0]["data_validade"] == validade

