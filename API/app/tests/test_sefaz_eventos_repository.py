from datetime import datetime, timezone

import pytest


@pytest.fixture
def documento_id(migrated_db) -> int:
    with migrated_db.cursor() as cur:
        cur.execute(
            "INSERT INTO public.empresas (cnpj, nome) VALUES (%s, %s) RETURNING id",
            ("12345678000190", "Empresa Teste SEFAZ"),
        )
        empresa_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO sefaz.documentos
                (empresa_id, chave_acesso, tipo_documento, direcao, cnpj_emitente, nsu)
            VALUES (%s, %s, 'resNFe', 'recebida', '98765432000199', '000000000000001')
            RETURNING id
            """,
            (empresa_id, "6666666666666666666666666666666666666666"),
        )
        new_id = cur.fetchone()[0]
    migrated_db.commit()
    return new_id


def test_inserir_e_listar_por_documento(migrated_db, documento_id):
    from app.repositories.sefaz.eventos_repository import EventosRepository

    repo = EventosRepository()
    with migrated_db.cursor() as cur:
        cur.execute("SELECT empresa_id FROM sefaz.documentos WHERE id = %s", (documento_id,))
        empresa_id = cur.fetchone()[0]

    repo.inserir(
        documento_id=documento_id,
        empresa_id=empresa_id,
        tipo_evento="manifestacao_ciencia",
        protocolo="135260000000009",
        status="recebido",
        payload_xml="<evento/>",
    )

    eventos = repo.listar_por_documento(documento_id)
    assert len(eventos) == 1
    assert eventos[0]["tipo_evento"] == "manifestacao_ciencia"
    assert eventos[0]["protocolo"] == "135260000000009"

