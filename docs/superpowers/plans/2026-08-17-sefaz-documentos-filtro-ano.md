# SEFAZ documentos — filtro por ano Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar parametro `ano` em `GET /api/sefaz/documentos`, atalho pra `data_inicio=01/01/ano`/`data_fim=31/12/ano`, sem tocar sincronizacao/persistencia.

**Architecture:** Um helper puro de dominio (`intervalo_do_ano`) converte `ano` em par de datas; a rota valida combinacao com `data_inicio`/`data_fim` e repassa pro `DocumentosRepository.listar` ja existente (sem mudar assinatura do repository).

**Tech Stack:** FastAPI (Query params), Python `datetime.date`, pytest + `TestClient` (padrao `app/tests/test_sefaz_routes.py`).

## Global Constraints

- Rota nao pode ultrapassar 30-40 linhas (`docs/backend-pr-checklist.md`) — logica de validacao do `ano` deve ficar enxuta.
- Erro de combinacao invalida = `400` (`docs/backend-error-handling.md`).
- `ano` fora de `[2000, 2100]` = `422` automatico via `Query(ge=2000, le=2100)`.
- Nao alterar `DocumentosRepository.listar` nem schema `sefaz.documentos`.
- Testes de rota nao tocam banco real — usam `monkeypatch.setattr(routes, "DocumentosRepository", ...)` como ja feito em `app/tests/test_sefaz_routes.py`.

---

### Task 1: Helper de dominio `intervalo_do_ano`

**Files:**
- Create: `app/domain/sefaz/periodo.py`
- Test: `app/tests/test_sefaz_periodo.py`

**Interfaces:**
- Produces: `intervalo_do_ano(ano: int) -> tuple[date, date]` — usado na Task 2 pela rota.

- [ ] **Step 1: Write the failing test**

Create `app/tests/test_sefaz_periodo.py`:

```python
from datetime import date

from app.domain.sefaz.periodo import intervalo_do_ano


def test_intervalo_do_ano_retorna_primeiro_e_ultimo_dia():
    inicio, fim = intervalo_do_ano(2026)

    assert inicio == date(2026, 1, 1)
    assert fim == date(2026, 12, 31)


def test_intervalo_do_ano_bissexto():
    inicio, fim = intervalo_do_ano(2028)

    assert inicio == date(2028, 1, 1)
    assert fim == date(2028, 12, 31)
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `API/`): `.\.venv-local\Scripts\python.exe -m pytest app\tests\test_sefaz_periodo.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.domain.sefaz.periodo'`

- [ ] **Step 3: Write minimal implementation**

Create `app/domain/sefaz/periodo.py`:

```python
from __future__ import annotations

from datetime import date


def intervalo_do_ano(ano: int) -> tuple[date, date]:
    return date(ano, 1, 1), date(ano, 12, 31)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv-local\Scripts\python.exe -m pytest app\tests\test_sefaz_periodo.py -q`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add app/domain/sefaz/periodo.py app/tests/test_sefaz_periodo.py
git commit -m "feat(sefaz): helper intervalo_do_ano para filtro por ano"
```

---

### Task 2: Parametro `ano` na rota `GET /sefaz/documentos`

**Files:**
- Modify: `app/api/sefaz/routes.py` (funcao `listar_documentos`, atualmente linhas 126-152)
- Test: `app/tests/test_sefaz_routes.py`

**Interfaces:**
- Consumes: `intervalo_do_ano(ano: int) -> tuple[date, date]` (Task 1).
- Consumes: `DocumentosRepository.listar(*, empresa_id, direcao=None, situacao=None, manifestacao_pendente=None, data_inicio=None, data_fim=None, limit=50, offset=0) -> tuple[int, list[dict]]` (ja existe, sem mudanca).

- [ ] **Step 1: Write the failing tests**

Add to `app/tests/test_sefaz_routes.py` (mesmo arquivo, mesma fixture `client`/`FakeDocumentosRepository` ja usados por `test_listar_documentos` — ver linhas 183-196 do arquivo atual para o padrao de fixture usado):

```python
def test_listar_documentos_com_ano_calcula_intervalo(client, monkeypatch):
    fake_repo = FakeDocumentosRepository()
    monkeypatch.setattr(routes, "DocumentosRepository", lambda: fake_repo)

    response = client.get("/api/sefaz/documentos", params={"ano": 2026})

    assert response.status_code == 200
    _, kwargs = fake_repo.calls[0]
    assert kwargs["data_inicio"] == date(2026, 1, 1)
    assert kwargs["data_fim"] == date(2026, 12, 31)


def test_listar_documentos_ano_com_data_inicio_falha_400(client, monkeypatch):
    fake_repo = FakeDocumentosRepository()
    monkeypatch.setattr(routes, "DocumentosRepository", lambda: fake_repo)

    response = client.get(
        "/api/sefaz/documentos",
        params={"ano": 2026, "data_inicio": "2026-01-01"},
    )

    assert response.status_code == 400
    assert fake_repo.calls == []


def test_listar_documentos_ano_fora_do_intervalo_falha_422(client, monkeypatch):
    fake_repo = FakeDocumentosRepository()
    monkeypatch.setattr(routes, "DocumentosRepository", lambda: fake_repo)

    response = client.get("/api/sefaz/documentos", params={"ano": 1999})

    assert response.status_code == 422
```

Confirme no topo do arquivo que `date` ja esta importado (`from datetime import date, datetime, timezone`, linha 3 atual) — nenhum import novo necessario no arquivo de teste.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv-local\Scripts\python.exe -m pytest app\tests\test_sefaz_routes.py -k ano -q`
Expected: FAIL — `test_listar_documentos_com_ano_calcula_intervalo` e `test_listar_documentos_ano_com_data_inicio_falha_400` falham porque `ano` ainda nao existe como query param (FastAPI ignora silenciosamente hoje, entao `data_inicio`/`data_fim` chegam `None` no repo e o teste de asserção falha; o teste de 400 falha porque a resposta vem 200).

- [ ] **Step 3: Write minimal implementation**

Em `app/api/sefaz/routes.py`, adicionar o import do helper (junto aos demais imports do topo, apos a linha `from app.repositories.sefaz.documentos_repository import DocumentosRepository`):

```python
from app.domain.sefaz.periodo import intervalo_do_ano
```

Substituir a funcao `listar_documentos` (linhas 126-152 do arquivo atual) por:

```python
@sefaz_router.get("/documentos", response_model=SefazDocumentoListResponse)
def listar_documentos(
    direcao: str | None = Query(default=None),
    situacao: str | None = Query(default=None),
    manifestacao_pendente: bool | None = Query(default=None),
    ano: int | None = Query(default=None, ge=2000, le=2100),
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: AuthenticatedUser = Depends(require_company_scope),
):
    if ano is not None and (data_inicio is not None or data_fim is not None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nao é possivel combinar 'ano' com 'data_inicio'/'data_fim'.",
        )
    if ano is not None:
        data_inicio, data_fim = intervalo_do_ano(ano)

    total, documentos = DocumentosRepository().listar(
        empresa_id=current_user.empresa_id,
        direcao=direcao,
        situacao=situacao,
        manifestacao_pendente=manifestacao_pendente,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limit=limit,
        offset=offset,
    )
    return SefazDocumentoListResponse(
        total=total,
        limit=limit,
        offset=offset,
        resultados=[_documento_response(documento) for documento in documentos],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv-local\Scripts\python.exe -m pytest app\tests\test_sefaz_routes.py -q`
Expected: todos os testes do arquivo passam (inclusive os 3 novos e os pre-existentes, sem regressao).

- [ ] **Step 5: Commit**

```bash
git add app/api/sefaz/routes.py app/tests/test_sefaz_routes.py
git commit -m "feat(sefaz): filtro 'ano' em GET /sefaz/documentos"
```

---

### Task 3: Rodar suite completa de testes SEFAZ (regressao)

**Files:**
- Nenhum arquivo novo — apenas verificacao.

**Interfaces:**
- Nenhuma (task de verificacao final).

- [ ] **Step 1: Run full sefaz test suite**

Run (de dentro de `API/`): `.\.venv-local\Scripts\python.exe -m pytest app\tests -k sefaz -q`
Expected: todos os testes passam, sem regressao nos fluxos existentes (`sincronizar_empresa`, `distribuicao_dfe_client`, `manifestacao`, `routes`).

- [ ] **Step 2: Nenhum commit necessario nesta task** (verificacao apenas; se algo falhar, corrigir no arquivo relevante da Task 2 e recommitar la, nao aqui).
