from decimal import Decimal
from pathlib import Path

import pytest


APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parents[1]
MIGRATIONS_DIR = REPO_ROOT / "API" / "SQL" / "migrations"
ALEMBIC_DIR = APP_DIR / "alembic" / "versions"


def fetch_one(conn, query, params=None):
    with conn.cursor() as cur:
        cur.execute(query, params or ())
        return cur.fetchone()


def fetch_all(conn, query, params=None):
    with conn.cursor() as cur:
        cur.execute(query, params or ())
        return cur.fetchall()


def assert_insert_rejected(conn, query, params=None):
    with pytest.raises(Exception):
        with conn.transaction():
            conn.execute(query, params or ())


def test_alembic_revisions_and_sql_migrations_cover_expected_database_objects():
    initial_schema = (ALEMBIC_DIR / "20260505_0001_initial_schema.py").read_text(
        encoding="utf-8"
    )
    reforma_base = (MIGRATIONS_DIR / "004_add_reforma_tributaria_base.sql").read_text(
        encoding="utf-8"
    )
    reforma_documentos = (
        MIGRATIONS_DIR / "005_add_reforma_tributaria_documentos_itens.sql"
    ).read_text(encoding="utf-8")
    reforma_memoria = (
        MIGRATIONS_DIR / "006_add_reforma_tributaria_creditos_debitos_memoria.sql"
    ).read_text(encoding="utf-8")
    login_security = (
        ALEMBIC_DIR / "20260515_0004_login_security_columns.py"
    ).read_text(encoding="utf-8")

    for expected in [
        "CREATE TABLE IF NOT EXISTS empresas",
        "CREATE TABLE IF NOT EXISTS notas",
        "CREATE TABLE IF NOT EXISTS notas_itens",
        "CREATE TABLE IF NOT EXISTS notas_xml_importados",
        "CREATE TABLE IF NOT EXISTS sped_importados",
        "CREATE TABLE IF NOT EXISTS processing_jobs",
        "CONSTRAINT ck_processing_jobs_status",
    ]:
        assert expected in initial_schema

    for expected in [
        "CREATE TABLE IF NOT EXISTS public.tributos",
        "CREATE TABLE IF NOT EXISTS public.apuracao_tributaria",
        "CONSTRAINT ck_apuracao_tributaria_status",
    ]:
        assert expected in reforma_base

    for expected in [
        "CREATE TABLE IF NOT EXISTS public.documentos_fiscais_tributos",
        "CREATE TABLE IF NOT EXISTS public.itens_documentos_fiscais_tributos",
        "CONSTRAINT ck_documentos_fiscais_tributos_status",
    ]:
        assert expected in reforma_documentos

    for expected in [
        "CREATE TABLE IF NOT EXISTS public.creditos_tributarios",
        "CREATE TABLE IF NOT EXISTS public.debitos_tributarios",
        "CREATE TABLE IF NOT EXISTS public.memoria_calculo_tributaria",
        "CONSTRAINT ck_creditos_tributarios_valores",
        "CONSTRAINT ck_debitos_tributarios_valores",
    ]:
        assert expected in reforma_memoria

    for expected in [
        "ADD COLUMN IF NOT EXISTS tentativas_falhas",
        "ADD COLUMN IF NOT EXISTS bloqueado_ate",
        "ADD COLUMN IF NOT EXISTS ultimo_login_em",
    ]:
        assert expected in login_security


def test_staging_import_services_do_not_mutate_database_schema():
    xml_import_service = (
        APP_DIR / "services" / "nfe" / "xml_importacao_service.py"
    ).read_text(encoding="utf-8")
    sped_import_service = (
        APP_DIR / "services" / "sped" / "sped_importacao_service.py"
    ).read_text(encoding="utf-8")

    forbidden_fragments = [
        "CREATE TABLE IF NOT EXISTS notas_xml_importados",
        "ALTER TABLE notas_xml_importados",
        "CREATE TABLE IF NOT EXISTS sped_importados",
        "ALTER TABLE sped_importados",
    ]

    service_source = f"{xml_import_service}\n{sped_import_service}"
    for fragment in forbidden_fragments:
        assert fragment not in service_source


def test_jobs_repository_does_not_mutate_database_schema():
    jobs_repository = (
        APP_DIR / "repositories" / "jobs_repository.py"
    ).read_text(encoding="utf-8")

    forbidden_fragments = [
        "CREATE TABLE IF NOT EXISTS processing_jobs",
        "CREATE INDEX IF NOT EXISTS idx_processing_jobs",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in jobs_repository


def test_login_service_does_not_mutate_database_schema():
    login_service = (
        APP_DIR / "services" / "nfe" / "auth" / "login_service.py"
    ).read_text(encoding="utf-8")

    forbidden_fragments = [
        "ALTER TABLE public.login",
        "ADD COLUMN IF NOT EXISTS tentativas_falhas",
        "ADD COLUMN IF NOT EXISTS bloqueado_ate",
        "ADD COLUMN IF NOT EXISTS ultimo_login_em",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in login_service


def test_migrations_run_to_head_in_clean_test_database(migrated_db):
    revision = fetch_one(migrated_db, "SELECT version_num FROM alembic_version;")[0]

    assert revision == "20260515_0004"


def test_core_tables_columns_primary_keys_and_foreign_keys(migrated_db):
    expected_tables = {
        "empresas",
        "login",
        "notas_processamentos",
        "notas",
        "notas_itens",
        "processing_jobs",
        "tributos",
        "apuracao_tributaria",
        "documentos_fiscais_tributos",
        "itens_documentos_fiscais_tributos",
        "creditos_tributarios",
        "debitos_tributarios",
        "memoria_calculo_tributaria",
    }

    tables = {
        row[0]
        for row in fetch_all(
            migrated_db,
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """,
        )
    }
    assert expected_tables <= tables

    columns = {
        row[0]: (row[1], row[2])
        for row in fetch_all(
            migrated_db,
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'notas'
            """,
        )
    }
    assert columns["numero_nf"] == ("character varying", "NO")
    assert columns["emitente_cnpj"] == ("character varying", "NO")
    assert columns["data_emissao"] == ("date", "NO")
    assert columns["valor_total_nf"][0] == "numeric"

    login_columns = {
        row[0]: (row[1], row[2])
        for row in fetch_all(
            migrated_db,
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'login'
            """,
        )
    }
    assert login_columns["tentativas_falhas"] == ("integer", "NO")
    assert login_columns["bloqueado_ate"] == ("timestamp with time zone", "YES")
    assert login_columns["ultimo_login_em"] == ("timestamp with time zone", "YES")

    constraints = {
        row[0]
        for row in fetch_all(
            migrated_db,
            """
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_schema = 'public'
              AND table_name IN ('notas', 'notas_itens', 'processing_jobs')
            """,
        )
    }
    assert "notas_pkey" in constraints
    assert "notas_itens_pkey" in constraints
    assert "processing_jobs_pkey" in constraints
    assert "ck_processing_jobs_status" in constraints

    fk = fetch_one(
        migrated_db,
        """
        SELECT COUNT(*)
        FROM information_schema.referential_constraints
        WHERE constraint_schema = 'public'
          AND constraint_name = 'notas_itens_nota_id_fkey'
        """,
    )[0]
    assert fk == 1


def test_required_fields_status_lists_and_non_negative_financial_values(migrated_db):
    tributo_id = fetch_one(
        migrated_db, "SELECT id FROM tributos WHERE codigo = 'ICMS';"
    )[0]

    assert_insert_rejected(
        migrated_db,
        "INSERT INTO empresas (cnpj, nome) VALUES (%s, NULL);",
        ("11222333000144",),
    )
    assert_insert_rejected(
        migrated_db,
        """
        INSERT INTO notas (numero_nf, emitente_cnpj, data_emissao)
        VALUES (NULL, %s, CURRENT_DATE);
        """,
        ("11222333000144",),
    )
    assert_insert_rejected(
        migrated_db,
        """
        INSERT INTO processing_jobs (id, tipo, status)
        VALUES ('00000000-0000-0000-0000-000000000001', 'IMPORTACAO_NFE', 'PAGO');
        """,
    )
    assert_insert_rejected(
        migrated_db,
        """
        INSERT INTO apuracao_tributaria
            (empresa_cnpj, periodo_ano, periodo_mes, tributo_id, status)
        VALUES (%s, 2026, 5, %s, 'PENDENTE');
        """,
        ("11222333000144", tributo_id),
    )
    assert_insert_rejected(
        migrated_db,
        """
        INSERT INTO creditos_tributarios
            (empresa_cnpj, periodo_ano, periodo_mes, tributo_id,
             origem_credito, tipo_credito, valor_original)
        VALUES (%s, 2026, 5, %s, 'entrada', 'basico', -1);
        """,
        ("11222333000144", tributo_id),
    )
    assert_insert_rejected(
        migrated_db,
        """
        INSERT INTO debitos_tributarios
            (empresa_cnpj, periodo_ano, periodo_mes, tributo_id,
             origem_debito, tipo_debito, valor_devido)
        VALUES (%s, 2026, 5, %s, 'saida', 'operacao', -1);
        """,
        ("11222333000144", tributo_id),
    )


def test_fiscal_document_business_rules_are_enforced_by_schema(migrated_db):
    tributo_id = fetch_one(
        migrated_db, "SELECT id FROM tributos WHERE codigo = 'ICMS';"
    )[0]
    empresa_id = fetch_one(
        migrated_db,
        "INSERT INTO empresas (cnpj, nome) VALUES (%s, %s) RETURNING id;",
        ("11222333000144", "Empresa Ficticia Teste"),
    )[0]
    processamento_id = fetch_one(
        migrated_db,
        """
        INSERT INTO notas_processamentos (empresa_id, status, data_processamento)
        VALUES (%s, 'processado', NOW())
        RETURNING id;
        """,
        (empresa_id,),
    )[0]
    nota_id = fetch_one(
        migrated_db,
        """
        INSERT INTO notas
            (processamento_id, numero_nf, emitente_cnpj, destinatario_documento,
             destinatario_nome, data_emissao, valor_total_nf)
        VALUES (%s, '1001', %s, %s, 'Cliente Ficticio', '2026-05-10', 150.25)
        RETURNING id;
        """,
        (processamento_id, "11222333000144", "99888777000166"),
    )[0]

    assert nota_id is not None
    assert_insert_rejected(
        migrated_db,
        """
        INSERT INTO documentos_fiscais_tributos
            (nota_id, sped_documento_id, tributo_id, empresa_cnpj, tipo_operacao)
        VALUES (%s, 1, %s, %s, 'SAIDA');
        """,
        (nota_id, tributo_id, "11222333000144"),
    )
    assert_insert_rejected(
        migrated_db,
        """
        INSERT INTO documentos_fiscais_tributos
            (nota_id, tributo_id, empresa_cnpj, tipo_operacao, status)
        VALUES (%s, %s, %s, 'SAIDA', 'PAGO');
        """,
        (nota_id, tributo_id, "11222333000144"),
    )


def test_critical_listing_period_filter_and_financial_totalization_queries(migrated_db):
    empresa_id = fetch_one(
        migrated_db,
        "INSERT INTO empresas (cnpj, nome) VALUES (%s, %s) RETURNING id;",
        ("55666777000188", "Fornecedor e Cliente Ficticio"),
    )[0]
    processamento_id = fetch_one(
        migrated_db,
        """
        INSERT INTO notas_processamentos (empresa_id, status, data_processamento)
        VALUES (%s, 'processado', NOW())
        RETURNING id;
        """,
        (empresa_id,),
    )[0]

    rows = [
        ("2001", "2026-05-01", Decimal("100.00")),
        ("2002", "2026-05-15", Decimal("250.50")),
        ("2003", "2026-06-01", Decimal("75.25")),
    ]
    for numero, data_emissao, valor in rows:
        migrated_db.execute(
            """
            INSERT INTO notas
                (processamento_id, numero_nf, emitente_cnpj, destinatario_documento,
                 destinatario_nome, data_emissao, valor_total_nf)
            VALUES (%s, %s, %s, %s, 'Cliente Ficticio', %s, %s);
            """,
            (
                processamento_id,
                numero,
                "55666777000188",
                "00111222000133",
                data_emissao,
                valor,
            ),
        )

    listagem = fetch_all(
        migrated_db,
        """
        SELECT numero_nf
        FROM notas
        WHERE emitente_cnpj = %s
        ORDER BY data_emissao, numero_nf;
        """,
        ("55666777000188",),
    )
    assert [row[0] for row in listagem] == ["2001", "2002", "2003"]

    filtro_periodo = fetch_all(
        migrated_db,
        """
        SELECT numero_nf
        FROM notas
        WHERE emitente_cnpj = %s
          AND data_emissao >= DATE '2026-05-01'
          AND data_emissao < DATE '2026-06-01'
        ORDER BY numero_nf;
        """,
        ("55666777000188",),
    )
    assert [row[0] for row in filtro_periodo] == ["2001", "2002"]

    total = fetch_one(
        migrated_db,
        """
        SELECT COALESCE(SUM(valor_total_nf), 0)
        FROM notas
        WHERE emitente_cnpj = %s
          AND data_emissao >= DATE '2026-05-01'
          AND data_emissao < DATE '2026-06-01';
        """,
        ("55666777000188",),
    )[0]
    assert total == Decimal("350.50")
