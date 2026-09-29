# Integração Conta Azul — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Conta Azul" section to the company settings screen (`Painel/src/pages/Configuracoes.tsx`) that lets a user connect their company to Conta Azul via OAuth2, see integration status, and trigger/monitor data syncs — backed by new FastAPI routes, Postgres tables, and a Celery sync task (none of which exist yet).

**Architecture:** Backend follows the repo's existing raw-psycopg + services/repositories/routes layering (no ORM). The Conta Azul OAuth2 client and HTTP client already built in the standalone `API/contaazul-integracao/` CLI are **ported** (copied and adapted, not imported) into `API/app/services/conta_azul/`, because that CLI folder has no packaging metadata and isn't on the API's `PYTHONPATH`/Docker image dependencies. OAuth2 tokens are encrypted at rest with Fernet. Sync runs as a Celery task writing per-entity rows into `conta_azul.sincronizacoes`, polled by the frontend. Frontend is a new Card (`ContaAzulSection`) dropped into the existing `Configuracoes.tsx` grid, following the `CompanyDataCard` pattern exactly (Tailwind + shadcn/ui, no new UI library).

**Tech Stack:** FastAPI, psycopg3, Alembic, Celery/Redis, httpx, tenacity, cryptography (Fernet), pytest/respx — React 18 + TypeScript, Vite, Tailwind, shadcn/ui (Radix), TanStack Query is available but not required here, vitest + @testing-library/react + msw.

## Global Constraints

- Backend has **no ORM** — all DB access is raw `psycopg` with `row_factory=dict_row`, via a `_connect()` helper using `carregar_config_postgres()`/`opcoes_conexao_postgres()` from `app/services/nfe/postres_config.py`. Follow this exactly; do not introduce SQLAlchemy models.
- All new tables live in a new Postgres schema `conta_azul` (not `public`), per user decision.
- OAuth2 tokens (`access_token`, `refresh_token`) must be Fernet-encrypted before being written to Postgres, per user decision. Key comes from `CONTAAZUL_TOKEN_ENCRYPTION_KEY` (no insecure default — fail loudly if unset).
- All new routes require `Depends(get_current_user)` (`app/core/security.py`) and must verify the `empresa_id` path param matches `current_user.empresa_id` (403 otherwise) — mirrors `require_company_scope`'s spirit but for a path param, which that dependency doesn't cover.
- Do not import anything from `API/contaazul-integracao/` into `API/app/` — that folder is not on the API's Docker image `PYTHONPATH` and its `requirements.txt` (tenacity, respx) is not installed there. Port the needed code instead.
- Frontend is TypeScript (`.ts`/`.tsx`), not JSX. Use only what's already in the repo: Tailwind classes, `@/components/ui/*` (shadcn/ui), `@/hooks/use-toast`, `apiFetch`/`API_BASE_URL` from `@/services/api`. No axios, no CSS Modules, no new UI library.
- New section goes into `Painel/src/pages/Configuracoes.tsx`, as a sibling Card to `CompanyDataCard`/`PasswordChangeCard`.
- Migration file naming follows `YYYYMMDD_NNNN_description.py`; next revision is `20260728_0009`, `down_revision = "20260612_0008"` (the current head).
- Sync window for `vendas`/`contas_receber`/`contas_pagar` (which require a date range) defaults to the trailing 365 days (`SYNC_JANELA_DIAS = 365`) — there is no UI date picker for "Sincronizar agora".

---

### Task 1: Dependencies + Conta Azul config getters

**Files:**
- Modify: `API/app/requirements.txt`
- Modify: `API/app/.env.example`
- Modify: `API/app/core/config.py`
- Test: `API/app/tests/test_config_security.py`

**Interfaces:**
- Produces: `get_contaazul_client_id() -> str`, `get_contaazul_client_secret() -> str`, `get_contaazul_redirect_uri() -> str`, `get_contaazul_token_encryption_key() -> str` in `app.core.config`, all used by later tasks.

- [ ] **Step 1: Write the failing tests**

Append to `API/app/tests/test_config_security.py`:

```python
def test_contaazul_getters_leem_env(monkeypatch):
    from app.core import config

    monkeypatch.setenv("CONTAAZUL_CLIENT_ID", "client-123")
    monkeypatch.setenv("CONTAAZUL_CLIENT_SECRET", "secret-456")
    monkeypatch.setenv("CONTAAZUL_REDIRECT_URI", "https://api.example.com/api/conta-azul/callback")
    monkeypatch.setenv("CONTAAZUL_TOKEN_ENCRYPTION_KEY", "a-key")

    assert config.get_contaazul_client_id() == "client-123"
    assert config.get_contaazul_client_secret() == "secret-456"
    assert config.get_contaazul_redirect_uri() == "https://api.example.com/api/conta-azul/callback"
    assert config.get_contaazul_token_encryption_key() == "a-key"


def test_contaazul_getters_default_vazio(monkeypatch):
    from app.core import config

    monkeypatch.delenv("CONTAAZUL_CLIENT_ID", raising=False)
    monkeypatch.delenv("CONTAAZUL_TOKEN_ENCRYPTION_KEY", raising=False)

    assert config.get_contaazul_client_id() == ""
    assert config.get_contaazul_token_encryption_key() == ""


def test_validate_production_config_exige_contaazul_configurado_quando_habilitado(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://painel.example.com")
    monkeypatch.setenv("CORS_ALLOW_ORIGIN_REGEX", "")
    monkeypatch.setenv("CONTAAZUL_CLIENT_ID", "client-123")
    monkeypatch.delenv("CONTAAZUL_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("CONTAAZUL_REDIRECT_URI", raising=False)
    monkeypatch.delenv("CONTAAZUL_TOKEN_ENCRYPTION_KEY", raising=False)

    from app.core.config import validate_production_config

    with pytest.raises(RuntimeError, match="CONTAAZUL"):
        validate_production_config()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd API/app && python -m pytest tests/test_config_security.py -k contaazul -v`
Expected: FAIL with `AttributeError: module 'app.core.config' has no attribute 'get_contaazul_client_id'`

- [ ] **Step 3: Add dependencies**

Append to `API/app/requirements.txt`:

```
tenacity==8.5.0
cryptography==43.0.1
respx==0.21.1
```

- [ ] **Step 4: Add config getters and production validation**

Append to `API/app/core/config.py`:

```python
def get_contaazul_client_id() -> str:
    return os.getenv("CONTAAZUL_CLIENT_ID", "").strip()


def get_contaazul_client_secret() -> str:
    return os.getenv("CONTAAZUL_CLIENT_SECRET", "").strip()


def get_contaazul_redirect_uri() -> str:
    return os.getenv("CONTAAZUL_REDIRECT_URI", "").strip()


def get_contaazul_token_encryption_key() -> str:
    return os.getenv("CONTAAZUL_TOKEN_ENCRYPTION_KEY", "").strip()
```

In `validate_production_config()`, right before `if errors:`, add:

```python
    if get_contaazul_client_id():
        if not get_contaazul_client_secret():
            errors.append("CONTAAZUL_CLIENT_SECRET deve ser definido quando CONTAAZUL_CLIENT_ID estiver configurado")
        if not get_contaazul_redirect_uri():
            errors.append("CONTAAZUL_REDIRECT_URI deve ser definido quando CONTAAZUL_CLIENT_ID estiver configurado")
        if not get_contaazul_token_encryption_key():
            errors.append("CONTAAZUL_TOKEN_ENCRYPTION_KEY deve ser definido quando CONTAAZUL_CLIENT_ID estiver configurado")
```

Append to `API/app/.env.example`:

```
CONTAAZUL_CLIENT_ID=
CONTAAZUL_CLIENT_SECRET=
CONTAAZUL_REDIRECT_URI=
# Gere com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
CONTAAZUL_TOKEN_ENCRYPTION_KEY=
```

- [ ] **Step 5: Install dependencies and run tests to verify they pass**

Run: `cd API/app && pip install -r requirements.txt && python -m pytest tests/test_config_security.py -v`
Expected: PASS (all tests in the file, including the 3 new ones)

- [ ] **Step 6: Commit**

```bash
git add API/app/requirements.txt API/app/.env.example API/app/core/config.py API/app/tests/test_config_security.py
git commit -m "feat: add Conta Azul config getters and dependencies"
```

---

### Task 2: Migration — `conta_azul` schema

**Files:**
- Create: `API/app/alembic/versions/20260728_0009_conta_azul_schema.py`
- Test: `API/app/tests/test_conta_azul_migration.py`

**Interfaces:**
- Produces: Postgres schema `conta_azul` with tables `integracoes` and `sincronizacoes`, exact columns as in the design spec. Later tasks' repositories depend on these exact column names.

- [ ] **Step 1: Write the failing test**

Create `API/app/tests/test_conta_azul_migration.py`:

```python
from pathlib import Path

ALEMBIC_DIR = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def test_conta_azul_migration_cria_schema_e_tabelas_esperadas():
    migration = (ALEMBIC_DIR / "20260728_0009_conta_azul_schema.py").read_text(encoding="utf-8")

    for expected in [
        "CREATE SCHEMA IF NOT EXISTS conta_azul",
        "CREATE TABLE IF NOT EXISTS conta_azul.integracoes",
        "REFERENCES public.empresas(id) ON DELETE CASCADE",
        "UNIQUE (empresa_id)",
        "CREATE TABLE IF NOT EXISTS conta_azul.sincronizacoes",
        "REFERENCES conta_azul.integracoes(id) ON DELETE CASCADE",
        "ix_sincronizacoes_integracao_run",
    ]:
        assert expected in migration
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd API/app && python -m pytest tests/test_conta_azul_migration.py -v`
Expected: FAIL with `FileNotFoundError`

- [ ] **Step 3: Write the migration**

Create `API/app/alembic/versions/20260728_0009_conta_azul_schema.py`:

```python
"""conta azul schema

Revision ID: 20260728_0009
Revises: 20260612_0008
Create Date: 2026-07-28
"""

from alembic import op


revision = "20260728_0009"
down_revision = "20260612_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS conta_azul;

        CREATE TABLE IF NOT EXISTS conta_azul.integracoes (
            id BIGSERIAL PRIMARY KEY,
            empresa_id BIGINT NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
            access_token_encrypted TEXT,
            refresh_token_encrypted TEXT,
            token_expira_em TIMESTAMPTZ,
            oauth_state VARCHAR(255),
            oauth_state_expira_em TIMESTAMPTZ,
            erro_mensagem TEXT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_conta_azul_integracoes_empresa UNIQUE (empresa_id)
        );

        CREATE TABLE IF NOT EXISTS conta_azul.sincronizacoes (
            id BIGSERIAL PRIMARY KEY,
            integracao_id BIGINT NOT NULL REFERENCES conta_azul.integracoes(id) ON DELETE CASCADE,
            run_id UUID NOT NULL,
            entidade VARCHAR(30) NOT NULL,
            status VARCHAR(20) NOT NULL,
            registros_processados INTEGER,
            erro_mensagem TEXT,
            iniciado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            fim_em TIMESTAMPTZ
        );

        CREATE INDEX IF NOT EXISTS ix_sincronizacoes_integracao_run
        ON conta_azul.sincronizacoes (integracao_id, run_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS conta_azul.sincronizacoes;
        DROP TABLE IF EXISTS conta_azul.integracoes;
        DROP SCHEMA IF EXISTS conta_azul;
        """
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd API/app && python -m pytest tests/test_conta_azul_migration.py -v`
Expected: PASS

- [ ] **Step 5: If a disposable test database is configured, apply and verify the migration**

Run (only if `PLATAFORMA_FISCAL_TEST_DATABASE_URL` is set in your shell):
`cd API/app && PLATAFORMA_FISCAL_TEST_DATABASE_URL=$PLATAFORMA_FISCAL_TEST_DATABASE_URL python -m pytest tests/test_database_schema.py -v`
This doesn't test the new migration directly but confirms `alembic upgrade head` still runs cleanly end-to-end with the new revision appended. If the env var isn't set, skip this step — Task 6/7's repository tests will exercise `alembic upgrade head` against the new tables via the same `migrated_db` fixture.

- [ ] **Step 6: Commit**

```bash
git add API/app/alembic/versions/20260728_0009_conta_azul_schema.py API/app/tests/test_conta_azul_migration.py
git commit -m "feat: add conta_azul schema migration (integracoes, sincronizacoes)"
```

---

### Task 3: Crypto service (Fernet token encryption)

**Files:**
- Create: `API/app/services/conta_azul/__init__.py`
- Create: `API/app/services/conta_azul/crypto_service.py`
- Test: `API/app/tests/test_conta_azul_crypto.py`

**Interfaces:**
- Consumes: `get_contaazul_token_encryption_key()` from Task 1.
- Produces: `encrypt_token(value: str) -> str`, `decrypt_token(value: str) -> str`, both raising `RuntimeError` if the key is unset. Used by Task 6 (repository) and Task 8 (sync service).

- [ ] **Step 1: Write the failing test**

Create `API/app/tests/test_conta_azul_crypto.py`:

```python
import pytest
from cryptography.fernet import Fernet


def test_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setenv("CONTAAZUL_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())

    from app.services.conta_azul.crypto_service import decrypt_token, encrypt_token

    ciphertext = encrypt_token("meu-token-secreto")
    assert ciphertext != "meu-token-secreto"
    assert decrypt_token(ciphertext) == "meu-token-secreto"


def test_encrypt_sem_chave_configurada_falha(monkeypatch):
    monkeypatch.delenv("CONTAAZUL_TOKEN_ENCRYPTION_KEY", raising=False)

    from app.services.conta_azul.crypto_service import encrypt_token

    with pytest.raises(RuntimeError, match="CONTAAZUL_TOKEN_ENCRYPTION_KEY"):
        encrypt_token("qualquer-coisa")


def test_decrypt_token_corrompido_falha(monkeypatch):
    monkeypatch.setenv("CONTAAZUL_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())

    from app.services.conta_azul.crypto_service import decrypt_token

    with pytest.raises(ValueError, match="corrompido"):
        decrypt_token("nao-e-um-token-fernet-valido")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd API/app && python -m pytest tests/test_conta_azul_crypto.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.conta_azul'`

- [ ] **Step 3: Implement**

Create `API/app/services/conta_azul/__init__.py` (empty file).

Create `API/app/services/conta_azul/crypto_service.py`:

```python
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_contaazul_token_encryption_key


def _fernet() -> Fernet:
    key = get_contaazul_token_encryption_key()
    if not key:
        raise RuntimeError(
            "CONTAAZUL_TOKEN_ENCRYPTION_KEY nao configurada. Gere uma com "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"`."
        )
    return Fernet(key.encode("utf-8"))


def encrypt_token(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_token(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Token Conta Azul corrompido ou chave de criptografia invalida.") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd API/app && python -m pytest tests/test_conta_azul_crypto.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add API/app/services/conta_azul/__init__.py API/app/services/conta_azul/crypto_service.py API/app/tests/test_conta_azul_crypto.py
git commit -m "feat: add Fernet-based Conta Azul token encryption service"
```

---

### Task 4: Ported Conta Azul models + HTTP client

**Files:**
- Create: `API/app/services/conta_azul/contaazul_models.py`
- Create: `API/app/services/conta_azul/contaazul_client.py`
- Test: `API/app/tests/test_conta_azul_client.py`

**Interfaces:**
- Produces: `ContaAzulClient(access_token: str)` with `listar_pessoas_todas() -> list[Cliente]`, `listar_produtos_todos() -> list[Produto]`, `listar_categorias_todas() -> list[Categoria]`, `listar_vendas_todas(data_inicio: date, data_fim: date) -> list[Venda]`, `listar_contas_a_receber_todas(data_inicio, data_fim) -> list[ContaReceber]`, `listar_contas_a_pagar_todas(data_inicio, data_fim) -> list[ContaPagar]`. Exceptions `ApiError(status_code, payload)`, `AuthError`. Used by Task 8 (sync service).

- [ ] **Step 1: Write the failing tests**

Create `API/app/tests/test_conta_azul_client.py`:

```python
from datetime import date

import httpx
import pytest
import respx

from app.services.conta_azul.contaazul_client import ApiError, AuthError, ContaAzulClient

BASE_URL = "https://api-v2.contaazul.com"


@respx.mock
def test_listar_pessoas_todas_pagina_ate_pagina_incompleta():
    respx.get(f"{BASE_URL}/v1/pessoas").mock(
        side_effect=[
            httpx.Response(200, json={"itens": [{"id": str(i), "nome": f"Pessoa {i}"} for i in range(100)]}),
            httpx.Response(200, json={"itens": [{"id": "100", "nome": "Pessoa 100"}]}),
        ]
    )

    client = ContaAzulClient(access_token="token-teste")
    pessoas = client.listar_pessoas_todas()

    assert len(pessoas) == 101
    assert pessoas[0].nome == "Pessoa 0"


@respx.mock
def test_listar_produtos_todos_pagina_unica():
    respx.get(f"{BASE_URL}/v1/produto/busca").mock(
        return_value=httpx.Response(200, json={"itens": [{"id": "p1", "nome": "Produto 1"}]})
    )

    client = ContaAzulClient(access_token="token-teste")
    produtos = client.listar_produtos_todos()

    assert len(produtos) == 1
    assert produtos[0].nome == "Produto 1"


@respx.mock
def test_retry_em_429_ate_sucesso():
    route = respx.get(f"{BASE_URL}/v1/categorias").mock(
        side_effect=[
            httpx.Response(429),
            httpx.Response(200, json={"itens": [{"id": "c1", "nome": "Categoria 1"}]}),
        ]
    )

    client = ContaAzulClient(access_token="token-teste")
    categorias = client.listar_categorias_todas()

    assert route.call_count == 2
    assert categorias[0].nome == "Categoria 1"


@respx.mock
def test_404_vira_api_error():
    respx.get(f"{BASE_URL}/v1/venda/busca").mock(return_value=httpx.Response(404, text="not found"))

    client = ContaAzulClient(access_token="token-teste")
    with pytest.raises(ApiError) as exc_info:
        client.listar_vendas_todas(date(2026, 1, 1), date(2026, 1, 31))

    assert exc_info.value.status_code == 404


@respx.mock
def test_401_vira_auth_error():
    respx.get(
        f"{BASE_URL}/v1/financeiro/eventos-financeiros/contas-a-receber/buscar"
    ).mock(return_value=httpx.Response(401, text="unauthorized"))

    client = ContaAzulClient(access_token="token-invalido")
    with pytest.raises(AuthError):
        client.listar_contas_a_receber_todas(date(2026, 1, 1), date(2026, 1, 31))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd API/app && python -m pytest tests/test_conta_azul_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.conta_azul.contaazul_client'`

- [ ] **Step 3: Implement models**

Create `API/app/services/conta_azul/contaazul_models.py`:

```python
"""Schemas normalizados da API v2 do Conta Azul usados na sincronizacao.

Portado de API/contaazul-integracao/contaazul/models.py, mantendo apenas as
entidades sincronizadas por esta feature (pessoas, produtos, categorias,
vendas, financeiro). Todo modelo usa extra="allow" e guarda o payload
original em `raw`, entao nenhum dado e perdido mesmo que um campo aqui nao
esteja mapeado explicitamente.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ContaAzulBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    raw: dict = Field(default_factory=dict, repr=False)


class Cliente(ContaAzulBaseModel):
    id: str
    nome: str
    documento: Optional[str] = None
    tipo_pessoa: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None


class Categoria(ContaAzulBaseModel):
    id: str
    nome: str
    tipo: Optional[str] = None


class Venda(ContaAzulBaseModel):
    id: str
    numero: Optional[int] = None
    data: Optional[date] = None
    tipo: Optional[str] = None
    origem: Optional[str] = None
    total: Optional[float] = None
    situacao: Optional[dict] = None
    cliente: Optional[dict] = None


class ContaReceber(ContaAzulBaseModel):
    id: str
    descricao: Optional[str] = None
    data_vencimento: Optional[date] = None
    status: Optional[str] = None
    total: Optional[float] = None
    pago: Optional[float] = None
    nao_pago: Optional[float] = None
    cliente: Optional[dict] = None


class ContaPagar(ContaAzulBaseModel):
    id: str
    descricao: Optional[str] = None
    data_vencimento: Optional[date] = None
    status: Optional[str] = None
    total: Optional[float] = None
    pago: Optional[float] = None
    nao_pago: Optional[float] = None
    fornecedor: Optional[dict] = None


class Produto(ContaAzulBaseModel):
    id: str
    id_legado: Optional[int] = None
    nome: str
    codigo_sku: Optional[str] = None
    codigo_ean: Optional[str] = None
    tipo: Optional[str] = None
    status: Optional[str] = None
    estoque: Optional[float] = None
    valor_venda: Optional[float] = None
    custo_medio: Optional[float] = None
```

- [ ] **Step 4: Implement client**

Create `API/app/services/conta_azul/contaazul_client.py`:

```python
"""Cliente HTTP para a API v2 da Conta Azul.

Portado de API/contaazul-integracao/contaazul/client.py. Diferencas da
versao da CLI: recebe o access_token diretamente no construtor (a validade
e renovacao do token sao responsabilidade de SyncService, nao do client) e
so implementa os 5 recursos usados pela sincronizacao (pessoas, produtos,
categorias, vendas, contas a receber/pagar).
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Callable, Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.services.conta_azul.contaazul_models import (
    Categoria,
    Cliente,
    ContaPagar,
    ContaReceber,
    Produto,
    Venda,
)

logger = logging.getLogger("conta_azul.client")

BASE_URL = "https://api-v2.contaazul.com"

ENDPOINTS = {
    "vendas": "/v1/venda/busca",
    "pessoas": "/v1/pessoas",
    "categorias": "/v1/categorias",
    "contas_receber": "/v1/financeiro/eventos-financeiros/contas-a-receber/buscar",
    "contas_pagar": "/v1/financeiro/eventos-financeiros/contas-a-pagar/buscar",
    "produtos": "/v1/produto/busca",
}

PAGE_PARAM = "pagina"
PAGE_SIZE_PARAM = "tamanho_pagina"
DEFAULT_PAGE_SIZE = 100

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class ApiError(Exception):
    """Erro retornado pela API da Conta Azul (status >= 400 nao retentavel)."""

    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"Conta Azul API respondeu {status_code}: {payload}")


class AuthError(Exception):
    """Token rejeitado pela API da Conta Azul (401)."""


class _RetryableApiError(Exception):
    def __init__(self, response: httpx.Response):
        self.response = response
        super().__init__(f"status {response.status_code}")


def _extract_items(payload) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("itens", "items", "dados", "data", "content", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    raise ApiError(200, f"Formato de resposta paginada inesperado: {payload!r}")


class ContaAzulClient:
    def __init__(
        self,
        access_token: str,
        base_url: str = BASE_URL,
        http_client: Optional[httpx.Client] = None,
    ):
        self.access_token = access_token
        self.base_url = base_url
        self._http = http_client or httpx.Client(timeout=30)

    def close(self) -> None:
        self._http.close()

    @retry(
        retry=retry_if_exception_type(_RetryableApiError),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _do_request(self, method: str, url: str, params: dict) -> httpx.Response:
        started = time.monotonic()
        response = self._http.request(
            method,
            url,
            params=params,
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        elapsed_ms = (time.monotonic() - started) * 1000
        logger.info(
            "conta_azul_request endpoint=%s status=%s elapsed_ms=%.1f",
            url,
            response.status_code,
            elapsed_ms,
        )
        if response.status_code in RETRYABLE_STATUS:
            raise _RetryableApiError(response)
        return response

    def _request_json(self, path: str, params: dict) -> dict:
        url = f"{self.base_url}{path}"
        try:
            response = self._do_request("GET", url, params)
        except _RetryableApiError as exc:
            raise ApiError(exc.response.status_code, exc.response.text) from exc

        if response.status_code == 401:
            raise AuthError(f"Token rejeitado (401) em {url}.")
        if response.status_code >= 400:
            raise ApiError(response.status_code, response.text)
        return response.json()

    def _get(self, resource_key: str, params: dict) -> list[dict]:
        return _extract_items(self._request_json(ENDPOINTS[resource_key], params))

    def _paginar(self, buscar_pagina: Callable[[int], list]) -> list:
        resultados: list = []
        pagina = 1
        while True:
            itens_pagina = buscar_pagina(pagina)
            resultados.extend(itens_pagina)
            if len(itens_pagina) < DEFAULT_PAGE_SIZE:
                break
            pagina += 1
        return resultados

    def listar_pessoas(self, pagina: int = 1) -> list[Cliente]:
        items = self._get("pessoas", {PAGE_PARAM: pagina, PAGE_SIZE_PARAM: DEFAULT_PAGE_SIZE})
        return [Cliente(**item, raw=item) for item in items]

    def listar_pessoas_todas(self) -> list[Cliente]:
        return self._paginar(self.listar_pessoas)

    def listar_produtos(self, pagina: int = 1) -> list[Produto]:
        items = self._get("produtos", {PAGE_PARAM: pagina, PAGE_SIZE_PARAM: DEFAULT_PAGE_SIZE})
        return [Produto(**item, raw=item) for item in items]

    def listar_produtos_todos(self) -> list[Produto]:
        return self._paginar(self.listar_produtos)

    def listar_categorias(self, pagina: int = 1) -> list[Categoria]:
        items = self._get(
            "categorias",
            {PAGE_PARAM: pagina, PAGE_SIZE_PARAM: DEFAULT_PAGE_SIZE, "permite_apenas_filhos": False},
        )
        return [Categoria(**item, raw=item) for item in items]

    def listar_categorias_todas(self) -> list[Categoria]:
        return self._paginar(self.listar_categorias)

    def listar_vendas(self, data_inicio: date, data_fim: date, pagina: int = 1) -> list[Venda]:
        items = self._get(
            "vendas",
            {
                "data_inicio": data_inicio.isoformat(),
                "data_fim": data_fim.isoformat(),
                PAGE_PARAM: pagina,
                PAGE_SIZE_PARAM: DEFAULT_PAGE_SIZE,
            },
        )
        return [Venda(**item, raw=item) for item in items]

    def listar_vendas_todas(self, data_inicio: date, data_fim: date) -> list[Venda]:
        return self._paginar(lambda pagina: self.listar_vendas(data_inicio, data_fim, pagina))

    def listar_contas_a_receber(self, data_inicio: date, data_fim: date, pagina: int = 1) -> list[ContaReceber]:
        items = self._get(
            "contas_receber",
            {
                "data_vencimento_de": data_inicio.isoformat(),
                "data_vencimento_ate": data_fim.isoformat(),
                PAGE_PARAM: pagina,
                PAGE_SIZE_PARAM: DEFAULT_PAGE_SIZE,
            },
        )
        return [ContaReceber(**item, raw=item) for item in items]

    def listar_contas_a_receber_todas(self, data_inicio: date, data_fim: date) -> list[ContaReceber]:
        return self._paginar(lambda pagina: self.listar_contas_a_receber(data_inicio, data_fim, pagina))

    def listar_contas_a_pagar(self, data_inicio: date, data_fim: date, pagina: int = 1) -> list[ContaPagar]:
        items = self._get(
            "contas_pagar",
            {
                "data_vencimento_de": data_inicio.isoformat(),
                "data_vencimento_ate": data_fim.isoformat(),
                PAGE_PARAM: pagina,
                PAGE_SIZE_PARAM: DEFAULT_PAGE_SIZE,
            },
        )
        return [ContaPagar(**item, raw=item) for item in items]

    def listar_contas_a_pagar_todas(self, data_inicio: date, data_fim: date) -> list[ContaPagar]:
        return self._paginar(lambda pagina: self.listar_contas_a_pagar(data_inicio, data_fim, pagina))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd API/app && python -m pytest tests/test_conta_azul_client.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add API/app/services/conta_azul/contaazul_models.py API/app/services/conta_azul/contaazul_client.py API/app/tests/test_conta_azul_client.py
git commit -m "feat: port Conta Azul HTTP client and models into the API"
```

---

### Task 5: Ported OAuth2 auth service

**Files:**
- Create: `API/app/services/conta_azul/auth_service.py`
- Test: `API/app/tests/test_conta_azul_auth_service.py`

**Interfaces:**
- Produces: `ContaAzulAuthService(client_id, client_secret, redirect_uri)` with `build_authorization_url(scope=None) -> tuple[str, str]`, `exchange_code_for_token(code: str) -> ContaAzulTokenSet`, `refresh_access_token(refresh_token: str) -> ContaAzulTokenSet`. `ContaAzulTokenSet(access_token, refresh_token, expires_in, obtained_at, token_type, scope)`. Exceptions `AuthError`, `ReauthorizationRequired(AuthError)`. Used by Task 8 (sync service) and Task 11 (routes).

- [ ] **Step 1: Write the failing tests**

Create `API/app/tests/test_conta_azul_auth_service.py`:

```python
import httpx
import pytest
import respx

from app.services.conta_azul.auth_service import (
    AuthError,
    ContaAzulAuthService,
    ReauthorizationRequired,
)

TOKEN_URL = "https://auth.contaazul.com/oauth2/token"


def _service() -> ContaAzulAuthService:
    return ContaAzulAuthService(
        client_id="client-123",
        client_secret="secret-456",
        redirect_uri="https://api.example.com/api/conta-azul/callback",
    )


def test_build_authorization_url_inclui_client_id_e_redirect_uri():
    url, state = _service().build_authorization_url()

    assert url.startswith("https://auth.contaazul.com/oauth2/authorize?")
    assert "client_id=client-123" in url
    assert "redirect_uri=" in url
    assert state in url


@respx.mock
def test_exchange_code_for_token_retorna_tokens():
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "access-123",
                "refresh_token": "refresh-456",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )
    )

    tokens = _service().exchange_code_for_token("codigo-de-autorizacao")

    assert tokens.access_token == "access-123"
    assert tokens.refresh_token == "refresh-456"
    assert tokens.expires_in == 3600


@respx.mock
def test_exchange_code_for_token_erro_levanta_auth_error():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(400, text="invalid_grant"))

    with pytest.raises(AuthError):
        _service().exchange_code_for_token("codigo-invalido")


@respx.mock
def test_refresh_access_token_com_refresh_invalido_levanta_reauthorization_required():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(400, text="invalid_grant"))

    with pytest.raises(ReauthorizationRequired):
        _service().refresh_access_token("refresh-expirado")


@respx.mock
def test_refresh_access_token_sucesso():
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "novo-access", "refresh_token": "novo-refresh", "expires_in": 3600},
        )
    )

    tokens = _service().refresh_access_token("refresh-valido")

    assert tokens.access_token == "novo-access"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd API/app && python -m pytest tests/test_conta_azul_auth_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.conta_azul.auth_service'`

- [ ] **Step 3: Implement**

Create `API/app/services/conta_azul/auth_service.py`:

```python
"""Fluxo OAuth2 (Authorization Code) para a API v2 da Conta Azul.

Portado de API/contaazul-integracao/contaazul/auth.py: sem TokenStore em
arquivo (persistencia fica a cargo de IntegracoesRepository, via
crypto_service) e sem os fluxos so-de-CLI (run_local_authorization_flow /
run_manual_authorization_flow) — o callback web recebe code/state
diretamente como query params de uma rota FastAPI.
"""

from __future__ import annotations

import base64
import secrets
import time
import urllib.parse
from dataclasses import dataclass
from typing import Optional

import httpx

AUTH_URL = "https://auth.contaazul.com/oauth2/authorize"
TOKEN_URL = "https://auth.contaazul.com/oauth2/token"


class AuthError(Exception):
    """Erro de autenticacao/autorizacao junto a Conta Azul."""


class ReauthorizationRequired(AuthError):
    """refresh_token invalido/expirado: integracao precisa ser reconectada."""


@dataclass
class ContaAzulTokenSet:
    access_token: str
    refresh_token: str
    expires_in: int
    obtained_at: float
    token_type: str = "Bearer"
    scope: Optional[str] = None


class ContaAzulAuthService:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        http_client: Optional[httpx.Client] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._http = http_client or httpx.Client(timeout=30)

    def _basic_auth_header(self) -> str:
        raw = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")

    def build_authorization_url(self, scope: Optional[str] = None) -> tuple[str, str]:
        """Retorna (url, state). O state deve ser persistido para validar o callback."""
        state = secrets.token_urlsafe(24)
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        if scope:
            params["scope"] = scope
        return f"{AUTH_URL}?{urllib.parse.urlencode(params)}", state

    def exchange_code_for_token(self, code: str) -> ContaAzulTokenSet:
        response = self._http.post(
            TOKEN_URL,
            headers={
                "Authorization": self._basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
            },
        )
        return self._handle_token_response(response)

    def refresh_access_token(self, refresh_token: str) -> ContaAzulTokenSet:
        response = self._http.post(
            TOKEN_URL,
            headers={
                "Authorization": self._basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        if response.status_code in (400, 401):
            raise ReauthorizationRequired(
                "refresh_token invalido ou expirado. Integracao precisa ser reconectada."
            )
        return self._handle_token_response(response)

    def _handle_token_response(self, response: httpx.Response) -> ContaAzulTokenSet:
        if response.status_code >= 400:
            raise AuthError(f"Falha ao obter token (status {response.status_code}): {response.text}")
        payload = response.json()
        return ContaAzulTokenSet(
            access_token=payload["access_token"],
            refresh_token=payload["refresh_token"],
            expires_in=payload.get("expires_in", 3600),
            obtained_at=time.time(),
            token_type=payload.get("token_type", "Bearer"),
            scope=payload.get("scope"),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd API/app && python -m pytest tests/test_conta_azul_auth_service.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add API/app/services/conta_azul/auth_service.py API/app/tests/test_conta_azul_auth_service.py
git commit -m "feat: port Conta Azul OAuth2 auth service into the API"
```

---

### Task 6: `IntegracoesRepository`

**Files:**
- Create: `API/app/repositories/conta_azul/__init__.py`
- Create: `API/app/repositories/conta_azul/integracoes_repository.py`
- Test: `API/app/tests/test_conta_azul_integracoes_repository.py`

**Interfaces:**
- Consumes: `conta_azul.integracoes` table (Task 2).
- Produces: `IntegracoesRepository` with `get_by_empresa(empresa_id) -> dict | None`, `iniciar_autorizacao(*, empresa_id, state, expira_em)`, `validar_state(empresa_id, state) -> dict | None`, `salvar_tokens(*, empresa_id, access_token_encrypted, refresh_token_encrypted, token_expira_em)`, `marcar_desconectada(empresa_id)`, `marcar_expirada(empresa_id)`, `marcar_erro(empresa_id, erro_mensagem)`. Used by Task 8 (sync service) and Task 11 (routes).

This task requires a disposable Postgres test database. If `PLATAFORMA_FISCAL_TEST_DATABASE_URL` isn't set in your shell, the tests will `pytest.skip` (existing repo convention via the `migrated_db` fixture in `conftest.py`) — implement the repository anyway so later tasks can import it.

- [ ] **Step 1: Write the failing tests**

Create `API/app/tests/test_conta_azul_integracoes_repository.py`:

```python
from datetime import datetime, timedelta, timezone

import pytest


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


def test_get_by_empresa_sem_integracao_retorna_none(migrated_db, empresa_id):
    from app.repositories.conta_azul.integracoes_repository import IntegracoesRepository

    assert IntegracoesRepository().get_by_empresa(empresa_id) is None


def test_iniciar_autorizacao_e_validar_state(migrated_db, empresa_id):
    from app.repositories.conta_azul.integracoes_repository import IntegracoesRepository

    repo = IntegracoesRepository()
    expira_em = datetime.now(timezone.utc) + timedelta(minutes=10)
    repo.iniciar_autorizacao(empresa_id=empresa_id, state="state-123", expira_em=expira_em)

    integracao = repo.get_by_empresa(empresa_id)
    assert integracao["status"] == "PENDENTE"
    assert integracao["oauth_state"] == "state-123"

    assert repo.validar_state(empresa_id, "state-123") is not None
    assert repo.validar_state(empresa_id, "state-errado") is None


def test_salvar_tokens_marca_ativa_e_limpa_state(migrated_db, empresa_id):
    from app.repositories.conta_azul.integracoes_repository import IntegracoesRepository

    repo = IntegracoesRepository()
    repo.iniciar_autorizacao(
        empresa_id=empresa_id, state="state-123", expira_em=datetime.now(timezone.utc) + timedelta(minutes=10)
    )

    token_expira_em = datetime.now(timezone.utc) + timedelta(hours=1)
    repo.salvar_tokens(
        empresa_id=empresa_id,
        access_token_encrypted="access-cifrado",
        refresh_token_encrypted="refresh-cifrado",
        token_expira_em=token_expira_em,
    )

    integracao = repo.get_by_empresa(empresa_id)
    assert integracao["status"] == "ATIVA"
    assert integracao["access_token_encrypted"] == "access-cifrado"
    assert integracao["oauth_state"] is None


def test_marcar_desconectada_limpa_tokens(migrated_db, empresa_id):
    from app.repositories.conta_azul.integracoes_repository import IntegracoesRepository

    repo = IntegracoesRepository()
    repo.iniciar_autorizacao(
        empresa_id=empresa_id, state="state-123", expira_em=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    repo.salvar_tokens(
        empresa_id=empresa_id,
        access_token_encrypted="access-cifrado",
        refresh_token_encrypted="refresh-cifrado",
        token_expira_em=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    repo.marcar_desconectada(empresa_id)

    integracao = repo.get_by_empresa(empresa_id)
    assert integracao["status"] == "DESCONECTADA"
    assert integracao["access_token_encrypted"] is None


def test_marcar_expirada_e_marcar_erro(migrated_db, empresa_id):
    from app.repositories.conta_azul.integracoes_repository import IntegracoesRepository

    repo = IntegracoesRepository()
    repo.iniciar_autorizacao(
        empresa_id=empresa_id, state="state-123", expira_em=datetime.now(timezone.utc) + timedelta(minutes=10)
    )

    repo.marcar_expirada(empresa_id)
    assert repo.get_by_empresa(empresa_id)["status"] == "EXPIRADA"

    repo.marcar_erro(empresa_id, "Falha ao autenticar")
    integracao = repo.get_by_empresa(empresa_id)
    assert integracao["status"] == "ERRO"
    assert integracao["erro_mensagem"] == "Falha ao autenticar"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd API/app && python -m pytest tests/test_conta_azul_integracoes_repository.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.repositories.conta_azul'` (or `SKIPPED` if `PLATAFORMA_FISCAL_TEST_DATABASE_URL` is unset — in that case, still do Step 3 so the module exists for later tasks, then confirm with `python -c "import app.repositories.conta_azul.integracoes_repository"`)

- [ ] **Step 3: Implement**

Create `API/app/repositories/conta_azul/__init__.py` (empty file).

Create `API/app/repositories/conta_azul/integracoes_repository.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


class IntegracoesRepository:
    def __init__(self) -> None:
        self.config = carregar_config_postgres()

    def _connect(self):
        last_error: Exception | None = None
        for options in opcoes_conexao_postgres(self.config):
            try:
                return psycopg.connect(**options, row_factory=dict_row)
            except psycopg.Error as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("Configuracao PostgreSQL invalida.")

    def get_by_empresa(self, empresa_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM conta_azul.integracoes WHERE empresa_id = %s",
                    (empresa_id,),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def iniciar_autorizacao(self, *, empresa_id: int, state: str, expira_em: datetime) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conta_azul.integracoes (empresa_id, status, oauth_state, oauth_state_expira_em)
                    VALUES (%s, 'PENDENTE', %s, %s)
                    ON CONFLICT (empresa_id) DO UPDATE
                    SET status = 'PENDENTE',
                        oauth_state = EXCLUDED.oauth_state,
                        oauth_state_expira_em = EXCLUDED.oauth_state_expira_em,
                        atualizado_em = NOW()
                    """,
                    (empresa_id, state, expira_em),
                )
            conn.commit()

    def validar_state(self, empresa_id: int, state: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM conta_azul.integracoes
                    WHERE empresa_id = %s
                      AND status = 'PENDENTE'
                      AND oauth_state = %s
                      AND oauth_state_expira_em > NOW()
                    """,
                    (empresa_id, state),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def salvar_tokens(
        self,
        *,
        empresa_id: int,
        access_token_encrypted: str,
        refresh_token_encrypted: str,
        token_expira_em: datetime,
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE conta_azul.integracoes
                    SET status = 'ATIVA',
                        access_token_encrypted = %s,
                        refresh_token_encrypted = %s,
                        token_expira_em = %s,
                        oauth_state = NULL,
                        oauth_state_expira_em = NULL,
                        erro_mensagem = NULL,
                        atualizado_em = NOW()
                    WHERE empresa_id = %s
                    """,
                    (access_token_encrypted, refresh_token_encrypted, token_expira_em, empresa_id),
                )
            conn.commit()

    def marcar_desconectada(self, empresa_id: int) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE conta_azul.integracoes
                    SET status = 'DESCONECTADA',
                        access_token_encrypted = NULL,
                        refresh_token_encrypted = NULL,
                        token_expira_em = NULL,
                        atualizado_em = NOW()
                    WHERE empresa_id = %s
                    """,
                    (empresa_id,),
                )
            conn.commit()

    def marcar_expirada(self, empresa_id: int) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE conta_azul.integracoes SET status = 'EXPIRADA', atualizado_em = NOW() WHERE empresa_id = %s",
                    (empresa_id,),
                )
            conn.commit()

    def marcar_erro(self, empresa_id: int, erro_mensagem: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE conta_azul.integracoes
                    SET status = 'ERRO', erro_mensagem = %s, atualizado_em = NOW()
                    WHERE empresa_id = %s
                    """,
                    (erro_mensagem, empresa_id),
                )
            conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass (or skip cleanly)**

Run: `cd API/app && python -m pytest tests/test_conta_azul_integracoes_repository.py -v`
Expected: PASS if `PLATAFORMA_FISCAL_TEST_DATABASE_URL` is set, otherwise `SKIPPED` (not FAILED/ERROR)

- [ ] **Step 5: Commit**

```bash
git add API/app/repositories/conta_azul/__init__.py API/app/repositories/conta_azul/integracoes_repository.py API/app/tests/test_conta_azul_integracoes_repository.py
git commit -m "feat: add IntegracoesRepository for Conta Azul integration state"
```

---

### Task 7: `SincronizacoesRepository`

**Files:**
- Create: `API/app/repositories/conta_azul/sincronizacoes_repository.py`
- Test: `API/app/tests/test_conta_azul_sincronizacoes_repository.py`

**Interfaces:**
- Consumes: `conta_azul.sincronizacoes` table (Task 2), `IntegracoesRepository` (Task 6, for the test fixture only).
- Produces: `ENTIDADES_SINCRONIZADAS: list[str]` (`["pessoas", "produtos", "categorias", "vendas", "financeiro"]`), `SincronizacoesRepository` with `iniciar_run(*, integracao_id, run_id, entidades)`, `atualizar_entidade(*, run_id, entidade, status, registros_processados=None, erro_mensagem=None)`, `obter_ultimo_run(integracao_id) -> dict | None` (shape: `{"run_id", "ultima_sync_em", "status", "entidades": [{"entidade", "registros_processados", "status", "fim_em", "erro"}]}`). Used by Task 8 (sync service) and Task 11 (routes).

- [ ] **Step 1: Write the failing tests**

Create `API/app/tests/test_conta_azul_sincronizacoes_repository.py`:

```python
import pytest


@pytest.fixture
def integracao_id(migrated_db) -> int:
    with migrated_db.cursor() as cur:
        cur.execute(
            "INSERT INTO public.empresas (cnpj, nome) VALUES (%s, %s) RETURNING id",
            ("98765432000199", "Empresa Sync Teste"),
        )
        empresa_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO conta_azul.integracoes (empresa_id, status) VALUES (%s, 'ATIVA') RETURNING id",
            (empresa_id,),
        )
        new_id = cur.fetchone()[0]
    migrated_db.commit()
    return new_id


def test_obter_ultimo_run_sem_execucoes_retorna_none(migrated_db, integracao_id):
    from app.repositories.conta_azul.sincronizacoes_repository import SincronizacoesRepository

    assert SincronizacoesRepository().obter_ultimo_run(integracao_id) is None


def test_iniciar_run_cria_uma_linha_por_entidade_em_processamento(migrated_db, integracao_id):
    from app.repositories.conta_azul.sincronizacoes_repository import (
        ENTIDADES_SINCRONIZADAS,
        SincronizacoesRepository,
    )

    repo = SincronizacoesRepository()
    repo.iniciar_run(integracao_id=integracao_id, run_id="11111111-1111-1111-1111-111111111111", entidades=ENTIDADES_SINCRONIZADAS)

    run = repo.obter_ultimo_run(integracao_id)
    assert run["status"] == "EM_PROCESSAMENTO"
    assert {item["entidade"] for item in run["entidades"]} == set(ENTIDADES_SINCRONIZADAS)
    assert all(item["status"] == "EM_PROCESSAMENTO" for item in run["entidades"])


def test_atualizar_entidade_sucesso_e_erro_calcula_status_geral(migrated_db, integracao_id):
    from app.repositories.conta_azul.sincronizacoes_repository import (
        ENTIDADES_SINCRONIZADAS,
        SincronizacoesRepository,
    )

    repo = SincronizacoesRepository()
    run_id = "22222222-2222-2222-2222-222222222222"
    repo.iniciar_run(integracao_id=integracao_id, run_id=run_id, entidades=ENTIDADES_SINCRONIZADAS)

    for entidade in ENTIDADES_SINCRONIZADAS:
        if entidade == "financeiro":
            repo.atualizar_entidade(run_id=run_id, entidade=entidade, status="ERRO", erro_mensagem="Rate limit atingido")
        else:
            repo.atualizar_entidade(run_id=run_id, entidade=entidade, status="SUCESSO", registros_processados=10)

    run = repo.obter_ultimo_run(integracao_id)
    assert run["status"] == "ERRO"
    financeiro = next(item for item in run["entidades"] if item["entidade"] == "financeiro")
    assert financeiro["erro"] == "Rate limit atingido"
    pessoas = next(item for item in run["entidades"] if item["entidade"] == "pessoas")
    assert pessoas["registros_processados"] == 10
    assert pessoas["fim_em"] is not None


def test_obter_ultimo_run_retorna_o_mais_recente(migrated_db, integracao_id):
    from app.repositories.conta_azul.sincronizacoes_repository import (
        ENTIDADES_SINCRONIZADAS,
        SincronizacoesRepository,
    )

    repo = SincronizacoesRepository()
    repo.iniciar_run(integracao_id=integracao_id, run_id="33333333-3333-3333-3333-333333333333", entidades=ENTIDADES_SINCRONIZADAS)
    repo.iniciar_run(integracao_id=integracao_id, run_id="44444444-4444-4444-4444-444444444444", entidades=ENTIDADES_SINCRONIZADAS)

    run = repo.obter_ultimo_run(integracao_id)
    assert run["run_id"] == "44444444-4444-4444-4444-444444444444"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd API/app && python -m pytest tests/test_conta_azul_sincronizacoes_repository.py -v`
Expected: FAIL with `ModuleNotFoundError` (or `SKIPPED` if no test DB configured)

- [ ] **Step 3: Implement**

Create `API/app/repositories/conta_azul/sincronizacoes_repository.py`:

```python
from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres

ENTIDADES_SINCRONIZADAS = ["pessoas", "produtos", "categorias", "vendas", "financeiro"]

_STATUS_PRIORIDADE = {"ERRO": 3, "SUCESSO_PARCIAL": 2, "EM_PROCESSAMENTO": 1, "SUCESSO": 0}


class SincronizacoesRepository:
    def __init__(self) -> None:
        self.config = carregar_config_postgres()

    def _connect(self):
        last_error: Exception | None = None
        for options in opcoes_conexao_postgres(self.config):
            try:
                return psycopg.connect(**options, row_factory=dict_row)
            except psycopg.Error as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("Configuracao PostgreSQL invalida.")

    def iniciar_run(self, *, integracao_id: int, run_id: str, entidades: list[str]) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                for entidade in entidades:
                    cur.execute(
                        """
                        INSERT INTO conta_azul.sincronizacoes (integracao_id, run_id, entidade, status)
                        VALUES (%s, %s, %s, 'EM_PROCESSAMENTO')
                        """,
                        (integracao_id, run_id, entidade),
                    )
            conn.commit()

    def atualizar_entidade(
        self,
        *,
        run_id: str,
        entidade: str,
        status: str,
        registros_processados: int | None = None,
        erro_mensagem: str | None = None,
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE conta_azul.sincronizacoes
                    SET status = %s,
                        registros_processados = %s,
                        erro_mensagem = %s,
                        fim_em = NOW()
                    WHERE run_id = %s AND entidade = %s
                    """,
                    (status, registros_processados, erro_mensagem, run_id, entidade),
                )
            conn.commit()

    def obter_ultimo_run(self, integracao_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT run_id FROM conta_azul.sincronizacoes
                    WHERE integracao_id = %s
                    ORDER BY iniciado_em DESC
                    LIMIT 1
                    """,
                    (integracao_id,),
                )
                ultimo = cur.fetchone()
                if not ultimo:
                    return None

                cur.execute(
                    """
                    SELECT entidade, status, registros_processados, erro_mensagem, fim_em
                    FROM conta_azul.sincronizacoes
                    WHERE run_id = %s
                    ORDER BY entidade
                    """,
                    (ultimo["run_id"],),
                )
                linhas = [dict(row) for row in cur.fetchall()]

        entidades = [
            {
                "entidade": linha["entidade"],
                "registros_processados": linha["registros_processados"],
                "status": linha["status"],
                "fim_em": linha["fim_em"],
                "erro": linha["erro_mensagem"],
            }
            for linha in linhas
        ]
        fins = [linha["fim_em"] for linha in linhas if linha["fim_em"]]
        status_geral = max((linha["status"] for linha in linhas), key=lambda s: _STATUS_PRIORIDADE.get(s, 0))

        return {
            "run_id": str(ultimo["run_id"]),
            "ultima_sync_em": max(fins) if fins else None,
            "status": status_geral,
            "entidades": entidades,
        }
```

- [ ] **Step 4: Run tests to verify they pass (or skip cleanly)**

Run: `cd API/app && python -m pytest tests/test_conta_azul_sincronizacoes_repository.py -v`
Expected: PASS if `PLATAFORMA_FISCAL_TEST_DATABASE_URL` is set, otherwise `SKIPPED`

- [ ] **Step 5: Commit**

```bash
git add API/app/repositories/conta_azul/sincronizacoes_repository.py API/app/tests/test_conta_azul_sincronizacoes_repository.py
git commit -m "feat: add SincronizacoesRepository for Conta Azul sync runs"
```

---

### Task 8: `SyncService`

**Files:**
- Create: `API/app/services/conta_azul/sync_service.py`
- Test: `API/app/tests/test_conta_azul_sync_service.py`

**Interfaces:**
- Consumes: `IntegracoesRepository` (Task 6), `SincronizacoesRepository` + `ENTIDADES_SINCRONIZADAS` (Task 7), `ContaAzulAuthService` + `ReauthorizationRequired` (Task 5), `ContaAzulClient` + `ApiError`/`AuthError` (Task 4), `encrypt_token`/`decrypt_token` (Task 3).
- Produces: `SyncService(integracoes_repository=None, sincronizacoes_repository=None, auth_service=None)` with `executar(*, empresa_id: int, run_id: str) -> None`. Used by Task 9 (Celery task).

This task is pure logic with all dependencies injectable, so it's fully unit-testable with fakes (no real DB/HTTP needed).

- [ ] **Step 1: Write the failing tests**

Create `API/app/tests/test_conta_azul_sync_service.py`:

```python
from datetime import datetime, timedelta, timezone

import pytest

from app.repositories.conta_azul.sincronizacoes_repository import ENTIDADES_SINCRONIZADAS
from app.services.conta_azul.auth_service import ContaAzulTokenSet, ReauthorizationRequired


class FakeIntegracoesRepository:
    def __init__(self, integracao: dict | None):
        self.integracao = integracao
        self.salvar_tokens_calls = []
        self.marcar_expirada_calls = []

    def get_by_empresa(self, empresa_id):
        return self.integracao

    def salvar_tokens(self, **kwargs):
        self.salvar_tokens_calls.append(kwargs)
        self.integracao = {**self.integracao, **kwargs}

    def marcar_expirada(self, empresa_id):
        self.marcar_expirada_calls.append(empresa_id)


class FakeSincronizacoesRepository:
    def __init__(self):
        self.updates = []

    def atualizar_entidade(self, **kwargs):
        self.updates.append(kwargs)


class FakeAuthService:
    def __init__(self, refresh_result=None, refresh_error=None):
        self.refresh_result = refresh_result
        self.refresh_error = refresh_error
        self.refresh_calls = []

    def refresh_access_token(self, refresh_token):
        self.refresh_calls.append(refresh_token)
        if self.refresh_error:
            raise self.refresh_error
        return self.refresh_result


def _integracao_ativa(**overrides) -> dict:
    base = {
        "empresa_id": 1,
        "access_token_encrypted": "access-cifrado",
        "refresh_token_encrypted": "refresh-cifrado",
        "token_expira_em": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    base.update(overrides)
    return base


def test_executar_sem_integracao_nao_faz_nada(monkeypatch):
    from app.services.conta_azul.sync_service import SyncService

    sincronizacoes_repo = FakeSincronizacoesRepository()
    service = SyncService(
        integracoes_repository=FakeIntegracoesRepository(None),
        sincronizacoes_repository=sincronizacoes_repo,
        auth_service=FakeAuthService(),
    )

    service.executar(empresa_id=1, run_id="run-1")

    assert sincronizacoes_repo.updates == []


def test_executar_com_token_expirado_renova_antes_de_sincronizar(monkeypatch):
    from app.services.conta_azul.sync_service import SyncService

    integracao = _integracao_ativa(token_expira_em=datetime.now(timezone.utc) - timedelta(minutes=1))
    integracoes_repo = FakeIntegracoesRepository(integracao)
    auth_service = FakeAuthService(
        refresh_result=ContaAzulTokenSet(
            access_token="access-novo", refresh_token="refresh-novo", expires_in=3600, obtained_at=0
        )
    )

    class FakeClient:
        def __init__(self, access_token):
            self.access_token = access_token

        def listar_pessoas_todas(self):
            return []

        def listar_produtos_todos(self):
            return []

        def listar_categorias_todas(self):
            return []

        def listar_vendas_todas(self, data_inicio, data_fim):
            return []

        def listar_contas_a_receber_todas(self, data_inicio, data_fim):
            return []

        def listar_contas_a_pagar_todas(self, data_inicio, data_fim):
            return []

    monkeypatch.setattr("app.services.conta_azul.sync_service.ContaAzulClient", FakeClient)
    monkeypatch.setattr("app.services.conta_azul.sync_service.decrypt_token", lambda value: value)
    monkeypatch.setattr("app.services.conta_azul.sync_service.encrypt_token", lambda value: f"cifrado-{value}")

    service = SyncService(
        integracoes_repository=integracoes_repo, sincronizacoes_repository=FakeSincronizacoesRepository(), auth_service=auth_service
    )

    service.executar(empresa_id=1, run_id="run-1")

    assert auth_service.refresh_calls == ["refresh-token-descriptografado"] or auth_service.refresh_calls == ["refresh-cifrado"]
    assert integracoes_repo.salvar_tokens_calls[0]["access_token_encrypted"] == "cifrado-access-novo"


def test_executar_refresh_falho_marca_expirada_e_todas_entidades_erro(monkeypatch):
    from app.services.conta_azul.sync_service import SyncService

    integracao = _integracao_ativa(token_expira_em=datetime.now(timezone.utc) - timedelta(minutes=1))
    integracoes_repo = FakeIntegracoesRepository(integracao)
    sincronizacoes_repo = FakeSincronizacoesRepository()
    auth_service = FakeAuthService(refresh_error=ReauthorizationRequired("expirado"))
    monkeypatch.setattr("app.services.conta_azul.sync_service.decrypt_token", lambda value: value)

    service = SyncService(
        integracoes_repository=integracoes_repo, sincronizacoes_repository=sincronizacoes_repo, auth_service=auth_service
    )

    service.executar(empresa_id=1, run_id="run-1")

    assert integracoes_repo.marcar_expirada_calls == [1]
    assert len(sincronizacoes_repo.updates) == len(ENTIDADES_SINCRONIZADAS)
    assert all(update["status"] == "ERRO" for update in sincronizacoes_repo.updates)


def test_executar_entidade_com_erro_nao_interrompe_as_demais(monkeypatch):
    from app.services.conta_azul.contaazul_client import ApiError
    from app.services.conta_azul.sync_service import SyncService

    integracao = _integracao_ativa()
    sincronizacoes_repo = FakeSincronizacoesRepository()
    monkeypatch.setattr("app.services.conta_azul.sync_service.decrypt_token", lambda value: value)

    class FakeClient:
        def __init__(self, access_token):
            pass

        def listar_pessoas_todas(self):
            return [1, 2, 3]

        def listar_produtos_todos(self):
            raise ApiError(429, "rate limited")

        def listar_categorias_todas(self):
            return [1]

        def listar_vendas_todas(self, data_inicio, data_fim):
            return []

        def listar_contas_a_receber_todas(self, data_inicio, data_fim):
            return []

        def listar_contas_a_pagar_todas(self, data_inicio, data_fim):
            return []

    monkeypatch.setattr("app.services.conta_azul.sync_service.ContaAzulClient", FakeClient)

    service = SyncService(
        integracoes_repository=FakeIntegracoesRepository(integracao),
        sincronizacoes_repository=sincronizacoes_repo,
        auth_service=FakeAuthService(),
    )

    service.executar(empresa_id=1, run_id="run-1")

    assert len(sincronizacoes_repo.updates) == len(ENTIDADES_SINCRONIZADAS)
    produtos_update = next(u for u in sincronizacoes_repo.updates if u["entidade"] == "produtos")
    assert produtos_update["status"] == "ERRO"
    pessoas_update = next(u for u in sincronizacoes_repo.updates if u["entidade"] == "pessoas")
    assert pessoas_update["status"] == "SUCESSO"
    assert pessoas_update["registros_processados"] == 3
```

Note: `test_executar_com_token_expirado_renova_antes_de_sincronizar`'s assertion on `refresh_calls` is deliberately loose (`or`) because it only needs to prove `refresh_access_token` was called with whatever `decrypt_token` returned — the important assertions are the ones after it.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd API/app && python -m pytest tests/test_conta_azul_sync_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.conta_azul.sync_service'`

- [ ] **Step 3: Implement**

Create `API/app/services/conta_azul/sync_service.py`:

```python
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.core.config import (
    get_contaazul_client_id,
    get_contaazul_client_secret,
    get_contaazul_redirect_uri,
)
from app.repositories.conta_azul.integracoes_repository import IntegracoesRepository
from app.repositories.conta_azul.sincronizacoes_repository import (
    ENTIDADES_SINCRONIZADAS,
    SincronizacoesRepository,
)
from app.services.conta_azul.auth_service import ContaAzulAuthService, ReauthorizationRequired
from app.services.conta_azul.contaazul_client import ApiError, AuthError, ContaAzulClient
from app.services.conta_azul.crypto_service import decrypt_token, encrypt_token

SYNC_JANELA_DIAS = 365


class SyncService:
    def __init__(
        self,
        integracoes_repository: IntegracoesRepository | None = None,
        sincronizacoes_repository: SincronizacoesRepository | None = None,
        auth_service: ContaAzulAuthService | None = None,
    ) -> None:
        self.integracoes_repository = integracoes_repository or IntegracoesRepository()
        self.sincronizacoes_repository = sincronizacoes_repository or SincronizacoesRepository()
        self.auth_service = auth_service or ContaAzulAuthService(
            client_id=get_contaazul_client_id(),
            client_secret=get_contaazul_client_secret(),
            redirect_uri=get_contaazul_redirect_uri(),
        )

    def executar(self, *, empresa_id: int, run_id: str) -> None:
        integracao = self.integracoes_repository.get_by_empresa(empresa_id)
        if not integracao:
            return

        try:
            access_token = self._access_token_valido(integracao)
        except ReauthorizationRequired:
            self.integracoes_repository.marcar_expirada(empresa_id)
            for entidade in ENTIDADES_SINCRONIZADAS:
                self.sincronizacoes_repository.atualizar_entidade(
                    run_id=run_id,
                    entidade=entidade,
                    status="ERRO",
                    erro_mensagem="Integração expirada. Reconecte o Conta Azul.",
                )
            return

        client = ContaAzulClient(access_token=access_token)
        data_fim = date.today()
        data_inicio = data_fim - timedelta(days=SYNC_JANELA_DIAS)

        self._sincronizar_entidade(run_id, "pessoas", client.listar_pessoas_todas)
        self._sincronizar_entidade(run_id, "produtos", client.listar_produtos_todos)
        self._sincronizar_entidade(run_id, "categorias", client.listar_categorias_todas)
        self._sincronizar_entidade(run_id, "vendas", lambda: client.listar_vendas_todas(data_inicio, data_fim))
        self._sincronizar_entidade(
            run_id,
            "financeiro",
            lambda: client.listar_contas_a_receber_todas(data_inicio, data_fim)
            + client.listar_contas_a_pagar_todas(data_inicio, data_fim),
        )

    def _access_token_valido(self, integracao: dict) -> str:
        token_expira_em = integracao["token_expira_em"]
        if token_expira_em and token_expira_em > datetime.now(timezone.utc):
            return decrypt_token(integracao["access_token_encrypted"])

        refresh_token = decrypt_token(integracao["refresh_token_encrypted"])
        tokens = self.auth_service.refresh_access_token(refresh_token)
        novo_token_expira_em = datetime.fromtimestamp(tokens.obtained_at + tokens.expires_in, tz=timezone.utc)
        self.integracoes_repository.salvar_tokens(
            empresa_id=integracao["empresa_id"],
            access_token_encrypted=encrypt_token(tokens.access_token),
            refresh_token_encrypted=encrypt_token(tokens.refresh_token),
            token_expira_em=novo_token_expira_em,
        )
        return tokens.access_token

    def _sincronizar_entidade(self, run_id: str, entidade: str, fetch) -> None:
        try:
            registros = fetch()
            self.sincronizacoes_repository.atualizar_entidade(
                run_id=run_id,
                entidade=entidade,
                status="SUCESSO",
                registros_processados=len(registros),
            )
        except (ApiError, AuthError) as exc:
            self.sincronizacoes_repository.atualizar_entidade(
                run_id=run_id,
                entidade=entidade,
                status="ERRO",
                erro_mensagem=str(exc),
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd API/app && python -m pytest tests/test_conta_azul_sync_service.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add API/app/services/conta_azul/sync_service.py API/app/tests/test_conta_azul_sync_service.py
git commit -m "feat: add Conta Azul SyncService orchestrating fetch + persistence"
```

---

### Task 9: Celery task + queue wiring

**Files:**
- Create: `API/app/workers/conta_azul_tasks.py`
- Modify: `API/app/workers/celery_app.py`
- Modify: `docker-compose.yml`
- Test: `API/app/tests/test_conta_azul_task.py`

**Interfaces:**
- Consumes: `SyncService` (Task 8).
- Produces: `sincronizar_conta_azul_task(empresa_id: int, run_id: str) -> dict` (Celery task, queue `conta_azul`). Used by Task 11 (routes).

- [ ] **Step 1: Write the failing test**

Create `API/app/tests/test_conta_azul_task.py`:

```python
def test_sincronizar_conta_azul_task_chama_sync_service(monkeypatch):
    calls = []

    class FakeSyncService:
        def executar(self, *, empresa_id, run_id):
            calls.append((empresa_id, run_id))

    monkeypatch.setattr("app.workers.conta_azul_tasks.SyncService", FakeSyncService)

    from app.workers.conta_azul_tasks import sincronizar_conta_azul_task

    result = sincronizar_conta_azul_task.run(1, "run-1")

    assert result == {"status": "SUCCESS", "run_id": "run-1"}
    assert calls == [(1, "run-1")]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd API/app && python -m pytest tests/test_conta_azul_task.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.workers.conta_azul_tasks'`

- [ ] **Step 3: Add the queue and task include to Celery config**

In `API/app/workers/celery_app.py`, change the `include` list:

```python
        include=[
            "app.workers.nfe_tasks",
            "app.workers.sped_tasks",
            "app.workers.conta_azul_tasks",
        ],
```

And add a queue to `task_queues`:

```python
        task_queues=(
            Queue("default", Exchange("default"), routing_key="default"),
            Queue("nfe", Exchange("nfe"), routing_key="nfe"),
            Queue("sped", Exchange("sped"), routing_key="sped"),
            Queue("conta_azul", Exchange("conta_azul"), routing_key="conta_azul"),
        ),
```

- [ ] **Step 4: Implement the task**

Create `API/app/workers/conta_azul_tasks.py`:

```python
from __future__ import annotations

from app.services.conta_azul.sync_service import SyncService
from app.workers.celery_app import celery_app


@celery_app.task(
    name="sincronizar_conta_azul_task",
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def sincronizar_conta_azul_task(empresa_id: int, run_id: str) -> dict:
    SyncService().executar(empresa_id=empresa_id, run_id=run_id)
    return {"status": "SUCCESS", "run_id": run_id}
```

- [ ] **Step 5: Add a dedicated Celery worker service to docker-compose**

In `docker-compose.yml`, after the `celery-worker-sped` service, add:

```yaml
  celery-worker-conta-azul:
    build:
      context: .
      dockerfile: Dockerfile
    env_file:
      - ./API/app/.env.example
    environment:
      DATABASE_URL: ${DATABASE_URL:-postgresql://postgres:postgres@postgres:5432/plataforma_fiscal}
      POSTGRES_DSN: ${DATABASE_URL:-postgresql://postgres:postgres@postgres:5432/plataforma_fiscal}
      REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}
    command: ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "-Q", "conta_azul"]
    depends_on:
      reference-seed:
        condition: service_completed_successfully
      redis:
        condition: service_healthy
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd API/app && python -m pytest tests/test_conta_azul_task.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add API/app/workers/conta_azul_tasks.py API/app/workers/celery_app.py docker-compose.yml API/app/tests/test_conta_azul_task.py
git commit -m "feat: add sincronizar_conta_azul_task and conta_azul Celery queue"
```

---

### Task 10: Pydantic response schemas

**Files:**
- Create: `API/app/models/conta_azul/__init__.py`
- Create: `API/app/models/conta_azul/schemas.py`

**Interfaces:**
- Produces: `IntegracaoStatusResponse`, `AuthUrlResponse`, `SincronizarResponse`, `EntidadeSincronizacaoResponse`, `SincronizacoesResponse` (all `pydantic.BaseModel`). Used by Task 11 (routes).

This task has no independent runtime behavior to unit-test (pure data shape) — it's exercised end-to-end by Task 11's route tests. No dedicated test file.

- [ ] **Step 1: Implement**

Create `API/app/models/conta_azul/__init__.py` (empty file).

Create `API/app/models/conta_azul/schemas.py`:

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class IntegracaoStatus(StrEnum):
    PENDENTE = "PENDENTE"
    ATIVA = "ATIVA"
    EXPIRADA = "EXPIRADA"
    ERRO = "ERRO"
    DESCONECTADA = "DESCONECTADA"


class SincronizacaoStatus(StrEnum):
    EM_PROCESSAMENTO = "EM_PROCESSAMENTO"
    SUCESSO = "SUCESSO"
    SUCESSO_PARCIAL = "SUCESSO_PARCIAL"
    ERRO = "ERRO"


class IntegracaoStatusResponse(BaseModel):
    status: IntegracaoStatus | None = None
    token_expira_em: datetime | None = None
    erro_mensagem: str | None = None


class AuthUrlResponse(BaseModel):
    auth_url: str


class SincronizarResponse(BaseModel):
    run_id: str


class EntidadeSincronizacaoResponse(BaseModel):
    entidade: str
    registros_processados: int | None = None
    status: SincronizacaoStatus
    fim_em: datetime | None = None
    erro: str | None = None


class SincronizacoesResponse(BaseModel):
    ultima_sync_em: datetime | None = None
    status: SincronizacaoStatus | None = None
    token_expira_em: datetime | None = None
    entidades: list[EntidadeSincronizacaoResponse] = []
```

- [ ] **Step 2: Verify it imports cleanly**

Run: `cd API/app && python -c "from app.models.conta_azul.schemas import IntegracaoStatusResponse, SincronizacoesResponse; print('ok')"`
Expected: prints `ok`

- [ ] **Step 3: Commit**

```bash
git add API/app/models/conta_azul/__init__.py API/app/models/conta_azul/schemas.py
git commit -m "feat: add Conta Azul response schemas"
```

---

### Task 11: Routes + wire into the app

**Files:**
- Create: `API/app/api/conta_azul/__init__.py`
- Create: `API/app/api/conta_azul/routes.py`
- Modify: `API/app/api/routes.py`
- Test: `API/app/tests/test_conta_azul_routes.py`

**Interfaces:**
- Consumes: everything from Tasks 3–10.
- Produces: the 6 HTTP endpoints from the design spec, mounted under `/api`.

- [ ] **Step 1: Write the failing tests**

Create `API/app/tests/test_conta_azul_routes.py`:

```python
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest


class FakeIntegracoesRepository:
    rows: dict[int, dict] = {}

    def get_by_empresa(self, empresa_id):
        return self.rows.get(empresa_id)

    def iniciar_autorizacao(self, *, empresa_id, state, expira_em):
        self.rows[empresa_id] = {
            "id": empresa_id,
            "empresa_id": empresa_id,
            "status": "PENDENTE",
            "oauth_state": state,
            "token_expira_em": None,
            "erro_mensagem": None,
        }

    def marcar_desconectada(self, empresa_id):
        self.rows[empresa_id] = {**self.rows.get(empresa_id, {}), "status": "DESCONECTADA"}


def test_status_sem_integracao_retorna_status_none(client, monkeypatch):
    monkeypatch.setattr("app.api.conta_azul.routes.IntegracoesRepository", FakeIntegracoesRepository)

    response = client.get("/api/empresas/1/integracoes/conta-azul")

    assert response.status_code == 200
    assert response.json()["status"] is None


def test_status_empresa_diferente_retorna_403(client, monkeypatch):
    monkeypatch.setattr("app.api.conta_azul.routes.IntegracoesRepository", FakeIntegracoesRepository)

    response = client.get("/api/empresas/999/integracoes/conta-azul")

    assert response.status_code == 403


def test_auth_url_retorna_url_e_persiste_state(client, monkeypatch):
    FakeIntegracoesRepository.rows = {}
    monkeypatch.setattr("app.api.conta_azul.routes.IntegracoesRepository", FakeIntegracoesRepository)

    response = client.get("/api/empresas/1/integracoes/conta-azul/auth-url")

    assert response.status_code == 200
    assert response.json()["auth_url"].startswith("https://auth.contaazul.com/oauth2/authorize?")
    assert FakeIntegracoesRepository.rows[1]["status"] == "PENDENTE"


def test_desconectar_retorna_204(client, monkeypatch):
    FakeIntegracoesRepository.rows = {1: {"id": 1, "empresa_id": 1, "status": "ATIVA"}}
    monkeypatch.setattr("app.api.conta_azul.routes.IntegracoesRepository", FakeIntegracoesRepository)

    response = client.delete("/api/empresas/1/integracoes/conta-azul")

    assert response.status_code == 204
    assert FakeIntegracoesRepository.rows[1]["status"] == "DESCONECTADA"


def test_sync_sem_integracao_ativa_retorna_409(client, monkeypatch):
    FakeIntegracoesRepository.rows = {}
    monkeypatch.setattr("app.api.conta_azul.routes.IntegracoesRepository", FakeIntegracoesRepository)

    response = client.post("/api/empresas/1/integracoes/conta-azul/sync")

    assert response.status_code == 409


def test_sync_com_integracao_ativa_retorna_202_e_dispara_task(client, monkeypatch):
    FakeIntegracoesRepository.rows = {1: {"id": 42, "empresa_id": 1, "status": "ATIVA"}}
    monkeypatch.setattr("app.api.conta_azul.routes.IntegracoesRepository", FakeIntegracoesRepository)

    class FakeSincronizacoesRepository:
        def iniciar_run(self, **kwargs):
            pass

    monkeypatch.setattr("app.api.conta_azul.routes.SincronizacoesRepository", FakeSincronizacoesRepository)

    dispatched = []

    class FakeTask:
        def apply_async(self, args, queue):
            dispatched.append((args, queue))

    monkeypatch.setattr("app.workers.conta_azul_tasks.sincronizar_conta_azul_task", FakeTask())

    response = client.post("/api/empresas/1/integracoes/conta-azul/sync")

    assert response.status_code == 202
    assert "run_id" in response.json()
    assert dispatched[0][1] == "conta_azul"
    assert dispatched[0][0][0] == 1


def test_sincronizacoes_sem_integracao_retorna_vazio(client, monkeypatch):
    FakeIntegracoesRepository.rows = {}
    monkeypatch.setattr("app.api.conta_azul.routes.IntegracoesRepository", FakeIntegracoesRepository)

    response = client.get("/api/empresas/1/integracoes/conta-azul/sincronizacoes")

    assert response.status_code == 200
    assert response.json()["entidades"] == []


def test_sincronizacoes_com_run_retorna_entidades(client, monkeypatch):
    FakeIntegracoesRepository.rows = {
        1: {"id": 42, "empresa_id": 1, "status": "ATIVA", "token_expira_em": None}
    }
    monkeypatch.setattr("app.api.conta_azul.routes.IntegracoesRepository", FakeIntegracoesRepository)

    class FakeSincronizacoesRepository:
        def obter_ultimo_run(self, integracao_id):
            return {
                "run_id": str(uuid4()),
                "ultima_sync_em": datetime.now(timezone.utc),
                "status": "SUCESSO",
                "entidades": [
                    {"entidade": "pessoas", "registros_processados": 10, "status": "SUCESSO", "fim_em": datetime.now(timezone.utc), "erro": None},
                ],
            }

    monkeypatch.setattr("app.api.conta_azul.routes.SincronizacoesRepository", FakeSincronizacoesRepository)

    response = client.get("/api/empresas/1/integracoes/conta-azul/sincronizacoes")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SUCESSO"
    assert body["entidades"][0]["entidade"] == "pessoas"


def test_callback_state_invalido_retorna_html_erro(client, monkeypatch):
    FakeIntegracoesRepository.rows = {}
    monkeypatch.setattr("app.api.conta_azul.routes.IntegracoesRepository", FakeIntegracoesRepository)

    response = client.get("/api/conta-azul/callback?code=abc&state=invalido")

    assert response.status_code == 200
    assert "conta-azul-oauth" in response.text
    assert "'error'" in response.text


def test_conta_azul_routes_exigem_autenticacao(unauthenticated_client):
    assert unauthenticated_client.get("/api/empresas/1/integracoes/conta-azul").status_code == 401
    assert unauthenticated_client.get("/api/empresas/1/integracoes/conta-azul/auth-url").status_code == 401
    assert unauthenticated_client.delete("/api/empresas/1/integracoes/conta-azul").status_code == 401
    assert unauthenticated_client.post("/api/empresas/1/integracoes/conta-azul/sync").status_code == 401
    assert unauthenticated_client.get("/api/empresas/1/integracoes/conta-azul/sincronizacoes").status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd API/app && python -m pytest tests/test_conta_azul_routes.py -v`
Expected: FAIL with `404 Not Found` (routes don't exist yet) / `ModuleNotFoundError`

- [ ] **Step 3: Implement routes**

Create `API/app/api/conta_azul/__init__.py` (empty file).

Create `API/app/api/conta_azul/routes.py`:

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse

from app.core.config import (
    get_contaazul_client_id,
    get_contaazul_client_secret,
    get_contaazul_redirect_uri,
)
from app.core.security import AuthenticatedUser, get_current_user
from app.models.conta_azul.schemas import (
    AuthUrlResponse,
    IntegracaoStatusResponse,
    SincronizacoesResponse,
    SincronizarResponse,
)
from app.repositories.conta_azul.integracoes_repository import IntegracoesRepository
from app.repositories.conta_azul.sincronizacoes_repository import (
    ENTIDADES_SINCRONIZADAS,
    SincronizacoesRepository,
)
from app.services.conta_azul.auth_service import ContaAzulAuthService
from app.services.conta_azul.crypto_service import encrypt_token

router = APIRouter(prefix="/empresas/{empresa_id}/integracoes/conta-azul", tags=["Conta Azul"])
callback_router = APIRouter(prefix="/conta-azul", tags=["Conta Azul"])

OAUTH_STATE_TTL_MINUTES = 10


def _verificar_empresa(empresa_id: int, current_user: AuthenticatedUser) -> None:
    if empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem acesso a esta empresa.")


def _auth_service() -> ContaAzulAuthService:
    return ContaAzulAuthService(
        client_id=get_contaazul_client_id(),
        client_secret=get_contaazul_client_secret(),
        redirect_uri=get_contaazul_redirect_uri(),
    )


def _popup_response(ok: bool) -> HTMLResponse:
    status_value = "success" if ok else "error"
    html = (
        "<!doctype html><html><body><script>"
        "window.opener && window.opener.postMessage("
        f"{{type: 'conta-azul-oauth', status: '{status_value}'}}, window.location.origin"
        ");"
        "window.close();"
        "</script></body></html>"
    )
    return HTMLResponse(content=html)


@router.get("", response_model=IntegracaoStatusResponse)
def obter_status(empresa_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    _verificar_empresa(empresa_id, current_user)
    integracao = IntegracoesRepository().get_by_empresa(empresa_id)
    if not integracao:
        return IntegracaoStatusResponse(status=None)
    return IntegracaoStatusResponse(
        status=integracao["status"],
        token_expira_em=integracao.get("token_expira_em"),
        erro_mensagem=integracao.get("erro_mensagem"),
    )


@router.get("/auth-url", response_model=AuthUrlResponse)
def gerar_auth_url(empresa_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    _verificar_empresa(empresa_id, current_user)
    auth_url, state = _auth_service().build_authorization_url()
    IntegracoesRepository().iniciar_autorizacao(
        empresa_id=empresa_id,
        state=state,
        expira_em=datetime.now(timezone.utc) + timedelta(minutes=OAUTH_STATE_TTL_MINUTES),
    )
    return AuthUrlResponse(auth_url=auth_url)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def desconectar(empresa_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    _verificar_empresa(empresa_id, current_user)
    IntegracoesRepository().marcar_desconectada(empresa_id)


@router.post("/sync", response_model=SincronizarResponse, status_code=status.HTTP_202_ACCEPTED)
def sincronizar(empresa_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    _verificar_empresa(empresa_id, current_user)
    integracao = IntegracoesRepository().get_by_empresa(empresa_id)
    if not integracao or integracao["status"] not in ("ATIVA", "EXPIRADA"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Integração Conta Azul não está ativa.")

    run_id = str(uuid4())
    SincronizacoesRepository().iniciar_run(
        integracao_id=integracao["id"], run_id=run_id, entidades=ENTIDADES_SINCRONIZADAS
    )

    from app.workers.conta_azul_tasks import sincronizar_conta_azul_task

    sincronizar_conta_azul_task.apply_async(args=[empresa_id, run_id], queue="conta_azul")

    return SincronizarResponse(run_id=run_id)


@router.get("/sincronizacoes", response_model=SincronizacoesResponse)
def obter_sincronizacoes(empresa_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    _verificar_empresa(empresa_id, current_user)
    integracao = IntegracoesRepository().get_by_empresa(empresa_id)
    if not integracao:
        return SincronizacoesResponse()

    run = SincronizacoesRepository().obter_ultimo_run(integracao["id"])
    if not run:
        return SincronizacoesResponse(token_expira_em=integracao.get("token_expira_em"))

    return SincronizacoesResponse(
        ultima_sync_em=run["ultima_sync_em"],
        status=run["status"],
        token_expira_em=integracao.get("token_expira_em"),
        entidades=run["entidades"],
    )


@callback_router.get("/callback")
def callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    if error or not code or not state:
        return _popup_response(ok=False)

    integracoes_repo = IntegracoesRepository()
    pendente = integracoes_repo.validar_state(current_user.empresa_id, state)
    if not pendente:
        return _popup_response(ok=False)

    try:
        tokens = _auth_service().exchange_code_for_token(code)
    except Exception:
        integracoes_repo.marcar_erro(current_user.empresa_id, "Falha ao trocar code por token.")
        return _popup_response(ok=False)

    token_expira_em = datetime.fromtimestamp(tokens.obtained_at + tokens.expires_in, tz=timezone.utc)
    integracoes_repo.salvar_tokens(
        empresa_id=current_user.empresa_id,
        access_token_encrypted=encrypt_token(tokens.access_token),
        refresh_token_encrypted=encrypt_token(tokens.refresh_token),
        token_expira_em=token_expira_em,
    )
    return _popup_response(ok=True)
```

- [ ] **Step 4: Wire the router into the app**

In `API/app/api/routes.py`, add the import and includes:

```python
from app.api.conta_azul.routes import callback_router as conta_azul_callback_router
from app.api.conta_azul.routes import router as conta_azul_router
```

and:

```python
router.include_router(conta_azul_router)
router.include_router(conta_azul_callback_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd API/app && python -m pytest tests/test_conta_azul_routes.py -v`
Expected: PASS (10 tests)

- [ ] **Step 6: Run the full backend test suite**

Run: `cd API/app && python -m pytest -v`
Expected: PASS (no regressions in existing tests)

- [ ] **Step 7: Commit**

```bash
git add API/app/api/conta_azul/__init__.py API/app/api/conta_azul/routes.py API/app/api/routes.py API/app/tests/test_conta_azul_routes.py
git commit -m "feat: add Conta Azul integration routes"
```

---

### Task 12: Frontend API client

**Files:**
- Create: `Painel/src/services/contaAzul.api.ts`
- Test: `Painel/src/services/contaAzul.api.test.ts`

**Interfaces:**
- Consumes: `API_BASE_URL`, `apiFetch` from `@/services/api`.
- Produces: `fetchIntegracaoStatus(empresaId)`, `fetchAuthUrl(empresaId)`, `desconectarIntegracao(empresaId)`, `sincronizarAgora(empresaId)`, `fetchSincronizacoes(empresaId)`, plus types `IntegracaoStatusResponse`, `EntidadeSincronizacao`, `SincronizacoesResponse`. Used by Task 13 (hook).

- [ ] **Step 1: Write the failing tests**

Create `Painel/src/services/contaAzul.api.test.ts`:

```typescript
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { API_BASE_URL } from './api';
import {
  desconectarIntegracao,
  fetchAuthUrl,
  fetchIntegracaoStatus,
  fetchSincronizacoes,
  sincronizarAgora,
} from './contaAzul.api';

vi.mock('./api', async () => {
  const actual = await vi.importActual<typeof import('./api')>('./api');
  return { ...actual, apiFetch: vi.fn() };
});

import { apiFetch } from './api';

const mockedApiFetch = vi.mocked(apiFetch);

describe('contaAzul.api', () => {
  beforeEach(() => {
    mockedApiFetch.mockReset();
  });

  it('fetchIntegracaoStatus busca o endpoint correto', async () => {
    mockedApiFetch.mockResolvedValue(
      new Response(JSON.stringify({ status: null, token_expira_em: null, erro_mensagem: null }), { status: 200 }),
    );

    const result = await fetchIntegracaoStatus(1);

    expect(mockedApiFetch).toHaveBeenCalledWith(`${API_BASE_URL}/empresas/1/integracoes/conta-azul`);
    expect(result.status).toBeNull();
  });

  it('fetchAuthUrl retorna a auth_url', async () => {
    mockedApiFetch.mockResolvedValue(new Response(JSON.stringify({ auth_url: 'https://auth.contaazul.com/x' }), { status: 200 }));

    const url = await fetchAuthUrl(1);

    expect(mockedApiFetch).toHaveBeenCalledWith(`${API_BASE_URL}/empresas/1/integracoes/conta-azul/auth-url`);
    expect(url).toBe('https://auth.contaazul.com/x');
  });

  it('desconectarIntegracao chama DELETE', async () => {
    mockedApiFetch.mockResolvedValue(new Response(null, { status: 204 }));

    await desconectarIntegracao(1);

    expect(mockedApiFetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/empresas/1/integracoes/conta-azul`,
      expect.objectContaining({ method: 'DELETE' }),
    );
  });

  it('sincronizarAgora chama POST e retorna run_id', async () => {
    mockedApiFetch.mockResolvedValue(new Response(JSON.stringify({ run_id: 'run-1' }), { status: 202 }));

    const result = await sincronizarAgora(1);

    expect(mockedApiFetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/empresas/1/integracoes/conta-azul/sync`,
      expect.objectContaining({ method: 'POST' }),
    );
    expect(result.run_id).toBe('run-1');
  });

  it('fetchSincronizacoes propaga erro amigavel quando resposta falha', async () => {
    mockedApiFetch.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Integração não encontrada.' }), { status: 404 }),
    );

    await expect(fetchSincronizacoes(1)).rejects.toThrow('Integração não encontrada.');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd Painel && npx vitest run src/services/contaAzul.api.test.ts`
Expected: FAIL with a module-not-found error for `./contaAzul.api`

- [ ] **Step 3: Implement**

Create `Painel/src/services/contaAzul.api.ts`:

```typescript
/**
 * Endpoints consumidos pela integração Conta Azul (Painel/src/features/configuracoes).
 *
 * - GET    /empresas/:id/integracoes/conta-azul               -> status atual da integração
 * - GET    /empresas/:id/integracoes/conta-azul/auth-url       -> { auth_url } para abrir o popup OAuth2
 * - DELETE /empresas/:id/integracoes/conta-azul                -> desconecta (sem payload)
 * - POST   /empresas/:id/integracoes/conta-azul/sync           -> dispara sincronização, retorna { run_id }
 * - GET    /empresas/:id/integracoes/conta-azul/sincronizacoes -> status do último run (polling)
 */
import { API_BASE_URL, apiFetch } from './api';

export type IntegracaoStatus = 'ATIVA' | 'EXPIRADA' | 'ERRO' | 'DESCONECTADA' | null;
export type EntidadeStatus = 'EM_PROCESSAMENTO' | 'SUCESSO' | 'SUCESSO_PARCIAL' | 'ERRO';

export interface IntegracaoStatusResponse {
  status: IntegracaoStatus;
  token_expira_em: string | null;
  erro_mensagem: string | null;
}

export interface EntidadeSincronizacao {
  entidade: string;
  registros_processados: number | null;
  status: EntidadeStatus;
  fim_em: string | null;
  erro?: string | null;
}

export interface SincronizacoesResponse {
  ultima_sync_em: string | null;
  status: EntidadeStatus | null;
  token_expira_em: string | null;
  entidades: EntidadeSincronizacao[];
}

interface ApiErrorDetail {
  detail?: string | { msg?: string }[];
}

const extractErrorMessage = (errorData: ApiErrorDetail | null, fallback: string) => {
  if (!errorData?.detail) return fallback;
  if (typeof errorData.detail === 'string') return errorData.detail;
  return errorData.detail[0]?.msg || fallback;
};

const baseUrl = (empresaId: number) => `${API_BASE_URL}/empresas/${empresaId}/integracoes/conta-azul`;

export const fetchIntegracaoStatus = async (empresaId: number): Promise<IntegracaoStatusResponse> => {
  const response = await apiFetch(baseUrl(empresaId));
  if (!response.ok) {
    const errorData = (await response.json().catch(() => null)) as ApiErrorDetail | null;
    throw new Error(extractErrorMessage(errorData, 'Não foi possível carregar o status da integração.'));
  }
  return response.json();
};

export const fetchAuthUrl = async (empresaId: number): Promise<string> => {
  const response = await apiFetch(`${baseUrl(empresaId)}/auth-url`);
  if (!response.ok) {
    const errorData = (await response.json().catch(() => null)) as ApiErrorDetail | null;
    throw new Error(extractErrorMessage(errorData, 'Não foi possível iniciar a conexão com o Conta Azul.'));
  }
  const data = (await response.json()) as { auth_url: string };
  return data.auth_url;
};

export const desconectarIntegracao = async (empresaId: number): Promise<void> => {
  const response = await apiFetch(baseUrl(empresaId), { method: 'DELETE' });
  if (!response.ok) {
    const errorData = (await response.json().catch(() => null)) as ApiErrorDetail | null;
    throw new Error(extractErrorMessage(errorData, 'Não foi possível desconectar o Conta Azul.'));
  }
};

export const sincronizarAgora = async (empresaId: number): Promise<{ run_id: string }> => {
  const response = await apiFetch(`${baseUrl(empresaId)}/sync`, { method: 'POST' });
  if (!response.ok) {
    const errorData = (await response.json().catch(() => null)) as ApiErrorDetail | null;
    throw new Error(extractErrorMessage(errorData, 'Não foi possível iniciar a sincronização.'));
  }
  return response.json();
};

export const fetchSincronizacoes = async (empresaId: number): Promise<SincronizacoesResponse> => {
  const response = await apiFetch(`${baseUrl(empresaId)}/sincronizacoes`);
  if (!response.ok) {
    const errorData = (await response.json().catch(() => null)) as ApiErrorDetail | null;
    throw new Error(extractErrorMessage(errorData, 'Não foi possível carregar os dados de sincronização.'));
  }
  return response.json();
};
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd Painel && npx vitest run src/services/contaAzul.api.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add Painel/src/services/contaAzul.api.ts Painel/src/services/contaAzul.api.test.ts
git commit -m "feat: add Conta Azul frontend API client"
```

---

### Task 13: `useContaAzulIntegracao` hook

**Files:**
- Create: `Painel/src/features/configuracoes/hooks/useContaAzulIntegracao.ts`
- Test: `Painel/src/features/configuracoes/hooks/useContaAzulIntegracao.test.ts`

**Interfaces:**
- Consumes: everything exported from `@/services/contaAzul.api` (Task 12), `useToast` from `@/hooks/use-toast`.
- Produces: `useContaAzulIntegracao(empresaId: number)` returning `{ status, sincronizacoes, loading, error, sincronizando, conectar, desconectar, sincronizarAgora, refresh }`. Used by Task 14 (components).

- [ ] **Step 1: Write the failing tests**

Create `Painel/src/features/configuracoes/hooks/useContaAzulIntegracao.test.ts`:

```typescript
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  fetchIntegracaoStatus: vi.fn(),
  fetchSincronizacoes: vi.fn(),
  fetchAuthUrl: vi.fn(),
  desconectarIntegracao: vi.fn(),
  sincronizarAgora: vi.fn(),
}));

vi.mock('@/services/contaAzul.api', () => mocks);
vi.mock('@/hooks/use-toast', () => ({ useToast: () => ({ toast: vi.fn() }) }));

import { useContaAzulIntegracao } from './useContaAzulIntegracao';

describe('useContaAzulIntegracao', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mocks.fetchIntegracaoStatus.mockReset();
    mocks.fetchSincronizacoes.mockReset();
    mocks.fetchAuthUrl.mockReset();
    mocks.desconectarIntegracao.mockReset();
    mocks.sincronizarAgora.mockReset();
  });

  it('estado inicial sem integração', async () => {
    mocks.fetchIntegracaoStatus.mockResolvedValue({ status: null, token_expira_em: null, erro_mensagem: null });

    const { result } = renderHook(() => useContaAzulIntegracao(1));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.status?.status).toBeNull();
    expect(mocks.fetchSincronizacoes).not.toHaveBeenCalled();
  });

  it('transição para ATIVA após conectar dispara carga de sincronizações', async () => {
    mocks.fetchIntegracaoStatus
      .mockResolvedValueOnce({ status: null, token_expira_em: null, erro_mensagem: null })
      .mockResolvedValueOnce({ status: 'ATIVA', token_expira_em: '2026-07-28T15:00:00Z', erro_mensagem: null });
    mocks.fetchSincronizacoes.mockResolvedValue({
      ultima_sync_em: null,
      status: null,
      token_expira_em: null,
      entidades: [],
    });

    const { result } = renderHook(() => useContaAzulIntegracao(1));
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.status?.status).toBe('ATIVA');
    expect(mocks.fetchSincronizacoes).toHaveBeenCalled();
  });

  it('faz polling durante sincronização até nenhuma entidade estar EM_PROCESSAMENTO', async () => {
    mocks.fetchIntegracaoStatus.mockResolvedValue({ status: 'ATIVA', token_expira_em: null, erro_mensagem: null });
    mocks.fetchSincronizacoes
      .mockResolvedValueOnce({
        ultima_sync_em: null,
        status: 'EM_PROCESSAMENTO',
        token_expira_em: null,
        entidades: [{ entidade: 'pessoas', status: 'EM_PROCESSAMENTO', registros_processados: null, fim_em: null }],
      })
      .mockResolvedValueOnce({
        ultima_sync_em: '2026-07-28T14:00:00Z',
        status: 'SUCESSO',
        token_expira_em: null,
        entidades: [{ entidade: 'pessoas', status: 'SUCESSO', registros_processados: 10, fim_em: '2026-07-28T14:00:00Z' }],
      });
    mocks.sincronizarAgora.mockResolvedValue({ run_id: 'run-1' });

    const { result } = renderHook(() => useContaAzulIntegracao(1));
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.sincronizarAgora();
    });
    expect(result.current.sincronizando).toBe(true);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    expect(result.current.sincronizando).toBe(false);
    expect(mocks.fetchSincronizacoes).toHaveBeenCalledTimes(2);
  });

  it('limpa o polling ao desmontar', async () => {
    mocks.fetchIntegracaoStatus.mockResolvedValue({ status: 'ATIVA', token_expira_em: null, erro_mensagem: null });
    mocks.fetchSincronizacoes.mockResolvedValue({ ultima_sync_em: null, status: null, token_expira_em: null, entidades: [] });
    mocks.sincronizarAgora.mockResolvedValue({ run_id: 'run-1' });

    const clearIntervalSpy = vi.spyOn(global, 'clearInterval');
    const { result, unmount } = renderHook(() => useContaAzulIntegracao(1));
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.sincronizarAgora();
    });

    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd Painel && npx vitest run src/features/configuracoes/hooks/useContaAzulIntegracao.test.ts`
Expected: FAIL with a module-not-found error for `./useContaAzulIntegracao`

- [ ] **Step 3: Implement**

Create `Painel/src/features/configuracoes/hooks/useContaAzulIntegracao.ts`:

```typescript
import { useCallback, useEffect, useRef, useState } from 'react';

import { useToast } from '@/hooks/use-toast';
import {
  desconectarIntegracao,
  fetchAuthUrl,
  fetchIntegracaoStatus,
  fetchSincronizacoes,
  sincronizarAgora as sincronizarAgoraApi,
  type IntegracaoStatusResponse,
  type SincronizacoesResponse,
} from '@/services/contaAzul.api';

const POLLING_INTERVAL_MS = 3000;
const POLLING_MAX_ATTEMPTS = 60;

export interface ContaAzulIntegracaoState {
  status: IntegracaoStatusResponse | null;
  sincronizacoes: SincronizacoesResponse | null;
  loading: boolean;
  error: string | null;
  sincronizando: boolean;
  conectar: () => Promise<void>;
  desconectar: () => Promise<void>;
  sincronizarAgora: () => Promise<void>;
  refresh: () => Promise<void>;
}

export function useContaAzulIntegracao(empresaId: number): ContaAzulIntegracaoState {
  const { toast } = useToast();
  const [status, setStatus] = useState<IntegracaoStatusResponse | null>(null);
  const [sincronizacoes, setSincronizacoes] = useState<SincronizacoesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sincronizando, setSincronizando] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pararPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const carregarSincronizacoes = useCallback(async () => {
    const dados = await fetchSincronizacoes(empresaId);
    setSincronizacoes(dados);
    return dados;
  }, [empresaId]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const dadosStatus = await fetchIntegracaoStatus(empresaId);
      setStatus(dadosStatus);
      if (dadosStatus.status === 'ATIVA') {
        await carregarSincronizacoes();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro inesperado ao carregar a integração.');
    } finally {
      setLoading(false);
    }
  }, [empresaId, carregarSincronizacoes]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    return () => {
      pararPolling();
    };
  }, [pararPolling]);

  const iniciarPolling = useCallback(() => {
    let tentativas = 0;
    pararPolling();
    pollingRef.current = setInterval(async () => {
      tentativas += 1;
      try {
        const dados = await carregarSincronizacoes();
        const aindaProcessando = dados.entidades.some((item) => item.status === 'EM_PROCESSAMENTO');
        if (!aindaProcessando || tentativas >= POLLING_MAX_ATTEMPTS) {
          pararPolling();
          setSincronizando(false);
        }
      } catch {
        pararPolling();
        setSincronizando(false);
      }
    }, POLLING_INTERVAL_MS);
  }, [carregarSincronizacoes, pararPolling]);

  const conectar = useCallback(async () => {
    try {
      const authUrl = await fetchAuthUrl(empresaId);
      const popup = window.open(authUrl, 'conta-azul-oauth', 'width=520,height=640');

      const handleMessage = (event: MessageEvent) => {
        if (event.origin !== window.location.origin) return;
        if (event.data?.type !== 'conta-azul-oauth') return;

        window.removeEventListener('message', handleMessage);
        if (!popup?.closed) popup?.close();

        if (event.data.status === 'success') {
          toast({ title: 'Conta Azul conectado', description: 'Integração ativada com sucesso.' });
        } else {
          toast({
            variant: 'destructive',
            title: 'Falha ao conectar',
            description: 'Não foi possível concluir a autorização.',
          });
        }
        refresh();
      };

      window.addEventListener('message', handleMessage);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Não foi possível iniciar a conexão.';
      setError(message);
      toast({ variant: 'destructive', title: 'Erro ao conectar', description: message });
    }
  }, [empresaId, refresh, toast]);

  const desconectar = useCallback(async () => {
    try {
      await desconectarIntegracao(empresaId);
      setStatus(null);
      setSincronizacoes(null);
      toast({ title: 'Conta Azul desconectado' });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Não foi possível desconectar.';
      toast({ variant: 'destructive', title: 'Erro ao desconectar', description: message });
    }
  }, [empresaId, toast]);

  const executarSincronizacao = useCallback(async () => {
    setSincronizando(true);
    try {
      await sincronizarAgoraApi(empresaId);
      iniciarPolling();
    } catch (err) {
      setSincronizando(false);
      const message = err instanceof Error ? err.message : 'Não foi possível iniciar a sincronização.';
      toast({ variant: 'destructive', title: 'Erro ao sincronizar', description: message });
    }
  }, [empresaId, iniciarPolling, toast]);

  return {
    status,
    sincronizacoes,
    loading,
    error,
    sincronizando,
    conectar,
    desconectar,
    sincronizarAgora: executarSincronizacao,
    refresh,
  };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd Painel && npx vitest run src/features/configuracoes/hooks/useContaAzulIntegracao.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add Painel/src/features/configuracoes/hooks/useContaAzulIntegracao.ts Painel/src/features/configuracoes/hooks/useContaAzulIntegracao.test.ts
git commit -m "feat: add useContaAzulIntegracao hook"
```

---

### Task 14: `ContaAzulSection` components + wire into Configuracoes

**Files:**
- Create: `Painel/src/features/configuracoes/components/ContaAzulSection/ContaAzulSection.tsx`
- Create: `Painel/src/features/configuracoes/components/ContaAzulSection/SyncStatusPanel.tsx`
- Create: `Painel/src/features/configuracoes/components/ContaAzulSection/SyncEntidadeRow.tsx`
- Create: `Painel/src/features/configuracoes/components/ContaAzulSection/index.ts`
- Modify: `Painel/src/pages/Configuracoes.tsx`
- Modify: `Painel/src/test/mocks/handlers.ts`
- Test: `Painel/src/features/configuracoes/components/ContaAzulSection/ContaAzulSection.test.tsx`

**Interfaces:**
- Consumes: `useContaAzulIntegracao` (Task 13), `Card`/`CardHeader`/`CardTitle`/`CardDescription`/`CardContent`, `Badge`, `Button`, `Dialog*` (all existing `@/components/ui/*`).
- Produces: `<ContaAzulSection empresaId={number} />`, rendered as a new Card in `Configuracoes.tsx`.

- [ ] **Step 1: Write the failing test**

Create `Painel/src/features/configuracoes/components/ContaAzulSection/ContaAzulSection.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  fetchIntegracaoStatus: vi.fn(),
  fetchSincronizacoes: vi.fn(),
  fetchAuthUrl: vi.fn(),
  desconectarIntegracao: vi.fn(),
  sincronizarAgora: vi.fn(),
}));

vi.mock('@/services/contaAzul.api', () => mocks);
vi.mock('@/hooks/use-toast', () => ({ useToast: () => ({ toast: vi.fn() }) }));

import { ContaAzulSection } from './ContaAzulSection';

describe('ContaAzulSection', () => {
  beforeEach(() => {
    Object.values(mocks).forEach((mockFn) => mockFn.mockReset());
  });

  it('mostra estado vazio e botao de conectar quando nao ha integracao', async () => {
    mocks.fetchIntegracaoStatus.mockResolvedValue({ status: null, token_expira_em: null, erro_mensagem: null });

    render(<ContaAzulSection empresaId={1} />);

    expect(await screen.findByText(/conta azul/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /conectar conta azul/i })).toBeInTheDocument();
  });

  it('mostra painel de sincronizacao quando integracao esta ATIVA', async () => {
    mocks.fetchIntegracaoStatus.mockResolvedValue({
      status: 'ATIVA',
      token_expira_em: '2026-12-01T00:00:00Z',
      erro_mensagem: null,
    });
    mocks.fetchSincronizacoes.mockResolvedValue({
      ultima_sync_em: '2026-07-27T14:32:00Z',
      status: 'SUCESSO',
      token_expira_em: '2026-12-01T00:00:00Z',
      entidades: [
        { entidade: 'pessoas', registros_processados: 248, status: 'SUCESSO', fim_em: '2026-07-27T14:32:00Z' },
      ],
    });

    render(<ContaAzulSection empresaId={1} />);

    expect(await screen.findByText(/pessoas/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sincronizar dados do conta azul agora/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /desconectar do conta azul/i })).toBeInTheDocument();
  });

  it('abre modal de confirmacao ao clicar em desconectar', async () => {
    const user = userEvent.setup();
    mocks.fetchIntegracaoStatus.mockResolvedValue({ status: 'ATIVA', token_expira_em: null, erro_mensagem: null });
    mocks.fetchSincronizacoes.mockResolvedValue({ ultima_sync_em: null, status: null, token_expira_em: null, entidades: [] });

    render(<ContaAzulSection empresaId={1} />);

    await user.click(await screen.findByRole('button', { name: /desconectar do conta azul/i }));

    expect(await screen.findByText(/tem certeza\?/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /^desconectar$/i }));

    await waitFor(() => expect(mocks.desconectarIntegracao).toHaveBeenCalledWith(1));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd Painel && npx vitest run src/features/configuracoes/components/ContaAzulSection/ContaAzulSection.test.tsx`
Expected: FAIL with a module-not-found error for `./ContaAzulSection`

- [ ] **Step 3: Implement `SyncEntidadeRow`**

Create `Painel/src/features/configuracoes/components/ContaAzulSection/SyncEntidadeRow.tsx`:

```tsx
import { useState } from 'react';
import { CircleAlert } from 'lucide-react';

import type { EntidadeSincronizacao } from '@/services/contaAzul.api';

const ENTIDADE_LABELS: Record<string, string> = {
  pessoas: 'Pessoas',
  produtos: 'Produtos',
  categorias: 'Categorias',
  vendas: 'Vendas',
  financeiro: 'Financeiro',
};

interface SyncEntidadeRowProps {
  entidade: EntidadeSincronizacao;
  maiorValor: number;
}

export function SyncEntidadeRow({ entidade, maiorValor }: SyncEntidadeRowProps) {
  const [erroExpandido, setErroExpandido] = useState(false);
  const registros = entidade.registros_processados ?? 0;
  const percentual = maiorValor > 0 ? Math.round((registros / maiorValor) * 100) : 0;
  const comErro = entidade.status === 'ERRO';
  const label = ENTIDADE_LABELS[entidade.entidade] ?? entidade.entidade;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-slate-200">{label}</span>
        <span className="flex items-center text-slate-400">
          {registros.toLocaleString('pt-BR')} registros
          {comErro && (
            <button
              type="button"
              aria-label={`Ver detalhes do erro em ${label}`}
              className="ml-2 inline-flex items-center text-rose-300 hover:text-rose-200"
              onClick={() => setErroExpandido((atual) => !atual)}
            >
              <CircleAlert className="h-4 w-4" />
            </button>
          )}
        </span>
      </div>
      <div className="h-2 rounded-full bg-slate-800">
        <div
          className={comErro ? 'h-2 rounded-full bg-rose-500' : 'h-2 rounded-full bg-sky-500'}
          style={{ width: `${Math.max(percentual, comErro ? 100 : 4)}%` }}
        />
      </div>
      {comErro && erroExpandido && (
        <p className="text-xs text-rose-300">{entidade.erro || 'Erro desconhecido ao sincronizar.'}</p>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Implement `SyncStatusPanel`**

Create `Painel/src/features/configuracoes/components/ContaAzulSection/SyncStatusPanel.tsx`:

```tsx
import { Loader2, RefreshCw } from 'lucide-react';

import { Button } from '@/components/ui/button';
import type { SincronizacoesResponse } from '@/services/contaAzul.api';

import { SyncEntidadeRow } from './SyncEntidadeRow';

const formatarDataHora = (iso: string) => {
  const data = new Date(iso);
  const formatado = new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'America/Sao_Paulo',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(data);
  return formatado.replace(',', ' às');
};

interface SyncStatusPanelProps {
  sincronizacoes: SincronizacoesResponse | null;
  sincronizando: boolean;
  onSincronizar: () => void;
}

export function SyncStatusPanel({ sincronizacoes, sincronizando, onSincronizar }: SyncStatusPanelProps) {
  const entidades = sincronizacoes?.entidades ?? [];
  const maiorValor = Math.max(1, ...entidades.map((item) => item.registros_processados ?? 0));

  return (
    <div className="space-y-4 rounded-xl border border-slate-800/70 bg-slate-900/60 p-4">
      <div className="flex items-center justify-between text-sm text-slate-300">
        <span>Última sincronização</span>
        <span className="font-medium text-slate-100">
          {sincronizacoes?.ultima_sync_em
            ? formatarDataHora(sincronizacoes.ultima_sync_em)
            : 'Nenhuma sincronização realizada ainda'}
        </span>
      </div>

      {entidades.length > 0 ? (
        <div className="space-y-3" aria-live="polite">
          {entidades.map((entidade) => (
            <SyncEntidadeRow key={entidade.entidade} entidade={entidade} maiorValor={maiorValor} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-400">Nenhuma sincronização realizada ainda.</p>
      )}

      <Button onClick={onSincronizar} disabled={sincronizando} aria-label="Sincronizar dados do Conta Azul agora">
        {sincronizando ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Sincronizando...
          </>
        ) : (
          <>
            <RefreshCw className="h-4 w-4" />
            Sincronizar agora
          </>
        )}
      </Button>
    </div>
  );
}
```

- [ ] **Step 5: Implement `ContaAzulSection`**

Create `Painel/src/features/configuracoes/components/ContaAzulSection/ContaAzulSection.tsx`:

```tsx
import { useState } from 'react';
import { Cable, Unplug } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useContaAzulIntegracao } from '@/features/configuracoes/hooks/useContaAzulIntegracao';

import { SyncStatusPanel } from './SyncStatusPanel';

interface ContaAzulSectionProps {
  empresaId: number;
}

const BADGE_VARIANT: Record<string, 'default' | 'warning' | 'destructive' | 'secondary'> = {
  ATIVA: 'default',
  EXPIRADA: 'warning',
  ERRO: 'destructive',
  DESCONECTADA: 'secondary',
};

const BADGE_LABEL: Record<string, string> = {
  ATIVA: 'Conectado',
  EXPIRADA: 'Token expirado',
  ERRO: 'Erro na integração',
  DESCONECTADA: 'Desconectado',
};

const tokenExpiraEmBreve = (tokenExpiraEm: string | null) => {
  if (!tokenExpiraEm) return false;
  const restante = new Date(tokenExpiraEm).getTime() - Date.now();
  return restante > 0 && restante <= 30 * 60 * 1000;
};

export function ContaAzulSection({ empresaId }: ContaAzulSectionProps) {
  const { status, sincronizacoes, loading, error, sincronizando, conectar, desconectar, sincronizarAgora } =
    useContaAzulIntegracao(empresaId);
  const [confirmandoDesconexao, setConfirmandoDesconexao] = useState(false);

  const statusAtual = status?.status ?? null;

  return (
    <Card className="border-slate-800/80 bg-slate-950/80 shadow-[0_24px_80px_-52px_rgba(15,23,42,0.9)]">
      <CardHeader className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-sky-400/25 bg-sky-400/10 text-sky-300">
              <Cable className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-xl">Conta Azul</CardTitle>
              <CardDescription>Conecte a empresa ao Conta Azul para sincronizar dados automaticamente.</CardDescription>
            </div>
          </div>
          {statusAtual && <Badge variant={BADGE_VARIANT[statusAtual]}>{BADGE_LABEL[statusAtual]}</Badge>}
        </div>
      </CardHeader>
      <CardContent className="space-y-4" aria-live="polite">
        {loading ? (
          <div className="h-11 animate-pulse rounded-md bg-slate-800/70" />
        ) : error ? (
          <p className="text-sm text-rose-300">{error}</p>
        ) : !statusAtual || statusAtual === 'DESCONECTADA' ? (
          <div className="flex flex-col items-start gap-3">
            <p className="text-sm text-slate-400">Nenhuma integração configurada com o Conta Azul.</p>
            <Button onClick={conectar} aria-label="Conectar ao Conta Azul">
              Conectar Conta Azul
            </Button>
          </div>
        ) : statusAtual === 'ATIVA' ? (
          <>
            {tokenExpiraEmBreve(status?.token_expira_em ?? null) && (
              <p className="text-xs text-amber-300">O token de acesso expira em breve.</p>
            )}
            <SyncStatusPanel sincronizacoes={sincronizacoes} sincronizando={sincronizando} onSincronizar={sincronizarAgora} />
            <Button variant="outline" onClick={() => setConfirmandoDesconexao(true)} aria-label="Desconectar do Conta Azul">
              <Unplug className="h-4 w-4" />
              Desconectar
            </Button>
          </>
        ) : (
          <div className="flex flex-col items-start gap-3">
            <p className="text-sm text-slate-400">
              {statusAtual === 'EXPIRADA'
                ? 'A conexão com o Conta Azul expirou.'
                : status?.erro_mensagem || 'Ocorreu um erro na integração com o Conta Azul.'}
            </p>
            <Button onClick={conectar} aria-label="Reconectar ao Conta Azul">
              {statusAtual === 'EXPIRADA' ? 'Reconectar' : 'Conectar novamente'}
            </Button>
          </div>
        )}
      </CardContent>

      <Dialog open={confirmandoDesconexao} onOpenChange={setConfirmandoDesconexao}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Desconectar Conta Azul?</DialogTitle>
            <DialogDescription>
              Tem certeza? Isso removerá a integração e os dados de sincronização deixarão de ser atualizados.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmandoDesconexao(false)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={async () => {
                await desconectar();
                setConfirmandoDesconexao(false);
              }}
            >
              Desconectar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
```

- [ ] **Step 6: Add the barrel export**

Create `Painel/src/features/configuracoes/components/ContaAzulSection/index.ts`:

```typescript
export { ContaAzulSection } from './ContaAzulSection';
```

- [ ] **Step 7: Run the component test to verify it passes**

Run: `cd Painel && npx vitest run src/features/configuracoes/components/ContaAzulSection/ContaAzulSection.test.tsx`
Expected: PASS (3 tests)

- [ ] **Step 8: Wire into `Configuracoes.tsx`**

Modify `Painel/src/pages/Configuracoes.tsx`:

```tsx
import { CompanyDataCard } from '@/features/configuracoes/components/CompanyDataCard';
import { ContaAzulSection } from '@/features/configuracoes/components/ContaAzulSection';
import { PasswordChangeCard } from '@/features/configuracoes/components/PasswordChangeCard';
import { SettingsHero } from '@/features/configuracoes/components/SettingsHero';
import { useConfiguracoesPageData } from '@/features/configuracoes/hooks/useConfiguracoesPageData';

export default function Configuracoes() {
  const { empresa, passwordForm, profileQuery } = useConfiguracoesPageData();

  return (
    <div className="space-y-6">
      <SettingsHero />

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <CompanyDataCard empresa={empresa} profileQuery={profileQuery} />
        <PasswordChangeCard passwordForm={passwordForm} />
      </div>

      {profileQuery.data?.empresa_id && <ContaAzulSection empresaId={profileQuery.data.empresa_id} />}
    </div>
  );
}
```

- [ ] **Step 9: Add an msw handler so the existing Configuracoes page test keeps passing**

`Painel/src/pages/Configuracoes.test.tsx` renders the whole page against msw with `onUnhandledRequest: "error"` (see `Painel/src/test/setup.ts`). Once `ContaAzulSection` calls `GET /empresas/1/integracoes/conta-azul` on mount, that request needs a handler or the existing test will fail.

In `Painel/src/test/mocks/handlers.ts`, add (after the `/auth/perfil` handler):

```typescript
  http.get(`${API_BASE_URL}/empresas/:empresaId/integracoes/conta-azul`, () =>
    HttpResponse.json({ status: null, token_expira_em: null, erro_mensagem: null }),
  ),
```

- [ ] **Step 10: Run the existing Configuracoes page test to verify no regression**

Run: `cd Painel && npx vitest run src/pages/Configuracoes.test.tsx`
Expected: PASS (both existing tests, unchanged)

- [ ] **Step 11: Run the full frontend test suite**

Run: `cd Painel && npx vitest run`
Expected: PASS (no regressions)

- [ ] **Step 12: Manually verify in the browser**

Run: `cd Painel && npm run dev` (with the backend/API running per `docker-compose.yml`, or against a mocked backend), open the Configurações page, and confirm the "Conta Azul" card renders below the existing two cards, shows the empty state with a "Conectar Conta Azul" button, and doesn't break the rest of the page.

- [ ] **Step 13: Commit**

```bash
git add Painel/src/features/configuracoes/components/ContaAzulSection Painel/src/pages/Configuracoes.tsx Painel/src/test/mocks/handlers.ts
git commit -m "feat: add ContaAzulSection to the company settings page"
```

---

## Self-Review Notes

- **Spec coverage:** All 6 routes, the OAuth2 flow (state persistence + popup + postMessage), the tolerant per-entity sync, the polling contract, Fernet encryption, the `conta_azul` schema, and all 7 frontend files from the design spec are covered by Tasks 1–14.
- **Type consistency checked:** `ContaAzulClient` method names (`listar_*_todas`/`listar_*_todos`) are identical between Task 4 (definition) and Task 8 (`sync_service.py` usage) and Task 8's test fakes. `SincronizacoesRepository.atualizar_entidade`/`iniciar_run`/`obter_ultimo_run` signatures match between Task 7 (definition) and Task 8/11 (usage). Frontend hook's returned key `sincronizarAgora` (a function) is deliberately named `executarSincronizacao` internally to avoid shadowing the imported `sincronizarAgora` API function from `@/services/contaAzul.api`.
- **Out of scope (explicitly, per the design spec):** incremental sync by date, any NCM/CEST/fiscal product data, background refresh outside of the sync flow.
