# SEFAZ documentos emitida -> banco Fiscal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transportar automaticamente os itens dos documentos SEFAZ `direcao='emitida'` para as tabelas Fiscal (`notas`, `notas_itens`, `produtos`, KPIs, Reforma Tributaria), reaproveitando `ProcessarNFeService.executar_xmls_importados`, sem exigir acao do usuario.

**Architecture:** Novo service `SefazFiscalTransportService` filtra documentos elegiveis (`direcao='emitida'`, `xml_armazenado` presente, ainda nao processado) e chama `ProcessarNFeService.executar_xmls_importados` diretamente (sem passar pela tabela de staging `notas_xml_importados`). Dois gatilhos: o hook ja existente `sefaz_evento_documento_novo_task` (por documento novo) e uma nova task `sefaz_backfill_fiscal_task` (por empresa, disparada ao fim de todo `sefaz_sync_empresa_task`) que cobre documentos ja sincronizados antes desta feature. Nova coluna `sefaz.documentos.processado_fiscal_em` controla o que ja foi transportado.

**Tech Stack:** FastAPI, Celery, psycopg (`dict_row`), Alembic, pytest (`TestClient`, `monkeypatch`, fixture `migrated_db` gated por `PLATAFORMA_FISCAL_TEST_DATABASE_URL`), React/TypeScript (Painel).

## Global Constraints

- Escopo: somente `direcao='emitida'`. `direcao='recebida'` fica de fora (fora de escopo do design).
- Nao reusar `XMLImportacaoService`/`notas_xml_importados` — chamar `ProcessarNFeService.executar_xmls_importados` diretamente com tuplas vindas de `sefaz.documentos`.
- Falha do `ProcessarNFeService` (`resposta.status != "processado"`) nunca propaga excecao — loga e deixa o documento pendente pra proxima tentativa.
- Nenhum endpoint HTTP novo — todo o fluxo e automatico (hook + backfill).
- Nao alterar `SefazDistribuicaoService._publicar_evento_documento_novo` nem a logica de calculo de `direcao` (`calcular_direcao`).
- Rota nao pode ultrapassar 30-40 linhas / service nao deve crescer alem de ~300 linhas por metodo de ~60 linhas (`docs/backend-pr-checklist.md`).
- Testes de rota/worker nao tocam banco real (`monkeypatch.setattr` no service/repository, padrao ja usado em `test_sefaz_task.py`/`test_sefaz_routes.py`); testes de repository usam a fixture `migrated_db` (pulados automaticamente sem `PLATAFORMA_FISCAL_TEST_DATABASE_URL`).
- Comandos de teste abaixo assumem execucao a partir de `API/` com o venv local do Windows: `.\.venv-local\Scripts\python.exe -m pytest ...`.

---

### Task 1: Migration `processado_fiscal_em` em `sefaz.documentos`

**Files:**
- Create: `app/alembic/versions/20260818_0014_sefaz_documentos_processado_fiscal.py`
- Modify: `app/tests/test_database_schema.py` (novo teste, apos `test_sefaz_migration_creates_expected_schema_objects`, linha 119 atual)
- Modify: `docs/database.md` (secao "Modulo SEFAZ")

**Interfaces:**
- Produces: coluna `sefaz.documentos.processado_fiscal_em TIMESTAMPTZ NULL`, consumida pelas Tasks 2-6.

- [ ] **Step 1: Write the failing test**

Adicionar em `app/tests/test_database_schema.py`, logo apos `test_sefaz_migration_creates_expected_schema_objects` (que termina na linha 118 com `assert "DROP SCHEMA IF EXISTS sefaz CASCADE" in sefaz_schema`):

```python
def test_sefaz_processado_fiscal_migration_adiciona_coluna():
    migration = (
        ALEMBIC_DIR / "20260818_0014_sefaz_documentos_processado_fiscal.py"
    ).read_text(encoding="utf-8")

    assert "ALTER TABLE sefaz.documentos" in migration
    assert "ADD COLUMN processado_fiscal_em TIMESTAMPTZ NULL" in migration
    assert 'revision = "20260818_0014"' in migration
    assert 'down_revision = "20260814_0013"' in migration
    assert "DROP COLUMN IF EXISTS processado_fiscal_em" in migration
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv-local\Scripts\python.exe -m pytest app\tests\test_database_schema.py -k processado_fiscal -q`
Expected: FAIL com `FileNotFoundError` (arquivo de migration ainda nao existe).

- [ ] **Step 3: Write minimal implementation**

Create `app/alembic/versions/20260818_0014_sefaz_documentos_processado_fiscal.py`:

```python
"""adiciona processado_fiscal_em em sefaz.documentos

Revision ID: 20260818_0014
Revises: 20260814_0013
Create Date: 2026-08-18
"""

from alembic import op


revision = "20260818_0014"
down_revision = "20260814_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE sefaz.documentos
            ADD COLUMN processado_fiscal_em TIMESTAMPTZ NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE sefaz.documentos
            DROP COLUMN IF EXISTS processado_fiscal_em;
        """
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv-local\Scripts\python.exe -m pytest app\tests\test_database_schema.py -k processado_fiscal -q`
Expected: `1 passed`

- [ ] **Step 5: Atualizar `docs/database.md`**

Na secao "Modulo SEFAZ", no bullet de `sefaz.documentos` (comeca com `- \`sefaz.documentos\`: documentos distribuidos pela SEFAZ...` e termina em "...so preenchido para \`nfeProc\` (XML completo); \`resNFe\` fica so com o resumo."), adicionar logo apos esse paragrafo:

```markdown
  Alembic `20260818_0014` adiciona `processado_fiscal_em` (`TIMESTAMPTZ NULL`) —
  marca quando os itens desse documento (somente `direcao='emitida'`) foram
  transportados para as tabelas Fiscal (`notas`/`notas_itens`). `NULL` cobre
  pendente, falha na ultima tentativa e `resNFe` sem XML completo — ver
  `docs/superpowers/specs/2026-08-18-sefaz-fiscal-transport-design.md`.
```

- [ ] **Step 6: Commit**

```bash
git add API/app/alembic/versions/20260818_0014_sefaz_documentos_processado_fiscal.py API/app/tests/test_database_schema.py docs/database.md
git commit -m "feat(sefaz): adiciona processado_fiscal_em em sefaz.documentos"
```

---

### Task 2: Repository — `marcar_processado_fiscal` e `listar_pendentes_fiscal`

**Files:**
- Modify: `app/repositories/sefaz/documentos_repository.py:88-101` (entre `atualizar_manifestacao` e `listar`)
- Test: `app/tests/test_sefaz_documentos_repository.py`

**Interfaces:**
- Consumes: nenhuma nova (usa `SefazRepositoryBase._connect()` ja existente).
- Produces: `DocumentosRepository.marcar_processado_fiscal(documento_id: int) -> None` e `DocumentosRepository.listar_pendentes_fiscal(empresa_id: int) -> list[dict[str, Any]]`, consumidos pelas Tasks 3-5.

- [ ] **Step 1: Write the failing tests**

Adicionar ao final de `app/tests/test_sefaz_documentos_repository.py` (reaproveita `_inserir_documento`/`empresa_id` ja definidos no topo do arquivo):

```python
def test_listar_pendentes_fiscal_filtra_emitida_com_xml_nao_processado(migrated_db, empresa_id):
    from app.repositories.sefaz.documentos_repository import DocumentosRepository

    repo = DocumentosRepository()
    _inserir_documento(
        repo,
        empresa_id,
        chave_acesso="6666666666666666666666666666666666666666",
        direcao="emitida",
        tipo_documento="nfeProc",
        xml_armazenado=b"<nfeProc>xml</nfeProc>",
    )
    _inserir_documento(
        repo,
        empresa_id,
        chave_acesso="7777777777777777777777777777777777777777",
        direcao="recebida",
        tipo_documento="nfeProc",
        xml_armazenado=b"<nfeProc>xml</nfeProc>",
    )
    _inserir_documento(
        repo,
        empresa_id,
        chave_acesso="8888888888888888888888888888888888888888",
        direcao="emitida",
        tipo_documento="resNFe",
        xml_armazenado=None,
    )

    pendentes = repo.listar_pendentes_fiscal(empresa_id)

    assert [documento["chave_acesso"] for documento in pendentes] == [
        "6666666666666666666666666666666666666666"
    ]


def test_marcar_processado_fiscal_atualiza_timestamp_e_sai_dos_pendentes(migrated_db, empresa_id):
    from app.repositories.sefaz.documentos_repository import DocumentosRepository

    repo = DocumentosRepository()
    _inserir_documento(
        repo,
        empresa_id,
        chave_acesso="9999999999999999999999999999999999999999",
        direcao="emitida",
        xml_armazenado=b"<nfeProc>xml</nfeProc>",
    )
    documento = repo.obter_por_chave(empresa_id, "9999999999999999999999999999999999999999")

    repo.marcar_processado_fiscal(documento["id"])

    atualizado = repo.obter_por_id(empresa_id, documento["id"])
    assert atualizado["processado_fiscal_em"] is not None
    assert repo.listar_pendentes_fiscal(empresa_id) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv-local\Scripts\python.exe -m pytest app\tests\test_sefaz_documentos_repository.py -k "pendentes_fiscal or processado_fiscal" -q`
Expected: FAIL com `AttributeError: 'DocumentosRepository' object has no attribute 'listar_pendentes_fiscal'` (ou `marcar_processado_fiscal`). Se `PLATAFORMA_FISCAL_TEST_DATABASE_URL` nao estiver setado, os testes sao pulados (`SKIPPED`) — nesse caso, rode com a variavel setada para validar antes de seguir (ver `docs/testing.md`).

- [ ] **Step 3: Write minimal implementation**

Em `app/repositories/sefaz/documentos_repository.py`, inserir os dois metodos abaixo entre `atualizar_manifestacao` (termina na linha 100 atual com `conn.commit()`) e `def listar(` (linha 102 atual):

```python
    def marcar_processado_fiscal(self, documento_id: int) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE sefaz.documentos
                    SET processado_fiscal_em = NOW()
                    WHERE id = %s
                    """,
                    (documento_id,),
                )
            conn.commit()

    def listar_pendentes_fiscal(self, empresa_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM sefaz.documentos
                    WHERE empresa_id = %s
                      AND direcao = 'emitida'
                      AND xml_armazenado IS NOT NULL
                      AND processado_fiscal_em IS NULL
                    ORDER BY id ASC
                    """,
                    (empresa_id,),
                )
                rows = [dict(row) for row in cur.fetchall()]

        return rows

```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv-local\Scripts\python.exe -m pytest app\tests\test_sefaz_documentos_repository.py -q`
Expected: todos os testes do arquivo passam (existentes + 2 novos), sem regressao.

- [ ] **Step 5: Commit**

```bash
git add API/app/repositories/sefaz/documentos_repository.py API/app/tests/test_sefaz_documentos_repository.py
git commit -m "feat(sefaz): marcar_processado_fiscal e listar_pendentes_fiscal no DocumentosRepository"
```

---

### Task 3: `SefazFiscalTransportService`

**Files:**
- Create: `app/services/sefaz/sefaz_fiscal_transport_service.py`
- Test: `app/tests/test_sefaz_fiscal_transport_service.py`

**Interfaces:**
- Consumes: `DocumentosRepository.marcar_processado_fiscal(documento_id: int) -> None` (Task 2); `ProcessarNFeService.executar_xmls_importados(cnpj_emitente: str, xmls_importados: list[tuple[int, str, bytes]]) -> tuple[ProcessarNFeResponse, list[int]]` (ja existe em `app/services/nfe/process_nfe.py`, `ProcessarNFeResponse.status: str`).
- Produces: `SefazFiscalTransportService(documentos_repository: DocumentosRepository | None = None)` com metodo `transportar_documentos(*, empresa_id: int, cnpj_empresa: str, documentos: list[dict]) -> int` (retorna quantidade marcada como processada), consumido pelas Tasks 4 e 5.

- [ ] **Step 1: Write the failing tests**

Create `app/tests/test_sefaz_fiscal_transport_service.py`:

```python
from __future__ import annotations

from types import SimpleNamespace

from app.services.sefaz.sefaz_fiscal_transport_service import SefazFiscalTransportService


class FakeDocumentosRepository:
    def __init__(self):
        self.marcados: list[int] = []

    def marcar_processado_fiscal(self, documento_id: int) -> None:
        self.marcados.append(documento_id)


def _documento(**overrides):
    base = {
        "id": 1,
        "chave_acesso": "35123456789012345678901234567890123456789012",
        "direcao": "emitida",
        "xml_armazenado": b"<nfeProc>xml</nfeProc>",
        "processado_fiscal_em": None,
    }
    base.update(overrides)
    return base


def test_ignora_documento_recebida():
    repo = FakeDocumentosRepository()
    service = SefazFiscalTransportService(documentos_repository=repo)

    total = service.transportar_documentos(
        empresa_id=1,
        cnpj_empresa="12345678000190",
        documentos=[_documento(direcao="recebida")],
    )

    assert total == 0
    assert repo.marcados == []


def test_ignora_documento_sem_xml_armazenado():
    repo = FakeDocumentosRepository()
    service = SefazFiscalTransportService(documentos_repository=repo)

    total = service.transportar_documentos(
        empresa_id=1,
        cnpj_empresa="12345678000190",
        documentos=[_documento(xml_armazenado=None)],
    )

    assert total == 0
    assert repo.marcados == []


def test_ignora_documento_ja_processado():
    repo = FakeDocumentosRepository()
    service = SefazFiscalTransportService(documentos_repository=repo)

    total = service.transportar_documentos(
        empresa_id=1,
        cnpj_empresa="12345678000190",
        documentos=[_documento(processado_fiscal_em="2026-08-18T00:00:00Z")],
    )

    assert total == 0
    assert repo.marcados == []


def test_sucesso_marca_documentos_processados(monkeypatch):
    def fake_executar(self, cnpj_emitente, xmls_importados):
        assert cnpj_emitente == "12345678000190"
        assert xmls_importados == [
            (1, "35123456789012345678901234567890123456789012", b"<nfeProc>xml</nfeProc>")
        ]
        return SimpleNamespace(status="processado", erros=[]), [1]

    monkeypatch.setattr(
        "app.services.sefaz.sefaz_fiscal_transport_service.ProcessarNFeService.executar_xmls_importados",
        fake_executar,
    )

    repo = FakeDocumentosRepository()
    service = SefazFiscalTransportService(documentos_repository=repo)

    total = service.transportar_documentos(
        empresa_id=1,
        cnpj_empresa="12345678000190",
        documentos=[_documento()],
    )

    assert total == 1
    assert repo.marcados == [1]


def test_falha_no_processamento_nao_marca_e_nao_propaga(monkeypatch):
    def fake_executar(self, cnpj_emitente, xmls_importados):
        return SimpleNamespace(status="erro", erros=[{"mensagem": "XML invalido"}]), []

    monkeypatch.setattr(
        "app.services.sefaz.sefaz_fiscal_transport_service.ProcessarNFeService.executar_xmls_importados",
        fake_executar,
    )

    repo = FakeDocumentosRepository()
    service = SefazFiscalTransportService(documentos_repository=repo)

    total = service.transportar_documentos(
        empresa_id=1,
        cnpj_empresa="12345678000190",
        documentos=[_documento()],
    )

    assert total == 0
    assert repo.marcados == []


def test_xml_armazenado_como_memoryview_e_convertido_para_bytes(monkeypatch):
    capturado = {}

    def fake_executar(self, cnpj_emitente, xmls_importados):
        capturado["xmls"] = xmls_importados
        return SimpleNamespace(status="processado", erros=[]), [1]

    monkeypatch.setattr(
        "app.services.sefaz.sefaz_fiscal_transport_service.ProcessarNFeService.executar_xmls_importados",
        fake_executar,
    )

    repo = FakeDocumentosRepository()
    service = SefazFiscalTransportService(documentos_repository=repo)

    service.transportar_documentos(
        empresa_id=1,
        cnpj_empresa="12345678000190",
        documentos=[_documento(xml_armazenado=memoryview(b"<nfeProc>xml</nfeProc>"))],
    )

    assert capturado["xmls"][0][2] == b"<nfeProc>xml</nfeProc>"
    assert isinstance(capturado["xmls"][0][2], bytes)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv-local\Scripts\python.exe -m pytest app\tests\test_sefaz_fiscal_transport_service.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.services.sefaz.sefaz_fiscal_transport_service'`

- [ ] **Step 3: Write minimal implementation**

Create `app/services/sefaz/sefaz_fiscal_transport_service.py`:

```python
from __future__ import annotations

import logging
from typing import Any

from app.repositories.sefaz.documentos_repository import DocumentosRepository
from app.services.nfe.process_nfe import ProcessarNFeService

logger = logging.getLogger("services.sefaz.fiscal_transport")


def _xml_bytes(valor: Any) -> bytes:
    if hasattr(valor, "tobytes"):
        return valor.tobytes()
    if isinstance(valor, (bytes, bytearray)):
        return bytes(valor)
    return bytes(valor)


class SefazFiscalTransportService:
    """Transporta itens de documentos SEFAZ 'emitida' para as tabelas Fiscal."""

    def __init__(self, documentos_repository: DocumentosRepository | None = None) -> None:
        self.documentos_repository = documentos_repository or DocumentosRepository()

    def transportar_documentos(
        self,
        *,
        empresa_id: int,
        cnpj_empresa: str,
        documentos: list[dict[str, Any]],
    ) -> int:
        elegiveis = [
            documento
            for documento in documentos
            if documento.get("direcao") == "emitida"
            and documento.get("xml_armazenado")
            and not documento.get("processado_fiscal_em")
        ]
        if not elegiveis:
            return 0

        tuplas = [
            (documento["id"], documento["chave_acesso"], _xml_bytes(documento["xml_armazenado"]))
            for documento in elegiveis
        ]

        resposta, ids_processados = ProcessarNFeService().executar_xmls_importados(
            cnpj_emitente=cnpj_empresa,
            xmls_importados=tuplas,
        )

        if resposta.status != "processado":
            logger.warning(
                "sefaz_fiscal_transport_falhou",
                extra={
                    "empresa_id": empresa_id,
                    "cnpj_empresa": cnpj_empresa,
                    "documentos": [documento["id"] for documento in elegiveis],
                    "erros": resposta.erros,
                },
            )
            return 0

        ids_processados_set = set(ids_processados)
        total_marcados = 0
        for documento in elegiveis:
            if documento["id"] in ids_processados_set:
                self.documentos_repository.marcar_processado_fiscal(documento["id"])
                total_marcados += 1

        logger.info(
            "sefaz_fiscal_transport_concluido",
            extra={
                "empresa_id": empresa_id,
                "cnpj_empresa": cnpj_empresa,
                "total_elegiveis": len(elegiveis),
                "total_marcados": total_marcados,
            },
        )
        return total_marcados
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv-local\Scripts\python.exe -m pytest app\tests\test_sefaz_fiscal_transport_service.py -q`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add API/app/services/sefaz/sefaz_fiscal_transport_service.py API/app/tests/test_sefaz_fiscal_transport_service.py
git commit -m "feat(sefaz): SefazFiscalTransportService transporta itens emitida para o Fiscal"
```

---

### Task 4: Ativar o hook `sefaz_evento_documento_novo_task`

**Files:**
- Modify: `app/workers/sefaz_tasks.py` (imports no topo + funcao `sefaz_evento_documento_novo_task`, linhas 59-66 atuais)
- Modify: `app/tests/test_sefaz_task.py` (substituir `test_evento_documento_novo_task_roda_sem_erro`, linhas 80-85 atuais, por dois testes novos)

**Interfaces:**
- Consumes: `DocumentosRepository.obter_por_chave(empresa_id: int, chave_acesso: str) -> dict | None` (ja existe); `SefazFiscalTransportService().transportar_documentos(*, empresa_id, cnpj_empresa, documentos) -> int` (Task 3).

- [ ] **Step 1: Write the failing tests**

Em `app/tests/test_sefaz_task.py`, substituir a funcao `test_evento_documento_novo_task_roda_sem_erro` (linhas 80-85 atuais) por:

```python
def test_evento_documento_novo_task_sem_documento_correspondente(monkeypatch):
    class FakeDocumentosRepository:
        def obter_por_chave(self, empresa_id, chave_acesso):
            return None

    monkeypatch.setattr(sefaz_tasks, "DocumentosRepository", FakeDocumentosRepository)

    resultado = sefaz_tasks.sefaz_evento_documento_novo_task.run(
        1, "35260812345678000190550010000000011234567890"
    )

    assert resultado == {"status": "SUCCESS", "motivo": "documento_nao_encontrado"}


def test_evento_documento_novo_task_transporta_documento_emitida(monkeypatch):
    documento = {
        "id": 10,
        "chave_acesso": "35260812345678000190550010000000011234567890",
        "direcao": "emitida",
        "cnpj_emitente": "12345678000190",
        "xml_armazenado": b"<nfeProc>xml</nfeProc>",
        "processado_fiscal_em": None,
    }

    class FakeDocumentosRepository:
        def obter_por_chave(self, empresa_id, chave_acesso):
            assert empresa_id == 1
            assert chave_acesso == documento["chave_acesso"]
            return documento

    chamadas = []

    class FakeTransportService:
        def transportar_documentos(self, *, empresa_id, cnpj_empresa, documentos):
            chamadas.append((empresa_id, cnpj_empresa, documentos))
            return 1

    monkeypatch.setattr(sefaz_tasks, "DocumentosRepository", FakeDocumentosRepository)
    monkeypatch.setattr(sefaz_tasks, "SefazFiscalTransportService", FakeTransportService)

    resultado = sefaz_tasks.sefaz_evento_documento_novo_task.run(1, documento["chave_acesso"])

    assert resultado == {"status": "SUCCESS", "total_marcados": 1}
    assert chamadas == [(1, "12345678000190", [documento])]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv-local\Scripts\python.exe -m pytest app\tests\test_sefaz_task.py -k evento_documento_novo -q`
Expected: FAIL — a task atual so loga e retorna `{"status": "SUCCESS"}`, sem consultar `DocumentosRepository` nem chamar `SefazFiscalTransportService` (asserts de `resultado`/`chamadas` falham).

- [ ] **Step 3: Write minimal implementation**

Em `app/workers/sefaz_tasks.py`, adicionar imports no topo (apos `from app.repositories.sefaz.certificados_repository import CertificadosRepository`, linha 5 atual):

```python
from app.repositories.sefaz.documentos_repository import DocumentosRepository
from app.services.sefaz.sefaz_fiscal_transport_service import SefazFiscalTransportService
```

Substituir a funcao `sefaz_evento_documento_novo_task` (linhas 59-66 atuais) por:

```python
@celery_app.task(name="sefaz_evento_documento_novo_task")
def sefaz_evento_documento_novo_task(empresa_id: int, chave_acesso: str) -> dict:
    """Transporta os itens do documento para o banco Fiscal quando elegivel (direcao=emitida)."""
    logger.info(
        "sefaz_documento_novo_evento_recebido",
        extra={"empresa_id": empresa_id, "chave_acesso": chave_acesso},
    )

    documento = DocumentosRepository().obter_por_chave(empresa_id, chave_acesso)
    if documento is None:
        return {"status": "SUCCESS", "motivo": "documento_nao_encontrado"}

    total_marcados = SefazFiscalTransportService().transportar_documentos(
        empresa_id=empresa_id,
        cnpj_empresa=documento["cnpj_emitente"],
        documentos=[documento],
    )
    return {"status": "SUCCESS", "total_marcados": total_marcados}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv-local\Scripts\python.exe -m pytest app\tests\test_sefaz_task.py -q`
Expected: todos os testes do arquivo passam (existentes + 2 novos), sem regressao.

- [ ] **Step 5: Commit**

```bash
git add API/app/workers/sefaz_tasks.py API/app/tests/test_sefaz_task.py
git commit -m "feat(sefaz): hook sefaz_evento_documento_novo_task transporta documento para o Fiscal"
```

---

### Task 5: Backfill `sefaz_backfill_fiscal_task` + disparo ao fim do sync

**Files:**
- Modify: `app/workers/sefaz_tasks.py` (nova task apos `sefaz_evento_documento_novo_task`; funcao `sefaz_sync_empresa_task`, linhas 27-39 atuais)
- Modify: `app/tests/test_sefaz_task.py` (`test_sync_empresa_task_retorna_resultado_do_service`, linhas 54-65 atuais, + 2 testes novos para a task de backfill)

**Interfaces:**
- Consumes: `DocumentosRepository.listar_pendentes_fiscal(empresa_id: int) -> list[dict]` (Task 2); `SefazFiscalTransportService().transportar_documentos(...)` (Task 3).
- Produces: task Celery `sefaz_backfill_fiscal_task(empresa_id: int, cnpj_empresa: str) -> dict`.

- [ ] **Step 1: Write the failing tests**

Em `app/tests/test_sefaz_task.py`, substituir `test_sync_empresa_task_retorna_resultado_do_service` (linhas 54-65 atuais) por:

```python
def test_sync_empresa_task_retorna_resultado_do_service_e_dispara_backfill(monkeypatch):
    monkeypatch.setattr(
        sefaz_tasks,
        "_sincronizar_empresa",
        lambda empresa_id, cnpj_titular: ResultadoSincronizacao(
            status="sucesso", documentos_novos=5, nsu_inicial="0", nsu_final="10"
        ),
    )
    chamadas = []
    monkeypatch.setattr(
        sefaz_tasks.sefaz_backfill_fiscal_task,
        "apply_async",
        lambda args, queue: chamadas.append((args, queue)),
    )

    resultado = sefaz_tasks.sefaz_sync_empresa_task.run(1, "11111111000191")

    assert resultado == {"status": "sucesso", "documentos_novos": 5, "empresa_id": 1}
    assert chamadas == [([1, "11111111000191"], "sefaz")]
```

Adicionar ao final do arquivo:

```python
def test_backfill_fiscal_task_processa_pendentes(monkeypatch):
    pendentes = [{"id": 1}, {"id": 2}]

    class FakeDocumentosRepository:
        def listar_pendentes_fiscal(self, empresa_id):
            assert empresa_id == 1
            return pendentes

    chamadas = []

    class FakeTransportService:
        def transportar_documentos(self, *, empresa_id, cnpj_empresa, documentos):
            chamadas.append((empresa_id, cnpj_empresa, documentos))
            return len(documentos)

    monkeypatch.setattr(sefaz_tasks, "DocumentosRepository", FakeDocumentosRepository)
    monkeypatch.setattr(sefaz_tasks, "SefazFiscalTransportService", FakeTransportService)

    resultado = sefaz_tasks.sefaz_backfill_fiscal_task.run(1, "11111111000191")

    assert resultado == {"status": "SUCCESS", "total_pendentes": 2, "total_marcados": 2}
    assert chamadas == [(1, "11111111000191", pendentes)]


def test_backfill_fiscal_task_sem_pendentes(monkeypatch):
    class FakeDocumentosRepository:
        def listar_pendentes_fiscal(self, empresa_id):
            return []

    chamadas = []

    class FakeTransportService:
        def transportar_documentos(self, *, empresa_id, cnpj_empresa, documentos):
            chamadas.append(documentos)
            return 0

    monkeypatch.setattr(sefaz_tasks, "DocumentosRepository", FakeDocumentosRepository)
    monkeypatch.setattr(sefaz_tasks, "SefazFiscalTransportService", FakeTransportService)

    resultado = sefaz_tasks.sefaz_backfill_fiscal_task.run(1, "11111111000191")

    assert resultado == {"status": "SUCCESS", "total_pendentes": 0, "total_marcados": 0}
    assert chamadas == [[]]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv-local\Scripts\python.exe -m pytest app\tests\test_sefaz_task.py -k "backfill or retorna_resultado" -q`
Expected: FAIL — `sefaz_backfill_fiscal_task` ainda nao existe (`AttributeError`) e `sefaz_sync_empresa_task` ainda nao dispara `apply_async`.

- [ ] **Step 3: Write minimal implementation**

Em `app/workers/sefaz_tasks.py`, adicionar apos a funcao `sefaz_evento_documento_novo_task` (que agora termina em `return {"status": "SUCCESS", "total_marcados": total_marcados}` apos a Task 4):

```python
@celery_app.task(name="sefaz_backfill_fiscal_task")
def sefaz_backfill_fiscal_task(empresa_id: int, cnpj_empresa: str) -> dict:
    """Reprocessa documentos 'emitida' pendentes de transporte para o banco Fiscal."""
    pendentes = DocumentosRepository().listar_pendentes_fiscal(empresa_id)
    total_marcados = SefazFiscalTransportService().transportar_documentos(
        empresa_id=empresa_id,
        cnpj_empresa=cnpj_empresa,
        documentos=pendentes,
    )
    logger.info(
        "sefaz_backfill_fiscal_concluido",
        extra={
            "empresa_id": empresa_id,
            "total_pendentes": len(pendentes),
            "total_marcados": total_marcados,
        },
    )
    return {
        "status": "SUCCESS",
        "total_pendentes": len(pendentes),
        "total_marcados": total_marcados,
    }
```

Substituir a funcao `sefaz_sync_empresa_task` (linhas 27-39 atuais) por:

```python
@celery_app.task(
    name="sefaz_sync_empresa_task",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def sefaz_sync_empresa_task(empresa_id: int, cnpj_titular: str) -> dict:
    resultado = _sincronizar_empresa(empresa_id, cnpj_titular)
    sefaz_backfill_fiscal_task.apply_async(args=[empresa_id, cnpj_titular], queue="sefaz")
    return {
        "status": resultado.status,
        "documentos_novos": resultado.documentos_novos,
        "empresa_id": empresa_id,
    }
```

Nota: o disparo do backfill so acontece apos `_sincronizar_empresa` retornar sem excecao — se `_sincronizar_empresa` levantar (caso coberto por `test_sync_empresa_task_propaga_excecao_para_autoretry`, que continua sem mudanca), o backfill nao e enfileirado nessa execucao; a proxima sincronizacao bem-sucedida cobre.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv-local\Scripts\python.exe -m pytest app\tests\test_sefaz_task.py -q`
Expected: todos os testes do arquivo passam (existentes + novos), sem regressao.

- [ ] **Step 5: Commit**

```bash
git add API/app/workers/sefaz_tasks.py API/app/tests/test_sefaz_task.py
git commit -m "feat(sefaz): backfill fiscal ao fim de cada sync SEFAZ"
```

---

### Task 6: Expor `processado_fiscal_em` em `GET /api/sefaz/documentos`

**Files:**
- Modify: `app/models/sefaz/schemas.py:22-35` (`SefazDocumentoResponse`)
- Modify: `app/api/sefaz/routes.py:37-52` (`_documento_response`)
- Test: `app/tests/test_sefaz_routes.py`

**Interfaces:**
- Produces: campo `processado_fiscal_em: datetime | None` em `SefazDocumentoResponse` e `SefazDocumentoDetalheResponse` (herda), consumido pela Task 7.

- [ ] **Step 1: Write the failing test**

Adicionar em `app/tests/test_sefaz_routes.py`, apos `test_listar_documentos` (linhas 183-193 atuais):

```python
def test_listar_documentos_expoe_processado_fiscal_em(client, monkeypatch):
    class FakeRepo:
        def listar(self, **kwargs):
            return 1, [
                {
                    "id": 20,
                    "chave_acesso": "35123456789012345678901234567890123456789099",
                    "tipo_documento": "nfeProc",
                    "direcao": "emitida",
                    "cnpj_emitente": "12345678000190",
                    "cnpj_destinatario": None,
                    "nsu": "000000000000020",
                    "data_emissao": date(2026, 8, 5),
                    "valor_total": Decimal("50.00"),
                    "situacao": "autorizada",
                    "manifestacao_status": None,
                    "criado_em": datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
                    "atualizado_em": datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
                    "processado_fiscal_em": datetime(2026, 8, 5, 13, 0, tzinfo=timezone.utc),
                }
            ]

    monkeypatch.setattr(routes, "DocumentosRepository", lambda: FakeRepo())

    response = client.get("/api/sefaz/documentos")

    assert response.status_code == 200
    resultado = response.json()["resultados"][0]
    assert resultado["processado_fiscal_em"] is not None


def test_listar_documentos_processado_fiscal_em_ausente_vira_none(client, monkeypatch):
    fake_repo = FakeDocumentosRepository()
    monkeypatch.setattr(routes, "DocumentosRepository", lambda: fake_repo)

    response = client.get("/api/sefaz/documentos")

    assert response.status_code == 200
    resultado = response.json()["resultados"][0]
    assert resultado["processado_fiscal_em"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv-local\Scripts\python.exe -m pytest app\tests\test_sefaz_routes.py -k processado_fiscal -q`
Expected: FAIL com `KeyError: 'processado_fiscal_em'` (campo ainda nao existe no response).

- [ ] **Step 3: Write minimal implementation**

Em `app/models/sefaz/schemas.py`, na classe `SefazDocumentoResponse` (linhas 22-35 atuais), adicionar apos `atualizado_em: datetime | None = None` (linha 35 atual):

```python
    processado_fiscal_em: datetime | None = None
```

Em `app/api/sefaz/routes.py`, na funcao `_documento_response` (linhas 37-52 atuais), adicionar apos `atualizado_em=documento.get("atualizado_em"),` (linha 51 atual):

```python
        processado_fiscal_em=documento.get("processado_fiscal_em"),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv-local\Scripts\python.exe -m pytest app\tests\test_sefaz_routes.py -q`
Expected: todos os testes do arquivo passam (existentes + 2 novos), sem regressao.

- [ ] **Step 5: Commit**

```bash
git add API/app/models/sefaz/schemas.py API/app/api/sefaz/routes.py API/app/tests/test_sefaz_routes.py
git commit -m "feat(sefaz): expoe processado_fiscal_em em GET /sefaz/documentos"
```

---

### Task 7: Badge "Fiscal" no Painel (`SefazSection`)

**Files:**
- Modify: `Painel/src/features/configuracoes/components/SefazSection/sefaz.types.ts:20-34` (`SefazDocumento`)
- Modify: `Painel/src/features/configuracoes/components/SefazSection/SefazSection.tsx` (helpers no topo + tabela de documentos, linhas 552-606 atuais)

**Interfaces:**
- Consumes: campo `processado_fiscal_em` do payload de `GET /api/sefaz/documentos` (Task 6) — sem camada de mapeamento camelCase, o tipo TS usa o mesmo nome snake_case do backend, igual aos demais campos de `SefazDocumento`.

- [ ] **Step 1: Adicionar o campo ao tipo**

Em `Painel/src/features/configuracoes/components/SefazSection/sefaz.types.ts`, na interface `SefazDocumento` (linhas 20-34 atuais), adicionar apos `atualizado_em: string | null;` (linha 33 atual):

```typescript
  processado_fiscal_em: string | null;
```

- [ ] **Step 2: Adicionar helpers de label/badge**

Em `Painel/src/features/configuracoes/components/SefazSection/SefazSection.tsx`, apos `getDirecaoLabel` (linha 62 atual: `const getDirecaoLabel = (direcao: SefazDocumento['direcao']) => (direcao === 'emitida' ? 'Emitida' : 'Recebida');`), adicionar:

```typescript
const getFiscalLabel = (documento: SefazDocumento) => {
  if (documento.direcao !== 'emitida') {
    return 'Nao aplicavel';
  }
  return documento.processado_fiscal_em ? 'No Fiscal' : 'Pendente';
};

const getFiscalBadge = (documento: SefazDocumento) => {
  if (documento.direcao !== 'emitida') {
    return 'outline' as const;
  }
  return documento.processado_fiscal_em ? ('default' as const) : ('secondary' as const);
};
```

- [ ] **Step 3: Adicionar coluna na tabela de documentos**

No cabecalho da tabela (linhas 552-563 atuais), adicionar `<TableHead>Fiscal</TableHead>` apos `<TableHead>Manifestacao</TableHead>` (linha 561 atual):

```tsx
                          <TableHead>Manifestacao</TableHead>
                          <TableHead>Fiscal</TableHead>
```

No corpo da tabela (linhas 565-606 atuais), adicionar a celula correspondente apos a celula de manifestacao (linhas 600-604 atuais: `<TableCell><Badge variant={getManifestacaoBadge(...)}>...</Badge></TableCell>`):

```tsx
                            <TableCell>
                              <Badge variant={getFiscalBadge(documento)}>{getFiscalLabel(documento)}</Badge>
                            </TableCell>
```

- [ ] **Step 4: Verificar tipos e lint**

Run (de dentro de `Painel/`): `npm run lint` e `npm run build`
Expected: sem erros novos de tipo/lint relacionados a `SefazSection`/`sefaz.types`.

- [ ] **Step 5: Commit**

```bash
git add Painel/src/features/configuracoes/components/SefazSection/sefaz.types.ts Painel/src/features/configuracoes/components/SefazSection/SefazSection.tsx
git commit -m "feat(painel): badge Fiscal na listagem de documentos SEFAZ"
```

---

### Task 8: Docs finais e regressao completa

**Files:**
- Modify: `docs/jobs.md` (secao "Sincronizacao SEFAZ (fora do framework `processing_jobs`)")
- Modify: `docs/api-contracts.md` (secao "Sincronizacao SEFAZ", linhas 283 e 287 atuais)

**Interfaces:** Nenhuma — apenas documentacao e verificacao final.

- [ ] **Step 1: Atualizar `docs/jobs.md`**

Na secao "Sincronizacao SEFAZ (fora do framework `processing_jobs`)", adicionar apos o paragrafo existente (que termina com "...Ver `docs/api-contracts.md` (secao \"Sincronizacao SEFAZ\") e `docs/mapeamento-busca-xml-sefaz.md`."):

```markdown

`sefaz_evento_documento_novo_task` (por documento novo) e `sefaz_backfill_fiscal_task`
(ao fim de cada `sefaz_sync_empresa_task`, por empresa) transportam documentos
`direcao='emitida'` para as tabelas Fiscal via `SefazFiscalTransportService` —
tambem best-effort, sem `job_id`/`processing_jobs`. Falha nao derruba o sync;
o documento fica pendente (`sefaz.documentos.processado_fiscal_em IS NULL`) ate
a proxima tentativa. Ver `docs/superpowers/specs/2026-08-18-sefaz-fiscal-transport-design.md`.
```

- [ ] **Step 2: Atualizar `docs/api-contracts.md`**

Na linha 283 atual (`- Response (\`SefazDocumentoListResponse\`): ... \`manifestacao_status\`, \`criado_em\`, \`atualizado_em\`).`), adicionar `processado_fiscal_em` ao final da lista de campos, antes do fechamento de parenteses:

```markdown
- Response (`SefazDocumentoListResponse`): `total`, `limit`, `offset`, `resultados` (lista de `SefazDocumentoResponse`: `id`, `chave_acesso`, `tipo_documento`, `direcao`, `cnpj_emitente`, `cnpj_destinatario`, `nsu`, `data_emissao`, `valor_total`, `situacao`, `manifestacao_status`, `criado_em`, `atualizado_em`, `processado_fiscal_em`).
```

Na linha 287 atual (bloco de `GET /api/sefaz/documentos/{documento_id}`), adicionar uma frase apos a descricao existente:

```markdown
- Response (`SefazDocumentoDetalheResponse`): campos de `SefazDocumentoResponse` (inclui `processado_fiscal_em`, preenchido somente para `direcao='emitida'` apos o transporte para o Fiscal) + `xml_armazenado_base64` (`nfeProc` completo em base64, quando disponivel; `null` para `resNFe`/`resEvento` sem manifestacao).
```

- [ ] **Step 3: Rodar suite completa de testes SEFAZ (regressao)**

Run (de dentro de `API/`): `.\.venv-local\Scripts\python.exe -m pytest app\tests -k sefaz -q`
Expected: todos os testes passam, sem regressao nos fluxos existentes (`sincronizar_empresa`, `distribuicao_dfe_client`, `manifestacao`, `routes`, `documentos_repository`, `fiscal_transport_service`, `database_schema`).

- [ ] **Step 4: Rodar suite completa backend (regressao ampla)**

Run (de dentro de `API/`): `.\.venv-local\Scripts\python.exe -m pytest app\tests -q`
Expected: todos os testes passam, sem regressao em `nfe`/`process_nfe` (o `ProcessarNFeService.executar_xmls_importados` nao foi alterado, so passou a ter um novo chamador).

- [ ] **Step 5: Commit**

```bash
git add docs/jobs.md docs/api-contracts.md
git commit -m "docs(sefaz): documenta transporte automatico de itens emitida para o Fiscal"
```
