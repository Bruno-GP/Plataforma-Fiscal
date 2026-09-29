# SEFAZ Fase 1 — Migration do schema `sefaz` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar a migration Alembic que introduz o schema `sefaz` (tabelas `certificados`,
`nsu_controle`, `documentos`, `eventos`, `sync_log`) usado pelo módulo de Sincronização SEFAZ.

**Architecture:** Uma única revision Alembic com `op.execute("""SQL""")` (sem SQLAlchemy ORM,
sem `target_metadata` — o projeto não usa isso, ver `API/app/alembic/env.py`), seguindo
exatamente o padrão de `20260730_0010_conta_azul_schema.py`: schema dedicado, DDL idempotente
(`IF NOT EXISTS`), downgrade destrutivo simples (`DROP SCHEMA ... CASCADE`).

**Tech Stack:** Alembic 1.13.3, PostgreSQL, `psycopg` (só usado na validação manual, não na
migration em si).

## Global Constraints

- PK/FK novas são `BIGSERIAL`/`BIGINT`, nunca UUID — `empresas.id` é `BIGINT` neste banco
  (fonte: `docs/superpowers/specs/2026-08-14-sefaz-distribuicao-dfe-design.md`).
- Tabelas em schema dedicado `sefaz.*` (ex: `sefaz.certificados`), nunca `public.sefaz_*`.
- Toda DDL usa `IF NOT EXISTS` (tabela e índice) — convenção de 100% das migrations existentes,
  torna a migration idempotente/segura de reexecutar.
- Campos de CNPJ são `VARCHAR(20)`, nunca tipo numérico (NT 2026.004, CNPJ alfanumérico desde
  2026-07-31).
- `chave_acesso` é `VARCHAR(44)`.
- Sem SQLAlchemy ORM/models — só SQL cru dentro de `op.execute`.
- Revision chain: a revision mais recente hoje é `20260813_0012` (arquivo
  `API/app/alembic/versions/20260813_0012_metas_tabelas.py`). A nova migration usa
  `down_revision = "20260813_0012"`.

---

### Task 1: Migration `sefaz` + teste de conteúdo (sem banco real)

**Files:**
- Create: `API/app/alembic/versions/20260814_0013_sefaz_schema.py`
- Modify: `API/app/tests/test_database_schema.py:94-96` (inserir função de teste nova entre o
  fim de `test_alembic_revisions_and_sql_migrations_cover_expected_database_objects` — linha 93
  — e a linha em branco antes de `def test_staging_import_services_do_not_mutate_database_schema`
  — linha 96)

**Interfaces:**
- Consumes: constantes já existentes no topo de `test_database_schema.py` —
  `ALEMBIC_DIR = APP_DIR / "alembic" / "versions"` (linha 10), `Path` (linha 2), `pytest`
  (linha 4). Não precisa de import novo.
- Produces: arquivo de migration lido por qualquer teste futuro que precise inspecionar DDL do
  schema `sefaz` (ex.: Fase 2 pode reler esse arquivo do mesmo jeito).

- [ ] **Step 1: Escrever o teste que falha (arquivo de migration ainda não existe)**

Abrir `API/app/tests/test_database_schema.py` e inserir, logo após a linha 93
(`        assert expected in login_security`) e antes da linha 96
(`def test_staging_import_services_do_not_mutate_database_schema():`), este bloco (com uma
linha em branco antes e depois, no mesmo estilo das funções vizinhas):

```python
def test_sefaz_migration_creates_expected_schema_objects():
    sefaz_schema = (ALEMBIC_DIR / "20260814_0013_sefaz_schema.py").read_text(
        encoding="utf-8"
    )

    for expected in [
        "CREATE SCHEMA IF NOT EXISTS sefaz",
        "CREATE TABLE IF NOT EXISTS sefaz.certificados",
        "empresa_id BIGINT NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_sefaz_certificados_empresa_ativo",
        "CREATE TABLE IF NOT EXISTS sefaz.nsu_controle",
        "CONSTRAINT uq_sefaz_nsu_controle_empresa_ambiente UNIQUE (empresa_id, ambiente)",
        "CREATE TABLE IF NOT EXISTS sefaz.documentos",
        "CONSTRAINT uq_sefaz_documentos_empresa_chave UNIQUE (empresa_id, chave_acesso)",
        "CREATE TABLE IF NOT EXISTS sefaz.eventos",
        "REFERENCES sefaz.documentos(id) ON DELETE CASCADE",
        "CREATE TABLE IF NOT EXISTS sefaz.sync_log",
    ]:
        assert expected in sefaz_schema, f"esperado no schema sefaz: {expected!r}"

    assert 'revision = "20260814_0013"' in sefaz_schema
    assert 'down_revision = "20260813_0012"' in sefaz_schema
    assert "DROP SCHEMA IF EXISTS sefaz CASCADE" in sefaz_schema
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_database_schema.py -k test_sefaz_migration_creates_expected_schema_objects -v`
Expected: FAIL — `FileNotFoundError` (o arquivo `20260814_0013_sefaz_schema.py` ainda não existe).

- [ ] **Step 3: Criar a migration**

Criar `API/app/alembic/versions/20260814_0013_sefaz_schema.py` com este conteúdo exato:

```python
"""cria schema sefaz (certificados, nsu_controle, documentos, eventos, sync_log)

Revision ID: 20260814_0013
Revises: 20260813_0012
Create Date: 2026-08-14
"""

from alembic import op


revision = "20260814_0013"
down_revision = "20260813_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS sefaz;

        CREATE TABLE IF NOT EXISTS sefaz.certificados (
            id BIGSERIAL PRIMARY KEY,
            empresa_id BIGINT NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
            arquivo_certificado BYTEA NOT NULL,
            senha_criptografada TEXT NOT NULL,
            cnpj_titular VARCHAR(20) NOT NULL,
            data_validade DATE NOT NULL,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE UNIQUE INDEX IF NOT EXISTS uq_sefaz_certificados_empresa_ativo
            ON sefaz.certificados (empresa_id) WHERE ativo;

        CREATE TABLE IF NOT EXISTS sefaz.nsu_controle (
            id BIGSERIAL PRIMARY KEY,
            empresa_id BIGINT NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
            ambiente SMALLINT NOT NULL,
            ultimo_nsu VARCHAR(15) NOT NULL DEFAULT '000000000000000',
            ultima_execucao_em TIMESTAMPTZ,
            status_ultima_execucao VARCHAR(20),
            CONSTRAINT uq_sefaz_nsu_controle_empresa_ambiente UNIQUE (empresa_id, ambiente)
        );

        CREATE TABLE IF NOT EXISTS sefaz.documentos (
            id BIGSERIAL PRIMARY KEY,
            empresa_id BIGINT NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
            chave_acesso VARCHAR(44) NOT NULL,
            tipo_documento VARCHAR(20) NOT NULL,
            direcao VARCHAR(10) NOT NULL,
            cnpj_emitente VARCHAR(20) NOT NULL,
            cnpj_destinatario VARCHAR(20),
            nsu VARCHAR(15) NOT NULL,
            data_emissao TIMESTAMPTZ,
            valor_total NUMERIC(18,2),
            situacao VARCHAR(20),
            xml_armazenado BYTEA,
            manifestacao_status VARCHAR(20),
            criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_sefaz_documentos_empresa_chave UNIQUE (empresa_id, chave_acesso)
        );

        CREATE INDEX IF NOT EXISTS ix_sefaz_documentos_empresa_situacao
            ON sefaz.documentos (empresa_id, situacao);

        CREATE INDEX IF NOT EXISTS ix_sefaz_documentos_manifestacao_pendente
            ON sefaz.documentos (empresa_id) WHERE manifestacao_status = 'pendente';

        CREATE TABLE IF NOT EXISTS sefaz.eventos (
            id BIGSERIAL PRIMARY KEY,
            documento_id BIGINT NOT NULL REFERENCES sefaz.documentos(id) ON DELETE CASCADE,
            empresa_id BIGINT NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
            tipo_evento VARCHAR(30) NOT NULL,
            protocolo VARCHAR(20),
            status VARCHAR(20) NOT NULL,
            payload_xml TEXT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS ix_sefaz_eventos_documento ON sefaz.eventos (documento_id);

        CREATE TABLE IF NOT EXISTS sefaz.sync_log (
            id BIGSERIAL PRIMARY KEY,
            empresa_id BIGINT NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
            iniciado_em TIMESTAMPTZ NOT NULL,
            finalizado_em TIMESTAMPTZ,
            documentos_novos INT NOT NULL DEFAULT 0,
            nsu_inicial VARCHAR(15),
            nsu_final VARCHAR(15),
            status VARCHAR(20) NOT NULL,
            erro_detalhe TEXT
        );

        CREATE INDEX IF NOT EXISTS ix_sefaz_sync_log_empresa
            ON sefaz.sync_log (empresa_id, iniciado_em DESC);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP SCHEMA IF EXISTS sefaz CASCADE;
        """
    )
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_database_schema.py -k test_sefaz_migration_creates_expected_schema_objects -v`
Expected: PASS.

- [ ] **Step 5: Rodar a suíte rápida inteira pra garantir que nada quebrou**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests -q`
Expected: todos os testes passam (a suíte rápida não toca Postgres real, exceto os testes
guardados por `PLATAFORMA_FISCAL_TEST_DATABASE_URL`, que ficam `SKIPPED` se a env var não
estiver definida).

- [ ] **Step 6: Commit**

```bash
git add API/app/alembic/versions/20260814_0013_sefaz_schema.py API/app/tests/test_database_schema.py
git commit -m "feat(sefaz): cria schema sefaz (certificados, nsu_controle, documentos, eventos, sync_log)"
```

---

### Task 2: Validar a migration contra PostgreSQL real (upgrade e downgrade)

**Files:** nenhum arquivo novo — só execução e verificação. Se algo falhar aqui, volte à Task 1
para corrigir `20260814_0013_sefaz_schema.py` e repita esta task do zero.

**Interfaces:**
- Consumes: `API/app/alembic/versions/20260814_0013_sefaz_schema.py` (Task 1), fixture
  `migrated_db`/`test_database_url` em `API/app/tests/conftest.py:66-129` (já existente, não
  precisa mexer), `API/app/alembic.ini`, `API/app/alembic/env.py` (lê `DATABASE_URL`/
  `POSTGRES_DSN`, ver `_database_url()` em `env.py:40-61`).
- Produces: nada consumido por outra task — é o gate de saída da Fase 1.

Pré-requisito: um PostgreSQL local descartável acessível, com um banco cujo nome contenha
`test` ou `teste` (a fixture `_is_safe_test_database` em `conftest.py:58-63` recusa qualquer
outro nome). Se você não tem um Postgres disponível, rode via Docker:
`docker run --rm -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16` e crie o banco
`plataforma_fiscal_test` (`createdb -h localhost -U postgres plataforma_fiscal_test` ou
equivalente).

- [ ] **Step 1: Rodar a suíte guardada por Postgres real (exercita `alembic upgrade head`)**

```powershell
$env:PLATAFORMA_FISCAL_TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/plataforma_fiscal_test"
cd API
.\.venv-local\Scripts\python.exe -m pytest app/tests/test_database_schema.py -q
```

Expected: todos os testes passam, incluindo `test_migrations_run_to_head_in_clean_test_database`
e o novo `test_sefaz_migration_creates_expected_schema_objects`. A fixture `migrated_db` já
recria o schema `public` do zero e roda `alembic upgrade head` — se a migration da Task 1 tiver
erro de SQL, esse comando falha aqui com o erro do Postgres.

- [ ] **Step 2: Confirmar manualmente que as tabelas do schema `sefaz` existem após o upgrade**

```powershell
$env:DATABASE_URL = $env:PLATAFORMA_FISCAL_TEST_DATABASE_URL
cd API
.\.venv-local\Scripts\python.exe -m alembic -c app\alembic.ini upgrade head
```

```powershell
psql $env:PLATAFORMA_FISCAL_TEST_DATABASE_URL -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'sefaz' ORDER BY table_name;"
```

Expected: 5 linhas — `certificados`, `documentos`, `eventos`, `nsu_controle`, `sync_log`.

- [ ] **Step 3: Confirmar que o downgrade remove o schema por completo**

```powershell
cd API
.\.venv-local\Scripts\python.exe -m alembic -c app\alembic.ini downgrade -1
```

```powershell
psql $env:PLATAFORMA_FISCAL_TEST_DATABASE_URL -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'sefaz';"
```

Expected: 0 linhas (schema `sefaz` não existe mais).

- [ ] **Step 4: Restaurar o banco de teste pro estado `head`**

```powershell
cd API
.\.venv-local\Scripts\python.exe -m alembic -c app\alembic.ini upgrade head
```

Expected: comando roda sem erro (deixa o banco de teste pronto pra próxima pessoa/CI usar).

- [ ] **Step 5: Limpar variáveis de ambiente da sessão**

```powershell
Remove-Item Env:\DATABASE_URL
Remove-Item Env:\PLATAFORMA_FISCAL_TEST_DATABASE_URL
```

Sem commit nesta task — nenhum arquivo foi alterado, só validado contra Postgres real. Fase 1
está completa quando as Tasks 1 e 2 passarem; aguardar validação do usuário antes de começar o
plano da Fase 2 (backend).
