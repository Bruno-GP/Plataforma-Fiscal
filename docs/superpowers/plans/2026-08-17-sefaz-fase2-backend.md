# SEFAZ Fase 2 — Backend (FastAPI + Celery) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar o backend do módulo Sincronização SEFAZ (`NFeDistribuicaoDFe`): domínio puro
(regras de `cStat` e parsing de documentos), serviços (criptografia de certificado, cadastro de
certificado, cliente `distDFeInt`, orquestração de sincronização, manifestação do destinatário),
repositories sobre o schema `sefaz` (já criado na Fase 1), tasks Celery (`sefaz_sync_diario_task` +
`sefaz_sync_empresa_task`) e rotas FastAPI (`/api/sefaz/*`).

**Architecture:** Camadas `api -> services -> repositories -> domain`, mesmo padrão de
`docs/backend-architecture.md`. `distribuicao_dfe_client.py` é o único arquivo que importa
`nfelib`/`erpbrasil.*` (ADR 0001) — todo o resto do módulo depende só do contrato dele
(`RespostaDistribuicao`, `DocumentoBruto`). Sem SQLAlchemy ORM — `psycopg` raw SQL com
`row_factory=dict_row`, mesmo padrão de `app/repositories/conta_azul/` e `app/repositories/jobs_repository.py`.

**Tech Stack:** FastAPI, Celery 5.4, `psycopg[binary]==3.2.1`, `cryptography==43.0.1`, `nfelib`,
`erpbrasil.edoc`, `erpbrasil.assinatura` (versões exatas fixadas na Task 1).

## Global Constraints

- Sem SQLAlchemy ORM/models — só SQL cru (`op.execute`/`psycopg`), conforme
  `docs/backend-architecture.md` e o restante do backend.
- `empresa_id` é `BIGINT` (FK pra `public.empresas.id`) em toda tabela `sefaz.*` — já assim na
  migration da Fase 1 (`API/app/alembic/versions/20260814_0013_sefaz_schema.py`, mergeada em `dev`).
- Campos de CNPJ são `VARCHAR(20)` (CNPJ alfanumérico, NT 2026.004, vigente desde 2026-07-31) —
  usar `normalizar_cnpj` de `app.services.nfe.empresa_service` pra qualquer comparação/normalização,
  nunca comparar string bruta sem normalizar.
- `chave_acesso` é `VARCHAR(44)`.
- Rotas nunca aceitam `{empresa_id}` no path — sempre `current_user.empresa_id` via
  `Depends(require_company_scope)` (`app.core.security`), mesmo padrão de
  `app/api/conta_azul/routes.py`.
- Services não levantam `HTTPException` em código novo (`docs/backend-error-handling.md`) —
  levantam `ValueError`/exceções de domínio próprias, convertidas em `HTTPException` só na rota.
- Repositories nunca importam FastAPI, nunca levantam `HTTPException`, sempre usam
  `app.services.nfe.postres_config.carregar_config_postgres()` +
  `opcoes_conexao_postgres()` pra conectar (schema `sefaz` vive no mesmo banco de
  `public.empresas`, banco "NFe" do projeto) — mesmo padrão de `CompanyProfileService._connect()`
  (`app/services/company_profile_service.py:26-35`) e `JobsRepository._connect()`
  (`app/repositories/jobs_repository.py:34-42`).
- Certificado (`.pfx`/`.p12`) e senha nunca aparecem em log, exceção ou resposta de API — só
  bytes cifrados (Fernet) trafegam fora de memória volátil. Chave de cifra própria
  `SEFAZ_CERT_ENCRYPTION_KEY`, nunca reaproveita `CONTAAZUL_TOKEN_ENCRYPTION_KEY`.
- Testes de rota usam a fixture `client` de `API/app/tests/conftest.py` (usuário anônimo
  `empresa_id=1`, `cnpj="12345678000190"`) e fazem `monkeypatch` das classes de service/repository
  no ponto de uso dentro de `app.api.sefaz.routes`, mesmo padrão de
  `API/app/tests/test_conta_azul_callback.py`.
- Testes de repository são gated por Postgres real (`migrated_db`/`test_database_url` de
  `conftest.py`) — `SKIPPED` sem `PLATAFORMA_FISCAL_TEST_DATABASE_URL` apontando pra banco com
  `test`/`teste` no nome, mesmo padrão de `API/app/tests/test_conta_azul_integracoes_repository.py`.
- Testes de service/task/domínio nunca tocam rede real nem Postgres real — tudo via
  `monkeypatch`/fakes no ponto de uso, mesmo padrão de `API/app/tests/test_conta_azul_task.py` e
  `API/app/tests/test_conta_azul_crypto.py`.
- Indentação de 4 espaços (padrão de `app/core`, `app/repositories`, `app/workers`, `app/tests` —
  a maioria do backend; alguns arquivos legados de `nfe`/`conta_azul` usam 2 espaços, não é
  convenção a seguir em código novo).
- Fila Celery nova `sefaz`, somando-se a `default`/`nfe`/`sped`/`conta_azul` já registradas em
  `app/workers/celery_app.py`.
- Todo parsing de XML vindo da SEFAZ (fonte externa: `distDFeInt`, `resNFe`/`resEvento`/`nfeProc`
  de terceiros) usa `defusedxml.ElementTree`, nunca `xml.etree.ElementTree` puro — o parser
  stdlib é vulnerável a XXE/billion-laughs por padrão. `app/domain/nfe/xml_reader.py` (código
  legado, fora do escopo deste plano) ainda usa `xml.etree.ElementTree` cru; não é convenção a
  seguir em código novo.

---

### Task 1: Dependências (`nfelib`, `erpbrasil.*`) e variável de ambiente

**Files:**
- Modify: `API/app/requirements.txt`
- Modify: `API/app/.env.example`
- Modify: `API/app/.env` (local, não versionado — só pra desenvolvimento)

**Interfaces:**
- Produces: bibliotecas instaladas no `.venv-local`, disponíveis pras Tasks 6 e 7
  (`distribuicao_dfe_client.py` e testes de `certificado_service.py`, que usa
  `cryptography.hazmat.primitives.serialization.pkcs12`, já disponível via `cryptography==43.0.1`
  já pinada).

ADR 0001 (`docs/adr/0001-sefaz-distribuicao-dfe-biblioteca.md`) decidiu `nfelib` +
`erpbrasil.assinatura` + `erpbrasil.edoc`, com nota de que as versões devem ser fixadas exatas
(não usar `>=`), verificadas em 2026-08-14 como `nfelib` 2.3.0 e `erpbrasil.edoc` 3.1.1. As
versões de `erpbrasil.assinatura`/`erpbrasil.base`/`erpbrasil.transmissao` e das transitivas
(`lxml`, `xsdata`, `signxml` ou equivalente) não estavam confirmadas na ADR — este task instala
sem pin primeiro pra descobrir a resolução real, depois fixa exato.

- [ ] **Step 1: Instalar as libs sem pin pra descobrir as versões resolvidas**

Run (Windows, venv local do projeto):
```powershell
cd API
.\.venv-local\Scripts\pip.exe install nfelib erpbrasil.edoc erpbrasil.assinatura defusedxml
```
Expected: instala sem erro. Se `erpbrasil.edoc`/`erpbrasil.assinatura` trouxerem
`erpbrasil.base`/`erpbrasil.transmissao` como dependência transitiva, elas aparecem instaladas
também (não precisa instalar à parte). `defusedxml` é adição independente da ADR 0001 — protege
contra XXE/billion-laughs no parsing de XML vindo da SEFAZ (fonte externa), usado nas Tasks 2 e 6.

- [ ] **Step 2: Capturar as versões exatas resolvidas**

Run:
```powershell
.\.venv-local\Scripts\pip.exe freeze | Select-String -Pattern "nfelib|erpbrasil|lxml|xsdata|signxml|zeep|defusedxml"
```
Expected: uma linha `pacote==versao` por dependência — anotar a saída completa, ela vira o
conteúdo do Step 3.

- [ ] **Step 3: Fixar as versões exatas em `requirements.txt`**

Abrir `API/app/requirements.txt` e adicionar, logo após a linha `cryptography==43.0.1`, uma linha
por pacote capturado no Step 2 (formato `pacote==versao`, sem `>=` solto — convenção do arquivo,
ver ADR 0001). Exemplo de forma (substituir pelos valores reais do Step 2):
```
nfelib==2.3.0
erpbrasil.edoc==3.1.1
erpbrasil.assinatura==<versao-capturada>
erpbrasil.base==<versao-capturada>
erpbrasil.transmissao==<versao-capturada>
lxml==<versao-capturada>
xsdata==<versao-capturada>
defusedxml==<versao-capturada>
```

- [ ] **Step 4: Reinstalar a partir do `requirements.txt` fixado pra confirmar reprodutibilidade**

Run:
```powershell
.\.venv-local\Scripts\pip.exe install -r app\requirements.txt
```
Expected: sem erro, sem downgrade/upgrade de nada (já está tudo na versão pinada).

- [ ] **Step 5: Adicionar a variável de ambiente da chave de cifra do certificado**

Em `API/app/.env.example`, adicionar logo após a linha `CONTAAZUL_TOKEN_ENCRYPTION_KEY=`:
```
SEFAZ_CERT_ENCRYPTION_KEY=
```

No `API/app/.env` local (arquivo real, não versionado), gerar uma chave e preencher:
```powershell
.\.venv-local\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Copiar a saída pra linha `SEFAZ_CERT_ENCRYPTION_KEY=` do `.env` local.

- [ ] **Step 6: Confirmar que a suíte rápida ainda passa (sanity check, nada mudou em código)**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests -q`
Expected: mesmo resultado de antes desta task (instalar dependência não quebra teste existente).

- [ ] **Step 7: Commit**

```bash
git add API/app/requirements.txt API/app/.env.example
git commit -m "chore(sefaz): adiciona dependencias nfelib/erpbrasil e SEFAZ_CERT_ENCRYPTION_KEY"
```

---

### Task 2: Domínio puro — `cstat_rules.py` e `doc_parser.py`

**Files:**
- Create: `API/app/domain/sefaz/cstat_rules.py`
- Create: `API/app/domain/sefaz/doc_parser.py`
- Test: `API/app/tests/test_sefaz_cstat_rules.py`
- Test: `API/app/tests/test_sefaz_doc_parser.py`

**Interfaces:**
- Produces:
  - `decidir_paginacao(cstat: int, iteracao_atual: int) -> DecisaoPaginacao` (campos:
    `continuar: bool`, `bloqueado: bool`, `motivo: str`) — usado pela Task 7
    (`sefaz_distribuicao_service.py`).
  - `MAX_ITERACOES_PAGINACAO = 20` (constante) — usado pela Task 7.
  - `parse_documento(tipo_documento: str, xml_bytes: bytes) -> DocumentoParseado` (campos:
    `chave_acesso: str`, `tipo_documento: str`, `cnpj_emitente: str`,
    `cnpj_destinatario: str | None`, `data_emissao: str | None`, `valor_total: str | None`,
    `situacao: str | None`, `tipo_evento: str | None`, `protocolo: str | None`) — usado pela
    Task 7. `tipo_documento` aceita `"resNFe"`, `"resEvento"`, `"nfeProc"`.
  - `calcular_direcao(cnpj_emitente: str, cnpj_empresa: str) -> str` (retorna `"emitida"` ou
    `"recebida"`) — usado pela Task 7.
  - `DocumentoParseInvalidoError(ValueError)` — usado pela Task 7 pra pular documento malformado
    sem derrubar a sincronização inteira.

- [ ] **Step 1: Escrever os testes de `cstat_rules` (falham — módulo não existe)**

Criar `API/app/tests/test_sefaz_cstat_rules.py`:
```python
from app.domain.sefaz.cstat_rules import MAX_ITERACOES_PAGINACAO, decidir_paginacao


def test_cstat_137_para_sem_bloqueio():
    decisao = decidir_paginacao(cstat=137, iteracao_atual=1)
    assert decisao.continuar is False
    assert decisao.bloqueado is False
    assert decisao.motivo == "sem_novidade"


def test_cstat_138_continua_paginando_abaixo_do_teto():
    decisao = decidir_paginacao(cstat=138, iteracao_atual=1)
    assert decisao.continuar is True
    assert decisao.bloqueado is False


def test_cstat_138_no_teto_de_iteracoes_para_sem_bloqueio():
    decisao = decidir_paginacao(cstat=138, iteracao_atual=MAX_ITERACOES_PAGINACAO)
    assert decisao.continuar is False
    assert decisao.bloqueado is False
    assert decisao.motivo == "teto_iteracoes"


def test_cstat_656_bloqueia():
    decisao = decidir_paginacao(cstat=656, iteracao_atual=1)
    assert decisao.continuar is False
    assert decisao.bloqueado is True
    assert decisao.motivo == "consumo_indevido"


def test_cstat_desconhecido_para_com_motivo_descritivo():
    decisao = decidir_paginacao(cstat=999, iteracao_atual=1)
    assert decisao.continuar is False
    assert decisao.bloqueado is False
    assert "999" in decisao.motivo
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_cstat_rules.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.domain.sefaz.cstat_rules'`.

- [ ] **Step 3: Implementar `cstat_rules.py`**

Criar `API/app/domain/sefaz/cstat_rules.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

CSTAT_NENHUM_DOCUMENTO_NOVO = 137
CSTAT_DOCUMENTO_LOCALIZADO = 138
CSTAT_CONSUMO_INDEVIDO = 656

MAX_ITERACOES_PAGINACAO = 20


@dataclass(frozen=True)
class DecisaoPaginacao:
    continuar: bool
    bloqueado: bool
    motivo: str


def decidir_paginacao(cstat: int, iteracao_atual: int) -> DecisaoPaginacao:
    if cstat == CSTAT_CONSUMO_INDEVIDO:
        return DecisaoPaginacao(continuar=False, bloqueado=True, motivo="consumo_indevido")

    if cstat == CSTAT_NENHUM_DOCUMENTO_NOVO:
        return DecisaoPaginacao(continuar=False, bloqueado=False, motivo="sem_novidade")

    if cstat == CSTAT_DOCUMENTO_LOCALIZADO:
        if iteracao_atual >= MAX_ITERACOES_PAGINACAO:
            return DecisaoPaginacao(continuar=False, bloqueado=False, motivo="teto_iteracoes")
        return DecisaoPaginacao(continuar=True, bloqueado=False, motivo="documento_localizado")

    return DecisaoPaginacao(continuar=False, bloqueado=False, motivo=f"cstat_desconhecido_{cstat}")
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_cstat_rules.py -v`
Expected: PASS (5 testes).

- [ ] **Step 5: Escrever os testes de `doc_parser` (falham — módulo não existe)**

Criar `API/app/tests/test_sefaz_doc_parser.py`:
```python
import pytest

from app.domain.sefaz.doc_parser import (
    DocumentoParseInvalidoError,
    calcular_direcao,
    parse_documento,
)

NS = 'xmlns="http://www.portalfiscal.inf.br/nfe"'

RES_NFE_XML = f"""<resNFe {NS}>
    <chNFe>35260812345678000190550010000000011234567890</chNFe>
    <CNPJ>12345678000190</CNPJ>
    <xNome>EMPRESA EMITENTE LTDA</xNome>
    <IE>123456789</IE>
    <dhEmi>2026-08-01T10:00:00-03:00</dhEmi>
    <tpNF>1</tpNF>
    <vNF>1234.56</vNF>
    <digVal>abc123</digVal>
    <dhRecbto>2026-08-01T10:05:00-03:00</dhRecbto>
    <nProt>135260000000001</nProt>
    <cSitNFe>1</cSitNFe>
</resNFe>"""

RES_EVENTO_XML = f"""<resEvento {NS}>
    <chNFe>35260812345678000190550010000000011234567890</chNFe>
    <CNPJ>98765432000199</CNPJ>
    <dhEvento>2026-08-02T09:00:00-03:00</dhEvento>
    <tpEvento>110111</tpEvento>
    <nSeqEvento>1</nSeqEvento>
    <sitNFe>1</sitNFe>
    <xEvento>Cancelamento</xEvento>
    <dhRecbto>2026-08-02T09:01:00-03:00</dhRecbto>
    <nProt>135260000000002</nProt>
</resEvento>"""

NFE_PROC_XML = f"""<nfeProc {NS} versao="4.00">
    <NFe {NS}>
        <infNFe Id="NFe35260812345678000190550010000000011234567890" versao="4.00">
            <ide><dhEmi>2026-08-01T10:00:00-03:00</dhEmi></ide>
            <emit><CNPJ>12345678000190</CNPJ></emit>
            <dest><CNPJ>98765432000199</CNPJ></dest>
            <total><ICMSTot><vNF>1234.56</vNF></ICMSTot></total>
        </infNFe>
    </NFe>
    <protNFe {NS}>
        <infProt>
            <cStat>100</cStat>
            <nProt>135260000000003</nProt>
        </infProt>
    </protNFe>
</nfeProc>"""


def test_parse_res_nfe():
    doc = parse_documento("resNFe", RES_NFE_XML.encode("utf-8"))
    assert doc.chave_acesso == "35260812345678000190550010000000011234567890"
    assert doc.tipo_documento == "resNFe"
    assert doc.cnpj_emitente == "12345678000190"
    assert doc.cnpj_destinatario is None
    assert doc.data_emissao == "2026-08-01T10:00:00-03:00"
    assert doc.valor_total == "1234.56"
    assert doc.situacao == "autorizada"
    assert doc.protocolo == "135260000000001"


def test_parse_res_evento():
    doc = parse_documento("resEvento", RES_EVENTO_XML.encode("utf-8"))
    assert doc.chave_acesso == "35260812345678000190550010000000011234567890"
    assert doc.tipo_documento == "resEvento"
    assert doc.cnpj_emitente == "98765432000199"
    assert doc.tipo_evento == "110111"
    assert doc.valor_total is None
    assert doc.situacao is None


def test_parse_nfe_proc():
    doc = parse_documento("nfeProc", NFE_PROC_XML.encode("utf-8"))
    assert doc.chave_acesso == "35260812345678000190550010000000011234567890"
    assert doc.tipo_documento == "nfeProc"
    assert doc.cnpj_emitente == "12345678000190"
    assert doc.cnpj_destinatario == "98765432000199"
    assert doc.valor_total == "1234.56"
    assert doc.situacao == "autorizada"


def test_parse_documento_tipo_nao_suportado_falha():
    with pytest.raises(DocumentoParseInvalidoError, match="nao suportado"):
        parse_documento("outroSchema", b"<qualquer/>")


def test_parse_documento_xml_invalido_falha():
    with pytest.raises(DocumentoParseInvalidoError, match="XML invalido"):
        parse_documento("resNFe", b"<nao-fecha>")


def test_parse_res_nfe_sem_chave_falha():
    xml_sem_chave = f'<resNFe {NS}><CNPJ>12345678000190</CNPJ></resNFe>'
    with pytest.raises(DocumentoParseInvalidoError, match="chNFe"):
        parse_documento("resNFe", xml_sem_chave.encode("utf-8"))


def test_calcular_direcao_emitida_quando_cnpj_bate():
    assert calcular_direcao("12345678000190", "12345678000190") == "emitida"


def test_calcular_direcao_recebida_quando_cnpj_diferente():
    assert calcular_direcao("12345678000190", "98765432000199") == "recebida"
```

- [ ] **Step 6: Rodar e confirmar que falha**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_doc_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.domain.sefaz.doc_parser'`.

- [ ] **Step 7: Implementar `doc_parser.py`**

Criar `API/app/domain/sefaz/doc_parser.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from defusedxml import ElementTree as ET

NFE_NAMESPACE = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

SITUACAO_POR_CSITNFE = {
    "1": "autorizada",
    "2": "cancelada",
    "3": "denegada",
}

SITUACAO_POR_CSTAT_PROTOCOLO = {
    "100": "autorizada",
    "101": "cancelada",
    "151": "cancelada",
    "110": "denegada",
    "301": "denegada",
    "302": "denegada",
}


class DocumentoParseInvalidoError(ValueError):
    pass


@dataclass(frozen=True)
class DocumentoParseado:
    chave_acesso: str
    tipo_documento: str
    cnpj_emitente: str
    cnpj_destinatario: str | None
    data_emissao: str | None
    valor_total: str | None
    situacao: str | None
    tipo_evento: str | None
    protocolo: str | None


def _texto(elemento: ET.Element | None) -> str | None:
    if elemento is None or elemento.text is None:
        return None
    valor = elemento.text.strip()
    return valor or None


def _parse_res_nfe(raiz: ET.Element) -> DocumentoParseado:
    chave = _texto(raiz.find("nfe:chNFe", NFE_NAMESPACE))
    if not chave:
        raise DocumentoParseInvalidoError("resNFe sem chNFe.")

    cnpj_emitente = _texto(raiz.find("nfe:CNPJ", NFE_NAMESPACE)) or _texto(
        raiz.find("nfe:CPF", NFE_NAMESPACE)
    )
    if not cnpj_emitente:
        raise DocumentoParseInvalidoError(f"resNFe {chave} sem CNPJ/CPF do emitente.")

    csit_nfe = _texto(raiz.find("nfe:cSitNFe", NFE_NAMESPACE))

    return DocumentoParseado(
        chave_acesso=chave,
        tipo_documento="resNFe",
        cnpj_emitente=cnpj_emitente,
        cnpj_destinatario=None,
        data_emissao=_texto(raiz.find("nfe:dhEmi", NFE_NAMESPACE)),
        valor_total=_texto(raiz.find("nfe:vNF", NFE_NAMESPACE)),
        situacao=SITUACAO_POR_CSITNFE.get(csit_nfe or "", None),
        tipo_evento=None,
        protocolo=_texto(raiz.find("nfe:nProt", NFE_NAMESPACE)),
    )


def _parse_res_evento(raiz: ET.Element) -> DocumentoParseado:
    chave = _texto(raiz.find("nfe:chNFe", NFE_NAMESPACE))
    if not chave:
        raise DocumentoParseInvalidoError("resEvento sem chNFe.")

    cnpj_emitente = _texto(raiz.find("nfe:CNPJ", NFE_NAMESPACE)) or _texto(
        raiz.find("nfe:CPF", NFE_NAMESPACE)
    )
    if not cnpj_emitente:
        raise DocumentoParseInvalidoError(f"resEvento {chave} sem CNPJ/CPF do autor.")

    return DocumentoParseado(
        chave_acesso=chave,
        tipo_documento="resEvento",
        cnpj_emitente=cnpj_emitente,
        cnpj_destinatario=None,
        data_emissao=_texto(raiz.find("nfe:dhEvento", NFE_NAMESPACE)),
        valor_total=None,
        situacao=None,
        tipo_evento=_texto(raiz.find("nfe:tpEvento", NFE_NAMESPACE)),
        protocolo=_texto(raiz.find("nfe:nProt", NFE_NAMESPACE)),
    )


def _parse_nfe_proc(raiz: ET.Element) -> DocumentoParseado:
    inf_nfe = raiz.find("nfe:NFe/nfe:infNFe", NFE_NAMESPACE)
    if inf_nfe is None:
        raise DocumentoParseInvalidoError("nfeProc sem NFe/infNFe.")

    id_attr = inf_nfe.get("Id", "")
    chave = id_attr[3:] if id_attr.startswith("NFe") else id_attr
    if len(chave) != 44:
        raise DocumentoParseInvalidoError(f"nfeProc com chave de acesso invalida: {id_attr!r}.")

    cnpj_emitente = _texto(inf_nfe.find("nfe:emit/nfe:CNPJ", NFE_NAMESPACE)) or _texto(
        inf_nfe.find("nfe:emit/nfe:CPF", NFE_NAMESPACE)
    )
    if not cnpj_emitente:
        raise DocumentoParseInvalidoError(f"nfeProc {chave} sem CNPJ/CPF do emitente.")

    cnpj_destinatario = _texto(inf_nfe.find("nfe:dest/nfe:CNPJ", NFE_NAMESPACE)) or _texto(
        inf_nfe.find("nfe:dest/nfe:CPF", NFE_NAMESPACE)
    )

    protocolo = _texto(raiz.find("nfe:protNFe/nfe:infProt/nfe:nProt", NFE_NAMESPACE))
    cstat_protocolo = _texto(raiz.find("nfe:protNFe/nfe:infProt/nfe:cStat", NFE_NAMESPACE))

    return DocumentoParseado(
        chave_acesso=chave,
        tipo_documento="nfeProc",
        cnpj_emitente=cnpj_emitente,
        cnpj_destinatario=cnpj_destinatario,
        data_emissao=_texto(inf_nfe.find("nfe:ide/nfe:dhEmi", NFE_NAMESPACE)),
        valor_total=_texto(inf_nfe.find("nfe:total/nfe:ICMSTot/nfe:vNF", NFE_NAMESPACE)),
        situacao=SITUACAO_POR_CSTAT_PROTOCOLO.get(cstat_protocolo or "", None),
        tipo_evento=None,
        protocolo=protocolo,
    )


_PARSERS = {
    "resNFe": _parse_res_nfe,
    "resEvento": _parse_res_evento,
    "nfeProc": _parse_nfe_proc,
}


def parse_documento(tipo_documento: str, xml_bytes: bytes) -> DocumentoParseado:
    parser = _PARSERS.get(tipo_documento)
    if parser is None:
        raise DocumentoParseInvalidoError(f"Tipo de documento nao suportado: {tipo_documento!r}.")

    try:
        raiz = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise DocumentoParseInvalidoError(f"XML invalido para {tipo_documento}: {exc}") from exc

    return parser(raiz)


def calcular_direcao(cnpj_emitente: str, cnpj_empresa: str) -> str:
    return "emitida" if cnpj_emitente.strip() == cnpj_empresa.strip() else "recebida"
```

- [ ] **Step 8: Rodar e confirmar que passa**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_doc_parser.py -v`
Expected: PASS (9 testes).

- [ ] **Step 9: Commit**

```bash
git add API/app/domain/sefaz/cstat_rules.py API/app/domain/sefaz/doc_parser.py \
  API/app/tests/test_sefaz_cstat_rules.py API/app/tests/test_sefaz_doc_parser.py
git commit -m "feat(sefaz): dominio puro cstat_rules e doc_parser"
```

---

### Task 3: `crypto_service.py` (Fernet, chave própria do SEFAZ)

**Files:**
- Create: `API/app/services/sefaz/crypto_service.py`
- Test: `API/app/tests/test_sefaz_crypto.py`

**Interfaces:**
- Consumes: variável de ambiente `SEFAZ_CERT_ENCRYPTION_KEY` (Task 1).
- Produces: `encrypt_bytes(value: bytes) -> bytes`, `decrypt_bytes(value: bytes) -> bytes`,
  `encrypt_text(value: str) -> str`, `decrypt_text(value: str) -> str` — usados pela Task 5
  (`certificado_service.py`).

- [ ] **Step 1: Escrever os testes (falham — módulo não existe)**

Criar `API/app/tests/test_sefaz_crypto.py`:
```python
import pytest
from cryptography.fernet import Fernet


def test_encrypt_decrypt_bytes_roundtrip(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", Fernet.generate_key().decode())

    from app.services.sefaz.crypto_service import decrypt_bytes, encrypt_bytes

    original = b"conteudo binario do certificado .pfx"
    ciphertext = encrypt_bytes(original)
    assert ciphertext != original
    assert decrypt_bytes(ciphertext) == original


def test_encrypt_decrypt_text_roundtrip(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", Fernet.generate_key().decode())

    from app.services.sefaz.crypto_service import decrypt_text, encrypt_text

    ciphertext = encrypt_text("senha-do-certificado")
    assert ciphertext != "senha-do-certificado"
    assert decrypt_text(ciphertext) == "senha-do-certificado"


def test_encrypt_sem_chave_configurada_falha(monkeypatch):
    monkeypatch.delenv("SEFAZ_CERT_ENCRYPTION_KEY", raising=False)

    from app.services.sefaz.crypto_service import encrypt_text

    with pytest.raises(RuntimeError, match="SEFAZ_CERT_ENCRYPTION_KEY"):
        encrypt_text("qualquer-coisa")


def test_decrypt_bytes_corrompido_falha(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", Fernet.generate_key().decode())

    from app.services.sefaz.crypto_service import decrypt_bytes

    with pytest.raises(ValueError, match="corrompido"):
        decrypt_bytes(b"nao-e-um-token-fernet-valido")


def test_decrypt_text_corrompido_falha(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", Fernet.generate_key().decode())

    from app.services.sefaz.crypto_service import decrypt_text

    with pytest.raises(ValueError, match="corrompida"):
        decrypt_text("nao-e-um-token-fernet-valido")
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_crypto.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implementar `crypto_service.py`**

Criar `API/app/services/sefaz/crypto_service.py`:
```python
from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken


def _fernet() -> Fernet:
    key = os.environ.get("SEFAZ_CERT_ENCRYPTION_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "SEFAZ_CERT_ENCRYPTION_KEY nao configurada. Gere uma com "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"`."
        )
    return Fernet(key.encode("utf-8"))


def encrypt_bytes(value: bytes) -> bytes:
    return _fernet().encrypt(value)


def decrypt_bytes(value: bytes) -> bytes:
    try:
        return _fernet().decrypt(value)
    except InvalidToken as exc:
        raise ValueError("Certificado SEFAZ corrompido ou chave de criptografia invalida.") from exc


def encrypt_text(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Senha do certificado SEFAZ corrompida ou chave de criptografia invalida.") from exc
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_crypto.py -v`
Expected: PASS (5 testes).

- [ ] **Step 5: Commit**

```bash
git add API/app/services/sefaz/crypto_service.py API/app/tests/test_sefaz_crypto.py
git commit -m "feat(sefaz): crypto_service com chave propria SEFAZ_CERT_ENCRYPTION_KEY"
```

---

### Task 4: Repositories (`certificados`, `nsu_controle`, `documentos`, `eventos`, `sync_log`)

**Files:**
- Create: `API/app/repositories/sefaz/certificados_repository.py`
- Create: `API/app/repositories/sefaz/nsu_controle_repository.py`
- Create: `API/app/repositories/sefaz/documentos_repository.py`
- Create: `API/app/repositories/sefaz/eventos_repository.py`
- Create: `API/app/repositories/sefaz/sync_log_repository.py`
- Test: `API/app/tests/test_sefaz_certificados_repository.py`
- Test: `API/app/tests/test_sefaz_nsu_controle_repository.py`
- Test: `API/app/tests/test_sefaz_documentos_repository.py`
- Test: `API/app/tests/test_sefaz_eventos_repository.py`
- Test: `API/app/tests/test_sefaz_sync_log_repository.py`

**Interfaces:**
- Consumes: `app.services.nfe.postres_config.carregar_config_postgres`/`opcoes_conexao_postgres`
  (já existentes); schema `sefaz.*` da migration da Fase 1 (já mergeada em `dev`).
- Produces (usados pelas Tasks 5, 7, 8, 9):
  - `CertificadosRepository`: `get_ativo(empresa_id) -> dict | None`,
    `inserir(*, empresa_id, arquivo_certificado, senha_criptografada, cnpj_titular, data_validade) -> int`,
    `listar_ativos_com_validade() -> list[dict]`.
  - `NsuControleRepository`: `obter(empresa_id, ambiente) -> dict | None`,
    `upsert_execucao(empresa_id, ambiente, ultimo_nsu, status_ultima_execucao) -> None`.
  - `DocumentosRepository`: `inserir_se_novo(**kwargs) -> bool` (idempotente por
    `(empresa_id, chave_acesso)`), `obter_por_chave(empresa_id, chave_acesso) -> dict | None`,
    `obter_por_id(empresa_id, documento_id) -> dict | None`,
    `atualizar_manifestacao(documento_id, manifestacao_status) -> None`,
    `listar(*, empresa_id, direcao=None, situacao=None, manifestacao_pendente=None, data_inicio=None, data_fim=None, limit=50, offset=0) -> tuple[int, list[dict]]`.
  - `EventosRepository`: `inserir(*, documento_id, empresa_id, tipo_evento, protocolo, status, payload_xml) -> int`,
    `listar_por_documento(documento_id) -> list[dict]`.
  - `SyncLogRepository`: `registrar(*, empresa_id, iniciado_em, finalizado_em, documentos_novos, nsu_inicial, nsu_final, status, erro_detalhe) -> int`,
    `listar(empresa_id, *, limit=50, offset=0) -> tuple[int, list[dict]]`.

Todos os testes desta task exigem `PLATAFORMA_FISCAL_TEST_DATABASE_URL` (Postgres descartável
com `test`/`teste` no nome) — sem isso, `SKIPPED` (mesmo padrão de
`test_conta_azul_integracoes_repository.py`).

- [ ] **Step 1: Escrever teste de `CertificadosRepository` (falha — módulo não existe)**

Criar `API/app/tests/test_sefaz_certificados_repository.py`:
```python
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
```

- [ ] **Step 2: Implementar `certificados_repository.py`**

Criar `API/app/repositories/sefaz/certificados_repository.py`:
```python
from __future__ import annotations

from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


class CertificadosRepository:
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

    def get_ativo(self, empresa_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM sefaz.certificados WHERE empresa_id = %s AND ativo = TRUE",
                    (empresa_id,),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def inserir(
        self,
        *,
        empresa_id: int,
        arquivo_certificado: bytes,
        senha_criptografada: str,
        cnpj_titular: str,
        data_validade: date,
    ) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE sefaz.certificados SET ativo = FALSE WHERE empresa_id = %s AND ativo = TRUE",
                    (empresa_id,),
                )
                cur.execute(
                    """
                    INSERT INTO sefaz.certificados
                        (empresa_id, arquivo_certificado, senha_criptografada, cnpj_titular, data_validade, ativo)
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                    RETURNING id
                    """,
                    (empresa_id, arquivo_certificado, senha_criptografada, cnpj_titular, data_validade),
                )
                new_id = cur.fetchone()["id"]
            conn.commit()
        return new_id

    def listar_ativos_com_validade(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, empresa_id, cnpj_titular, data_validade FROM sefaz.certificados WHERE ativo = TRUE"
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]
```

- [ ] **Step 3: Rodar teste de `CertificadosRepository`**

Run:
```powershell
$env:PLATAFORMA_FISCAL_TEST_DATABASE_URL = "postgresql://<usuario>:<senha>@localhost:<porta>/plataforma_fiscal_test"
cd API
.\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_certificados_repository.py -v
```
Expected: PASS (4 testes) se `PLATAFORMA_FISCAL_TEST_DATABASE_URL` estiver configurada;
`SKIPPED` caso contrário (ambiente sem Postgres descartável).

- [ ] **Step 4: Escrever teste de `NsuControleRepository`**

Criar `API/app/tests/test_sefaz_nsu_controle_repository.py`:
```python
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
    repo.upsert_execucao(empresa_id, ambiente=1, ultimo_nsu="000000000000010", status_ultima_execucao="sucesso")

    cursor = repo.obter(empresa_id, ambiente=1)
    assert cursor["ultimo_nsu"] == "000000000000010"
    assert cursor["status_ultima_execucao"] == "sucesso"

    repo.upsert_execucao(empresa_id, ambiente=1, ultimo_nsu="000000000000025", status_ultima_execucao="sucesso")
    cursor = repo.obter(empresa_id, ambiente=1)
    assert cursor["ultimo_nsu"] == "000000000000025"


def test_ambientes_diferentes_tem_cursores_independentes(migrated_db, empresa_id):
    from app.repositories.sefaz.nsu_controle_repository import NsuControleRepository

    repo = NsuControleRepository()
    repo.upsert_execucao(empresa_id, ambiente=1, ultimo_nsu="000000000000001", status_ultima_execucao="sucesso")
    repo.upsert_execucao(empresa_id, ambiente=2, ultimo_nsu="000000000000099", status_ultima_execucao="sucesso")

    assert repo.obter(empresa_id, ambiente=1)["ultimo_nsu"] == "000000000000001"
    assert repo.obter(empresa_id, ambiente=2)["ultimo_nsu"] == "000000000000099"
```

- [ ] **Step 5: Implementar `nsu_controle_repository.py`**

Criar `API/app/repositories/sefaz/nsu_controle_repository.py`:
```python
from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


class NsuControleRepository:
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

    def obter(self, empresa_id: int, ambiente: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM sefaz.nsu_controle WHERE empresa_id = %s AND ambiente = %s",
                    (empresa_id, ambiente),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def upsert_execucao(
        self, empresa_id: int, ambiente: int, ultimo_nsu: str, status_ultima_execucao: str
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sefaz.nsu_controle
                        (empresa_id, ambiente, ultimo_nsu, ultima_execucao_em, status_ultima_execucao)
                    VALUES (%s, %s, %s, NOW(), %s)
                    ON CONFLICT (empresa_id, ambiente) DO UPDATE
                    SET ultimo_nsu = EXCLUDED.ultimo_nsu,
                        ultima_execucao_em = NOW(),
                        status_ultima_execucao = EXCLUDED.status_ultima_execucao
                    """,
                    (empresa_id, ambiente, ultimo_nsu, status_ultima_execucao),
                )
            conn.commit()
```

- [ ] **Step 6: Rodar teste de `NsuControleRepository`**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_nsu_controle_repository.py -v`
Expected: PASS (3 testes) ou `SKIPPED` sem Postgres de teste.

- [ ] **Step 7: Escrever teste de `DocumentosRepository`**

Criar `API/app/tests/test_sefaz_documentos_repository.py`:
```python
from datetime import date, datetime, timedelta, timezone

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
        repo, empresa_id, chave_acesso="3333333333333333333333333333333333333333",
        direcao="recebida", manifestacao_status="pendente",
    )
    _inserir_documento(
        repo, empresa_id, chave_acesso="4444444444444444444444444444444444444444",
        direcao="emitida", manifestacao_status=None,
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
            repo, empresa_id, chave_acesso=f"555555555555555555555555555555555555555{indice}"
        )

    total, pagina_1 = repo.listar(empresa_id=empresa_id, limit=2, offset=0)
    total_2, pagina_2 = repo.listar(empresa_id=empresa_id, limit=2, offset=2)

    assert total == 3
    assert total_2 == 3
    assert len(pagina_1) == 2
    assert len(pagina_2) == 1
```

- [ ] **Step 8: Implementar `documentos_repository.py`**

Criar `API/app/repositories/sefaz/documentos_repository.py`:
```python
from __future__ import annotations

from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


class DocumentosRepository:
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

    def inserir_se_novo(
        self,
        *,
        empresa_id: int,
        chave_acesso: str,
        tipo_documento: str,
        direcao: str,
        cnpj_emitente: str,
        cnpj_destinatario: str | None,
        nsu: str,
        data_emissao,
        valor_total: str | None,
        situacao: str | None,
        xml_armazenado: bytes | None,
        manifestacao_status: str | None,
    ) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sefaz.documentos (
                        empresa_id, chave_acesso, tipo_documento, direcao, cnpj_emitente,
                        cnpj_destinatario, nsu, data_emissao, valor_total, situacao,
                        xml_armazenado, manifestacao_status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (empresa_id, chave_acesso) DO NOTHING
                    """,
                    (
                        empresa_id, chave_acesso, tipo_documento, direcao, cnpj_emitente,
                        cnpj_destinatario, nsu, data_emissao, valor_total, situacao,
                        xml_armazenado, manifestacao_status,
                    ),
                )
                inseriu = cur.rowcount == 1
            conn.commit()
        return inseriu

    def obter_por_chave(self, empresa_id: int, chave_acesso: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM sefaz.documentos WHERE empresa_id = %s AND chave_acesso = %s",
                    (empresa_id, chave_acesso),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def obter_por_id(self, empresa_id: int, documento_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM sefaz.documentos WHERE empresa_id = %s AND id = %s",
                    (empresa_id, documento_id),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def atualizar_manifestacao(self, documento_id: int, manifestacao_status: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE sefaz.documentos SET manifestacao_status = %s, atualizado_em = NOW() WHERE id = %s",
                    (manifestacao_status, documento_id),
                )
            conn.commit()

    def listar(
        self,
        *,
        empresa_id: int,
        direcao: str | None = None,
        situacao: str | None = None,
        manifestacao_pendente: bool | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[dict[str, Any]]]:
        filters: list[str] = ["empresa_id = %s"]
        params: list[Any] = [empresa_id]

        if direcao:
            filters.append("direcao = %s")
            params.append(direcao)
        if situacao:
            filters.append("situacao = %s")
            params.append(situacao)
        if manifestacao_pendente:
            filters.append("manifestacao_status = 'pendente'")
        if data_inicio:
            filters.append("data_emissao >= %s")
            params.append(data_inicio)
        if data_fim:
            filters.append("data_emissao < (%s::date + INTERVAL '1 day')")
            params.append(data_fim)

        where_clause = f"WHERE {' AND '.join(filters)}"

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) AS total FROM sefaz.documentos {where_clause}", params)
                total = cur.fetchone()["total"]

                cur.execute(
                    f"""
                    SELECT * FROM sefaz.documentos
                    {where_clause}
                    ORDER BY data_emissao DESC NULLS LAST, id DESC
                    LIMIT %s OFFSET %s
                    """,
                    params + [limit, offset],
                )
                rows = [dict(row) for row in cur.fetchall()]

        return total, rows
```

- [ ] **Step 9: Rodar teste de `DocumentosRepository`**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_documentos_repository.py -v`
Expected: PASS (6 testes) ou `SKIPPED` sem Postgres de teste.

- [ ] **Step 10: Escrever teste de `EventosRepository`**

Criar `API/app/tests/test_sefaz_eventos_repository.py`:
```python
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
```

- [ ] **Step 11: Implementar `eventos_repository.py`**

Criar `API/app/repositories/sefaz/eventos_repository.py`:
```python
from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


class EventosRepository:
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

    def inserir(
        self,
        *,
        documento_id: int,
        empresa_id: int,
        tipo_evento: str,
        protocolo: str | None,
        status: str,
        payload_xml: str | None,
    ) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sefaz.eventos (documento_id, empresa_id, tipo_evento, protocolo, status, payload_xml)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (documento_id, empresa_id, tipo_evento, protocolo, status, payload_xml),
                )
                new_id = cur.fetchone()["id"]
            conn.commit()
        return new_id

    def listar_por_documento(self, documento_id: int) -> list[dict]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM sefaz.eventos WHERE documento_id = %s ORDER BY criado_em DESC",
                    (documento_id,),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]
```

- [ ] **Step 12: Rodar teste de `EventosRepository`**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_eventos_repository.py -v`
Expected: PASS (1 teste) ou `SKIPPED` sem Postgres de teste.

- [ ] **Step 13: Escrever teste de `SyncLogRepository`**

Criar `API/app/tests/test_sefaz_sync_log_repository.py`:
```python
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
        empresa_id=empresa_id, iniciado_em=base - timedelta(days=1), finalizado_em=base - timedelta(days=1),
        documentos_novos=1, nsu_inicial="0", nsu_final="1", status="sucesso", erro_detalhe=None,
    )
    repo.registrar(
        empresa_id=empresa_id, iniciado_em=base, finalizado_em=base,
        documentos_novos=2, nsu_inicial="1", nsu_final="2", status="sucesso", erro_detalhe=None,
    )

    _, rows = repo.listar(empresa_id, limit=10, offset=0)
    assert rows[0]["documentos_novos"] == 2
    assert rows[1]["documentos_novos"] == 1
```

- [ ] **Step 14: Implementar `sync_log_repository.py`**

Criar `API/app/repositories/sefaz/sync_log_repository.py`:
```python
from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


class SyncLogRepository:
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

    def registrar(
        self,
        *,
        empresa_id: int,
        iniciado_em: datetime,
        finalizado_em: datetime | None,
        documentos_novos: int,
        nsu_inicial: str | None,
        nsu_final: str | None,
        status: str,
        erro_detalhe: str | None,
    ) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sefaz.sync_log (
                        empresa_id, iniciado_em, finalizado_em, documentos_novos,
                        nsu_inicial, nsu_final, status, erro_detalhe
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        empresa_id, iniciado_em, finalizado_em, documentos_novos,
                        nsu_inicial, nsu_final, status, erro_detalhe,
                    ),
                )
                new_id = cur.fetchone()["id"]
            conn.commit()
        return new_id

    def listar(self, empresa_id: int, *, limit: int = 50, offset: int = 0) -> tuple[int, list[dict[str, Any]]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) AS total FROM sefaz.sync_log WHERE empresa_id = %s",
                    (empresa_id,),
                )
                total = cur.fetchone()["total"]

                cur.execute(
                    """
                    SELECT * FROM sefaz.sync_log
                    WHERE empresa_id = %s
                    ORDER BY iniciado_em DESC
                    LIMIT %s OFFSET %s
                    """,
                    (empresa_id, limit, offset),
                )
                rows = [dict(row) for row in cur.fetchall()]

        return total, rows
```

- [ ] **Step 15: Rodar teste de `SyncLogRepository`**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_sync_log_repository.py -v`
Expected: PASS (2 testes) ou `SKIPPED` sem Postgres de teste.

- [ ] **Step 16: Rodar a suíte de repositories inteira de uma vez**

Run:
```powershell
cd API
.\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_certificados_repository.py app/tests/test_sefaz_nsu_controle_repository.py app/tests/test_sefaz_documentos_repository.py app/tests/test_sefaz_eventos_repository.py app/tests/test_sefaz_sync_log_repository.py -v
```
Expected: todos PASS (ou todos SKIPPED juntos, se sem Postgres de teste — nunca mistura de FAIL).

- [ ] **Step 17: Commit**

```bash
git add API/app/repositories/sefaz/ API/app/tests/test_sefaz_certificados_repository.py \
  API/app/tests/test_sefaz_nsu_controle_repository.py API/app/tests/test_sefaz_documentos_repository.py \
  API/app/tests/test_sefaz_eventos_repository.py API/app/tests/test_sefaz_sync_log_repository.py
git commit -m "feat(sefaz): repositories certificados, nsu_controle, documentos, eventos, sync_log"
```

---

### Task 5: `certificado_service.py`

**Files:**
- Create: `API/app/services/sefaz/certificado_service.py`
- Test: `API/app/tests/test_sefaz_certificado_service.py`

**Interfaces:**
- Consumes: `CertificadosRepository` (Task 4), `encrypt_bytes`/`decrypt_bytes`/`encrypt_text`/
  `decrypt_text` (Task 3), `normalizar_cnpj` de `app.services.nfe.empresa_service` (já existente).
- Produces: `CertificadoService.cadastrar(empresa_id, arquivo_pfx, senha, cnpj_esperado) -> CertificadoStatus`,
  `CertificadoService.status(empresa_id) -> CertificadoStatus`,
  `CertificadoService.obter_credenciais_descriptografadas(empresa_id) -> tuple[bytes, str] | None`,
  `CertificadoInvalidoError(ValueError)` — usados pelas Tasks 7, 8, 10.
  `CertificadoStatus` (dataclass): `ativo: bool`, `cnpj_titular: str | None`,
  `data_validade: date | None`, `dias_restantes: int | None`.

- [ ] **Step 1: Escrever os testes (falham — módulo não existe)**

Criar `API/app/tests/test_sefaz_certificado_service.py`:
```python
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID


def _gerar_pfx(cn: str, dias_validade: int = 365) -> tuple[bytes, str]:
    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    agora = datetime.now(timezone.utc)
    certificado = (
        x509.CertificateBuilder()
        .subject_name(nome)
        .issuer_name(nome)
        .public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - timedelta(days=1))
        .not_valid_after(agora + timedelta(days=dias_validade))
        .sign(chave, hashes.SHA256())
    )
    senha = "senha-teste-123"
    pfx_bytes = pkcs12.serialize_key_and_certificates(
        name=b"certificado-teste",
        key=chave,
        cert=certificado,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(senha.encode("utf-8")),
    )
    return pfx_bytes, senha


class FakeCertificadosRepository:
    def __init__(self):
        self.inserido = None
        self.ativo = None

    def inserir(self, **kwargs):
        self.inserido = kwargs
        self.ativo = {**kwargs, "ativo": True}
        return 1

    def get_ativo(self, empresa_id):
        return self.ativo


def test_cadastrar_certificado_valido(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", "kAcqlvvVAAvv1pIbFOfR1CH8Aq2KgV1zqvvz4XjPz6c=")
    from app.services.sefaz.certificado_service import CertificadoService

    pfx_bytes, senha = _gerar_pfx("EMPRESA TESTE LTDA:12345678000190")
    repo = FakeCertificadosRepository()
    servico = CertificadoService(repository=repo)

    resultado = servico.cadastrar(empresa_id=1, arquivo_pfx=pfx_bytes, senha=senha, cnpj_esperado="12345678000190")

    assert resultado.ativo is True
    assert resultado.cnpj_titular == "12345678000190"
    assert repo.inserido["cnpj_titular"] == "12345678000190"
    assert repo.inserido["arquivo_certificado"] != pfx_bytes
    assert repo.inserido["senha_criptografada"] != senha


def test_cadastrar_senha_incorreta_falha(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", "kAcqlvvVAAvv1pIbFOfR1CH8Aq2KgV1zqvvz4XjPz6c=")
    from app.services.sefaz.certificado_service import CertificadoInvalidoError, CertificadoService

    pfx_bytes, _ = _gerar_pfx("EMPRESA TESTE LTDA:12345678000190")
    servico = CertificadoService(repository=FakeCertificadosRepository())

    with pytest.raises(CertificadoInvalidoError, match="senha incorreta"):
        servico.cadastrar(empresa_id=1, arquivo_pfx=pfx_bytes, senha="senha-errada", cnpj_esperado="12345678000190")


def test_cadastrar_certificado_vencido_falha(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", "kAcqlvvVAAvv1pIbFOfR1CH8Aq2KgV1zqvvz4XjPz6c=")
    from app.services.sefaz.certificado_service import CertificadoInvalidoError, CertificadoService

    pfx_bytes, senha = _gerar_pfx("EMPRESA TESTE LTDA:12345678000190", dias_validade=-10)
    servico = CertificadoService(repository=FakeCertificadosRepository())

    with pytest.raises(CertificadoInvalidoError, match="vencido"):
        servico.cadastrar(empresa_id=1, arquivo_pfx=pfx_bytes, senha=senha, cnpj_esperado="12345678000190")


def test_cadastrar_cnpj_do_certificado_diferente_da_empresa_falha(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", "kAcqlvvVAAvv1pIbFOfR1CH8Aq2KgV1zqvvz4XjPz6c=")
    from app.services.sefaz.certificado_service import CertificadoInvalidoError, CertificadoService

    pfx_bytes, senha = _gerar_pfx("EMPRESA TESTE LTDA:12345678000190")
    servico = CertificadoService(repository=FakeCertificadosRepository())

    with pytest.raises(CertificadoInvalidoError, match="CNPJ"):
        servico.cadastrar(empresa_id=1, arquivo_pfx=pfx_bytes, senha=senha, cnpj_esperado="98765432000199")


def test_status_sem_certificado_retorna_inativo():
    from app.services.sefaz.certificado_service import CertificadoService

    servico = CertificadoService(repository=FakeCertificadosRepository())
    resultado = servico.status(empresa_id=1)

    assert resultado.ativo is False
    assert resultado.cnpj_titular is None


def test_obter_credenciais_descriptografadas_roundtrip(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", "kAcqlvvVAAvv1pIbFOfR1CH8Aq2KgV1zqvvz4XjPz6c=")
    from app.services.sefaz.certificado_service import CertificadoService

    pfx_bytes, senha = _gerar_pfx("EMPRESA TESTE LTDA:12345678000190")
    repo = FakeCertificadosRepository()
    servico = CertificadoService(repository=repo)
    servico.cadastrar(empresa_id=1, arquivo_pfx=pfx_bytes, senha=senha, cnpj_esperado="12345678000190")

    credenciais = servico.obter_credenciais_descriptografadas(empresa_id=1)
    assert credenciais == (pfx_bytes, senha)


def test_obter_credenciais_sem_certificado_retorna_none():
    from app.services.sefaz.certificado_service import CertificadoService

    servico = CertificadoService(repository=FakeCertificadosRepository())
    assert servico.obter_credenciais_descriptografadas(empresa_id=1) is None
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_certificado_service.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implementar `certificado_service.py`**

Criar `API/app/services/sefaz/certificado_service.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from app.repositories.sefaz.certificados_repository import CertificadosRepository
from app.services.nfe.empresa_service import normalizar_cnpj
from app.services.sefaz.crypto_service import decrypt_bytes, decrypt_text, encrypt_bytes, encrypt_text


class CertificadoInvalidoError(ValueError):
    pass


@dataclass(frozen=True)
class CertificadoStatus:
    ativo: bool
    cnpj_titular: str | None
    data_validade: date | None
    dias_restantes: int | None


class CertificadoService:
    def __init__(self, repository: CertificadosRepository | None = None) -> None:
        self.repository = repository or CertificadosRepository()

    def _extrair_cnpj_titular(self, certificado) -> str:
        atributos = certificado.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if not atributos:
            raise CertificadoInvalidoError("Certificado sem Common Name (CN) no titular.")

        cn = atributos[0].value
        partes = cn.rsplit(":", 1)
        if len(partes) != 2 or not partes[1].strip():
            raise CertificadoInvalidoError(
                "Certificado nao segue o padrao ICP-Brasil (CN esperado 'NOME:CNPJ')."
            )
        return normalizar_cnpj(partes[1].strip())

    def cadastrar(
        self, empresa_id: int, arquivo_pfx: bytes, senha: str, cnpj_esperado: str
    ) -> CertificadoStatus:
        try:
            chave, certificado, _ = pkcs12.load_key_and_certificates(arquivo_pfx, senha.encode("utf-8"))
        except ValueError as exc:
            raise CertificadoInvalidoError(
                "Nao foi possivel abrir o certificado: senha incorreta ou arquivo .pfx/.p12 invalido."
            ) from exc

        if chave is None or certificado is None:
            raise CertificadoInvalidoError("Certificado .pfx/.p12 sem chave privada ou sem certificado.")

        data_validade = certificado.not_valid_after_utc.date()
        if data_validade < datetime.now(timezone.utc).date():
            raise CertificadoInvalidoError(f"Certificado vencido em {data_validade.isoformat()}.")

        cnpj_titular = self._extrair_cnpj_titular(certificado)
        if cnpj_titular != normalizar_cnpj(cnpj_esperado):
            raise CertificadoInvalidoError(
                f"Certificado pertence ao CNPJ {cnpj_titular}, diferente da empresa logada."
            )

        self.repository.inserir(
            empresa_id=empresa_id,
            arquivo_certificado=encrypt_bytes(arquivo_pfx),
            senha_criptografada=encrypt_text(senha),
            cnpj_titular=cnpj_titular,
            data_validade=data_validade,
        )

        return CertificadoStatus(
            ativo=True,
            cnpj_titular=cnpj_titular,
            data_validade=data_validade,
            dias_restantes=(data_validade - datetime.now(timezone.utc).date()).days,
        )

    def status(self, empresa_id: int) -> CertificadoStatus:
        registro = self.repository.get_ativo(empresa_id)
        if not registro:
            return CertificadoStatus(ativo=False, cnpj_titular=None, data_validade=None, dias_restantes=None)

        data_validade = registro["data_validade"]
        return CertificadoStatus(
            ativo=True,
            cnpj_titular=registro["cnpj_titular"],
            data_validade=data_validade,
            dias_restantes=(data_validade - datetime.now(timezone.utc).date()).days,
        )

    def obter_credenciais_descriptografadas(self, empresa_id: int) -> tuple[bytes, str] | None:
        """Usado só pelo worker de sync -- nunca exposto via API."""
        registro = self.repository.get_ativo(empresa_id)
        if not registro:
            return None

        arquivo_certificado = registro["arquivo_certificado"]
        if hasattr(arquivo_certificado, "tobytes"):
            arquivo_certificado = arquivo_certificado.tobytes()

        return (
            decrypt_bytes(bytes(arquivo_certificado)),
            decrypt_text(registro["senha_criptografada"]),
        )
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_certificado_service.py -v`
Expected: PASS (7 testes).

- [ ] **Step 5: Commit**

```bash
git add API/app/services/sefaz/certificado_service.py API/app/tests/test_sefaz_certificado_service.py
git commit -m "feat(sefaz): certificado_service com validacao pkcs12 e cifra Fernet"
```

---

### Task 6: `distribuicao_dfe_client.py`

**Files:**
- Create: `API/app/services/sefaz/distribuicao_dfe_client.py`
- Test: `API/app/tests/test_sefaz_distribuicao_dfe_client.py`

**Interfaces:**
- Consumes: `nfelib`, `erpbrasil.assinatura`, `erpbrasil.edoc` (Task 1) — único arquivo do
  módulo que importa essas libs (ADR 0001).
- Produces: `DistribuicaoDFeClient(certificado_pfx, senha, cnpj, ambiente, uf_autor="AN")`,
  método `.consultar(ultimo_nsu: str) -> RespostaDistribuicao`;
  `RespostaDistribuicao` (dataclass): `cstat: int`, `ultimo_nsu: str`, `max_nsu: str`,
  `documentos: list[DocumentoBruto]`; `DocumentoBruto` (dataclass): `schema: str` (`"resNFe"` |
  `"resEvento"` | `"nfeProc"`), `nsu: str`, `xml_bytes: bytes`;
  `SefazIndisponivelError(ConnectionError)` (falha transitória de rede/SOAP -- propaga pro
  Celery `autoretry_for`), `SefazRespostaInvalidaError(RuntimeError)` (resposta malformada) —
  usados pela Task 7.

Este arquivo tem uma parte 100% testável sem rede (decodificação `docZip`, parsing da resposta
`distDFeInt`, orquestração de erro) e uma parte que só pode ser validada com certificado real
contra o ambiente de homologação da SEFAZ (`_montar_transmissor`, que fala de fato com
`nfelib`/`erpbrasil.edoc`) — essa segunda parte fica isolada num método privado, testada só por
inspeção manual/homologação (fora do escopo de teste automatizado, mesmo critério de "nunca rede
real" do restante da suíte).

- [ ] **Step 1: Escrever os testes da parte pura (decodificação e parsing) — falham, módulo não existe**

Criar `API/app/tests/test_sefaz_distribuicao_dfe_client.py`:
```python
import base64
import gzip

import pytest


NS = 'xmlns="http://www.portalfiscal.inf.br/nfe"'


def _doc_zip(schema: str, nsu: str, xml_interno: str) -> str:
    comprimido = gzip.compress(xml_interno.encode("utf-8"))
    return base64.b64encode(comprimido).decode("ascii")


def test_decodificar_doc_zip_roundtrip():
    from app.services.sefaz.distribuicao_dfe_client import _decodificar_doc_zip

    original = b"<resNFe>conteudo</resNFe>"
    codificado = base64.b64encode(gzip.compress(original)).decode("ascii")

    assert _decodificar_doc_zip(codificado) == original


def test_decodificar_doc_zip_invalido_falha():
    from app.services.sefaz.distribuicao_dfe_client import SefazRespostaInvalidaError, _decodificar_doc_zip

    with pytest.raises(SefazRespostaInvalidaError, match="docZip"):
        _decodificar_doc_zip("nao-e-base64-valido-!!!")


def test_parse_resposta_com_documentos():
    from app.services.sefaz.distribuicao_dfe_client import _parse_resposta_distribuicao

    doc_zip_1 = _doc_zip("resNFe", "000000000000001", "<resNFe>a</resNFe>")
    doc_zip_2 = _doc_zip("resEvento", "000000000000002", "<resEvento>b</resEvento>")

    xml_resposta = f"""<retDistDFeInt {NS} versao="1.35">
        <tpAmb>1</tpAmb>
        <cStat>138</cStat>
        <xMotivo>Documento(s) localizado(s)</xMotivo>
        <ultNSU>000000000000002</ultNSU>
        <maxNSU>000000000000010</maxNSU>
        <loteDistDFeInt>
            <docZip NSU="000000000000001" schema="resNFe_v1.01.xsd">{doc_zip_1}</docZip>
            <docZip NSU="000000000000002" schema="resEvento_v1.00.xsd">{doc_zip_2}</docZip>
        </loteDistDFeInt>
    </retDistDFeInt>""".encode("utf-8")

    resposta = _parse_resposta_distribuicao(xml_resposta)

    assert resposta.cstat == 138
    assert resposta.ultimo_nsu == "000000000000002"
    assert resposta.max_nsu == "000000000000010"
    assert len(resposta.documentos) == 2
    assert resposta.documentos[0].schema == "resNFe"
    assert resposta.documentos[0].xml_bytes == b"<resNFe>a</resNFe>"
    assert resposta.documentos[1].schema == "resEvento"


def test_parse_resposta_sem_documentos_cstat_137():
    from app.services.sefaz.distribuicao_dfe_client import _parse_resposta_distribuicao

    xml_resposta = f"""<retDistDFeInt {NS} versao="1.35">
        <tpAmb>1</tpAmb>
        <cStat>137</cStat>
        <xMotivo>Nenhum documento localizado</xMotivo>
        <ultNSU>000000000000005</ultNSU>
        <maxNSU>000000000000005</maxNSU>
    </retDistDFeInt>""".encode("utf-8")

    resposta = _parse_resposta_distribuicao(xml_resposta)

    assert resposta.cstat == 137
    assert resposta.documentos == []


def test_parse_resposta_sem_cstat_falha():
    from app.services.sefaz.distribuicao_dfe_client import SefazRespostaInvalidaError, _parse_resposta_distribuicao

    with pytest.raises(SefazRespostaInvalidaError, match="cStat"):
        _parse_resposta_distribuicao(f'<retDistDFeInt {NS}></retDistDFeInt>'.encode("utf-8"))


def test_parse_resposta_xml_invalido_falha():
    from app.services.sefaz.distribuicao_dfe_client import SefazRespostaInvalidaError, _parse_resposta_distribuicao

    with pytest.raises(SefazRespostaInvalidaError):
        _parse_resposta_distribuicao(b"<nao-fecha>")


def test_consultar_sucesso_delega_para_transmissor(monkeypatch):
    from app.services.sefaz.distribuicao_dfe_client import DistribuicaoDFeClient

    doc_zip_1 = _doc_zip("resNFe", "000000000000001", "<resNFe>a</resNFe>")
    xml_resposta = f"""<retDistDFeInt {NS} versao="1.35">
        <tpAmb>1</tpAmb>
        <cStat>138</cStat>
        <ultNSU>000000000000001</ultNSU>
        <maxNSU>000000000000010</maxNSU>
        <loteDistDFeInt>
            <docZip NSU="000000000000001" schema="resNFe_v1.01.xsd">{doc_zip_1}</docZip>
        </loteDistDFeInt>
    </retDistDFeInt>""".encode("utf-8")

    class FakeRespostaSoap:
        content = xml_resposta

    class FakeTransmissor:
        def consulta_distribuicao(self, cnpj, ult_nsu):
            assert cnpj == "12345678000190"
            assert ult_nsu == "000000000000000"
            return FakeRespostaSoap()

    cliente = DistribuicaoDFeClient(b"pfx", "senha", "12345678000190", ambiente=1)
    monkeypatch.setattr(cliente, "_montar_transmissor", lambda: FakeTransmissor())

    resposta = cliente.consultar("000000000000000")

    assert resposta.cstat == 138
    assert len(resposta.documentos) == 1


def test_consultar_erro_de_transporte_vira_sefaz_indisponivel(monkeypatch):
    from app.services.sefaz.distribuicao_dfe_client import DistribuicaoDFeClient, SefazIndisponivelError

    class FakeTransmissorComErro:
        def consulta_distribuicao(self, cnpj, ult_nsu):
            raise TimeoutError("timeout na conexao com o Ambiente Nacional")

    cliente = DistribuicaoDFeClient(b"pfx", "senha", "12345678000190", ambiente=1)
    monkeypatch.setattr(cliente, "_montar_transmissor", lambda: FakeTransmissorComErro())

    with pytest.raises(SefazIndisponivelError, match="Falha ao consultar"):
        cliente.consultar("000000000000000")
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_distribuicao_dfe_client.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implementar `distribuicao_dfe_client.py`**

Criar `API/app/services/sefaz/distribuicao_dfe_client.py`:
```python
"""Unico modulo do dominio sefaz que importa nfelib/erpbrasil (ADR 0001, ver
docs/adr/0001-sefaz-distribuicao-dfe-biblioteca.md). O resto do dominio depende so do
contrato desta classe (RespostaDistribuicao/DocumentoBruto), nunca das libs diretamente."""

from __future__ import annotations

import base64
import gzip
from dataclasses import dataclass

from defusedxml import ElementTree as ET

AMBIENTE_PRODUCAO = 1
AMBIENTE_HOMOLOGACAO = 2

NFE_NAMESPACE = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

_SCHEMA_PREFIXO_PARA_TIPO = {
    "resNFe": "resNFe",
    "resEvento": "resEvento",
    "procNFe": "nfeProc",
}


class SefazIndisponivelError(ConnectionError):
    """SOAP/rede falhou ao consultar o Ambiente Nacional -- Celery faz autoretry
    (ver app/workers/sefaz_tasks.py, autoretry_for inclui ConnectionError)."""


class SefazRespostaInvalidaError(RuntimeError):
    pass


@dataclass(frozen=True)
class DocumentoBruto:
    schema: str
    nsu: str
    xml_bytes: bytes


@dataclass(frozen=True)
class RespostaDistribuicao:
    cstat: int
    ultimo_nsu: str
    max_nsu: str
    documentos: list[DocumentoBruto]


def _decodificar_doc_zip(doc_zip_base64: str) -> bytes:
    try:
        return gzip.decompress(base64.b64decode(doc_zip_base64))
    except (OSError, ValueError) as exc:
        raise SefazRespostaInvalidaError(f"docZip invalido: {exc}") from exc


def _texto(raiz: ET.Element, caminho: str) -> str | None:
    elemento = raiz.find(caminho, NFE_NAMESPACE)
    if elemento is None or elemento.text is None:
        return None
    valor = elemento.text.strip()
    return valor or None


def _parse_resposta_distribuicao(xml_resposta: bytes) -> RespostaDistribuicao:
    try:
        raiz = ET.fromstring(xml_resposta)
    except ET.ParseError as exc:
        raise SefazRespostaInvalidaError(f"Resposta distDFeInt nao e XML valido: {exc}") from exc

    cstat_texto = _texto(raiz, "nfe:cStat")
    if not cstat_texto:
        raise SefazRespostaInvalidaError("Resposta distDFeInt sem cStat.")

    documentos: list[DocumentoBruto] = []
    for doc_zip in raiz.findall("nfe:loteDistDFeInt/nfe:docZip", NFE_NAMESPACE):
        schema_attr = doc_zip.get("schema", "")
        prefixo = schema_attr.split("_")[0] if schema_attr else ""
        tipo_documento = _SCHEMA_PREFIXO_PARA_TIPO.get(prefixo, prefixo)
        documentos.append(
            DocumentoBruto(
                schema=tipo_documento,
                nsu=doc_zip.get("NSU", ""),
                xml_bytes=_decodificar_doc_zip(doc_zip.text or ""),
            )
        )

    return RespostaDistribuicao(
        cstat=int(cstat_texto),
        ultimo_nsu=_texto(raiz, "nfe:ultNSU") or "000000000000000",
        max_nsu=_texto(raiz, "nfe:maxNSU") or "000000000000000",
        documentos=documentos,
    )


class DistribuicaoDFeClient:
    """Consulta distDFeInt para uma empresa. Recebe o .pfx/.p12 ja descriptografado em
    memoria -- nunca grava em disco, nunca loga o conteudo (nem em excecao)."""

    def __init__(
        self, certificado_pfx: bytes, senha: str, cnpj: str, ambiente: int, uf_autor: str = "AN"
    ) -> None:
        self.certificado_pfx = certificado_pfx
        self.senha = senha
        self.cnpj = cnpj
        self.ambiente = ambiente
        self.uf_autor = uf_autor

    def _montar_transmissor(self):
        # ATENCAO: verificar contra a versao instalada antes de alterar --
        # `python -c "import erpbrasil.edoc as m; print(dir(m))"` e o modulo/classe
        # equivalente em nfelib -- a superficie publica exposta por este metodo deve
        # continuar sendo um objeto com `.consulta_distribuicao(cnpj, ult_nsu) -> resposta`
        # onde `resposta.content` e o XML bruto (bytes) do retDistDFeInt, para que
        # `consultar()` abaixo e os testes desta task continuem validos.
        from erpbrasil.assinatura.assinatura import Assinatura
        from erpbrasil.edoc.nfe import NFe as NFeTransmissor
        from erpbrasil.transmissao import TransmissaoSOAP
        import requests

        certificado = Assinatura(self.certificado_pfx, self.senha)
        sessao = requests.Session()
        transmissao = TransmissaoSOAP(certificado, sessao)
        return NFeTransmissor(transmissao=transmissao, ambiente=self.ambiente, uf=self.uf_autor)

    def consultar(self, ultimo_nsu: str) -> RespostaDistribuicao:
        transmissor = self._montar_transmissor()
        try:
            resposta_soap = transmissor.consulta_distribuicao(cnpj=self.cnpj, ult_nsu=ultimo_nsu)
        except Exception as exc:  # erpbrasil nao expoe hierarquia propria de excecao de rede
            raise SefazIndisponivelError(f"Falha ao consultar distDFeInt: {exc}") from exc

        return _parse_resposta_distribuicao(resposta_soap.content)
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_distribuicao_dfe_client.py -v`
Expected: PASS (8 testes) — cobre tudo exceto `_montar_transmissor`, que só é validável com
certificado real contra o ambiente de homologação (fora do escopo de teste automatizado).

- [ ] **Step 5: Confirmar que os imports de `nfelib`/`erpbrasil` resolvem no ambiente instalado**

Run:
```powershell
cd API
.\.venv-local\Scripts\python.exe -c "from erpbrasil.assinatura.assinatura import Assinatura; from erpbrasil.edoc.nfe import NFe; from erpbrasil.transmissao import TransmissaoSOAP; from defusedxml import ElementTree; print('imports ok')"
```
Expected: `imports ok`. Se algum import falhar (nome de classe diferente na versão instalada
capturada na Task 1), ajustar só dentro de `_montar_transmissor()` -- a assinatura pública de
`DistribuicaoDFeClient.consultar()` e os testes do Step 1 não mudam.

- [ ] **Step 6: Commit**

```bash
git add API/app/services/sefaz/distribuicao_dfe_client.py \
  API/app/tests/test_sefaz_distribuicao_dfe_client.py
git commit -m "feat(sefaz): distribuicao_dfe_client (unico ponto de import de nfelib/erpbrasil)"
```

---

### Task 7: `sefaz_distribuicao_service.py`

**Files:**
- Create: `API/app/services/sefaz/sefaz_distribuicao_service.py`
- Test: `API/app/tests/test_sefaz_distribuicao_service.py`

**Interfaces:**
- Consumes: `decidir_paginacao` (Task 2), `parse_documento`/`calcular_direcao`/
  `DocumentoParseInvalidoError` (Task 2), `DocumentosRepository`/`EventosRepository`/
  `NsuControleRepository`/`SyncLogRepository` (Task 4), `CertificadoService` (Task 5),
  `DistribuicaoDFeClient`/`RespostaDistribuicao`/`DocumentoBruto` (Task 6), `celery_app` de
  `app.workers.celery_app` (já existente).
- Produces: `SefazDistribuicaoService.sincronizar_empresa(empresa_id, cnpj_empresa, ambiente=1) -> ResultadoSincronizacao`,
  `CertificadoAusenteError(ValueError)`, `ResultadoSincronizacao` (dataclass): `status: str`
  (`"sucesso"` | `"erro"` | `"bloqueado"`), `documentos_novos: int`, `nsu_inicial: str`,
  `nsu_final: str`, `erro_detalhe: str | None` — usados pela Task 9 (`workers/sefaz_tasks.py`). A
  cada documento novo persistido, dispara (por nome, via `celery_app.send_task`, sem importar
  `workers/sefaz_tasks` -- services não dependem de workers) a task `"sefaz_evento_documento_novo_task"`
  (definida na Task 9) -- hook desacoplado pro módulo fiscal/NCM reagir no futuro (spec: "sem
  acoplar agora, só o hook"). Falha nesse disparo nunca derruba a sincronização.

- [ ] **Step 1: Escrever os testes (falham — módulo não existe)**

Criar `API/app/tests/test_sefaz_distribuicao_service.py`:
```python
from datetime import datetime, timezone

import pytest

from app.services.sefaz.distribuicao_dfe_client import DocumentoBruto, RespostaDistribuicao


class FakeCertificadoService:
    def __init__(self, credenciais=(b"pfx", "senha")):
        self.credenciais = credenciais

    def obter_credenciais_descriptografadas(self, empresa_id):
        return self.credenciais


class FakeNsuRepository:
    def __init__(self, ultimo_nsu=None):
        self.ultimo_nsu = ultimo_nsu
        self.execucoes = []

    def obter(self, empresa_id, ambiente):
        if self.ultimo_nsu is None:
            return None
        return {"ultimo_nsu": self.ultimo_nsu}

    def upsert_execucao(self, empresa_id, ambiente, ultimo_nsu, status_ultima_execucao):
        self.execucoes.append((empresa_id, ambiente, ultimo_nsu, status_ultima_execucao))


class FakeDocumentosRepository:
    def __init__(self):
        self.inseridos: list[dict] = []
        self.chaves_existentes: set[str] = set()

    def inserir_se_novo(self, **kwargs):
        if kwargs["chave_acesso"] in self.chaves_existentes:
            return False
        self.chaves_existentes.add(kwargs["chave_acesso"])
        self.inseridos.append(kwargs)
        return True

    def obter_por_chave(self, empresa_id, chave_acesso):
        for doc in self.inseridos:
            if doc["chave_acesso"] == chave_acesso:
                return {**doc, "id": 1}
        return None


class FakeEventosRepository:
    def __init__(self):
        self.inseridos: list[dict] = []

    def inserir(self, **kwargs):
        self.inseridos.append(kwargs)
        return len(self.inseridos)


class FakeSyncLogRepository:
    def __init__(self):
        self.registros: list[dict] = []

    def registrar(self, **kwargs):
        self.registros.append(kwargs)
        return len(self.registros)


RES_NFE_XML = (
    '<resNFe xmlns="http://www.portalfiscal.inf.br/nfe">'
    "<chNFe>35260812345678000190550010000000011234567890</chNFe>"
    "<CNPJ>98765432000199</CNPJ>"
    "<dhEmi>2026-08-01T10:00:00-03:00</dhEmi>"
    "<vNF>100.00</vNF>"
    "<cSitNFe>1</cSitNFe>"
    "</resNFe>"
).encode("utf-8")


def _servico(client_respostas, **overrides):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            self._respostas = iter(client_respostas)

        def consultar(self, ultimo_nsu):
            return next(self._respostas)

    from app.services.sefaz.sefaz_distribuicao_service import SefazDistribuicaoService

    kwargs = {
        "certificado_service": FakeCertificadoService(),
        "nsu_repository": FakeNsuRepository(),
        "documentos_repository": FakeDocumentosRepository(),
        "eventos_repository": FakeEventosRepository(),
        "sync_log_repository": FakeSyncLogRepository(),
        "client_factory": FakeClient,
    }
    kwargs.update(overrides)
    return SefazDistribuicaoService(**kwargs)


def test_cstat_137_para_sem_documentos_e_registra_sucesso():
    servico = _servico([RespostaDistribuicao(cstat=137, ultimo_nsu="10", max_nsu="10", documentos=[])])

    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert resultado.status == "sucesso"
    assert resultado.documentos_novos == 0
    assert servico.sync_log_repository.registros[0]["status"] == "sucesso"


def test_documento_novo_persistido_e_direcao_calculada():
    doc = DocumentoBruto(schema="resNFe", nsu="1", xml_bytes=RES_NFE_XML)
    servico = _servico([
        RespostaDistribuicao(cstat=137, ultimo_nsu="1", max_nsu="1", documentos=[doc]),
    ])

    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert resultado.documentos_novos == 1
    inserido = servico.documentos_repository.inseridos[0]
    assert inserido["direcao"] == "recebida"
    assert inserido["cnpj_emitente"] == "98765432000199"


def test_pagina_ate_cstat_137_apos_138():
    doc = DocumentoBruto(schema="resNFe", nsu="1", xml_bytes=RES_NFE_XML)
    servico = _servico([
        RespostaDistribuicao(cstat=138, ultimo_nsu="1", max_nsu="10", documentos=[doc]),
        RespostaDistribuicao(cstat=137, ultimo_nsu="1", max_nsu="10", documentos=[]),
    ])

    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert resultado.status == "sucesso"
    assert resultado.documentos_novos == 1


def test_cstat_656_marca_bloqueado_e_para():
    servico = _servico([RespostaDistribuicao(cstat=656, ultimo_nsu="5", max_nsu="5", documentos=[])])

    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert resultado.status == "bloqueado"
    assert "656" in resultado.erro_detalhe or "indevido" in resultado.erro_detalhe


def test_idempotencia_reprocessar_mesmo_documento_nao_duplica():
    doc = DocumentoBruto(schema="resNFe", nsu="1", xml_bytes=RES_NFE_XML)
    documentos_repo = FakeDocumentosRepository()
    documentos_repo.chaves_existentes.add("35260812345678000190550010000000011234567890")

    servico = _servico(
        [RespostaDistribuicao(cstat=137, ultimo_nsu="1", max_nsu="1", documentos=[doc])],
        documentos_repository=documentos_repo,
    )

    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert resultado.documentos_novos == 0


def test_certificado_ausente_leva_excecao():
    from app.services.sefaz.sefaz_distribuicao_service import CertificadoAusenteError

    servico = _servico([], certificado_service=FakeCertificadoService(credenciais=None))

    with pytest.raises(CertificadoAusenteError):
        servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")


def test_erro_durante_consulta_marca_sync_log_como_erro_e_propaga():
    class FakeClientComErro:
        def __init__(self, *args, **kwargs):
            pass

        def consultar(self, ultimo_nsu):
            raise ConnectionError("timeout")

    servico = _servico([], client_factory=FakeClientComErro)

    with pytest.raises(ConnectionError):
        servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert servico.sync_log_repository.registros[0]["status"] == "erro"


def test_documento_novo_dispara_evento_celery_por_nome(monkeypatch):
    from app.services.sefaz import sefaz_distribuicao_service as modulo

    chamadas = []
    monkeypatch.setattr(
        modulo.celery_app, "send_task", lambda name, args, queue: chamadas.append((name, args, queue))
    )

    doc = DocumentoBruto(schema="resNFe", nsu="1", xml_bytes=RES_NFE_XML)
    servico = _servico([RespostaDistribuicao(cstat=137, ultimo_nsu="1", max_nsu="1", documentos=[doc])])

    servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert chamadas == [
        (
            "sefaz_evento_documento_novo_task",
            [1, "35260812345678000190550010000000011234567890"],
            "sefaz",
        )
    ]


def test_falha_ao_disparar_evento_celery_nao_derruba_sincronizacao(monkeypatch):
    from app.services.sefaz import sefaz_distribuicao_service as modulo

    def _falha(*args, **kwargs):
        raise ConnectionError("broker indisponivel")

    monkeypatch.setattr(modulo.celery_app, "send_task", _falha)

    doc = DocumentoBruto(schema="resNFe", nsu="1", xml_bytes=RES_NFE_XML)
    servico = _servico([RespostaDistribuicao(cstat=137, ultimo_nsu="1", max_nsu="1", documentos=[doc])])

    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert resultado.status == "sucesso"
    assert resultado.documentos_novos == 1
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_distribuicao_service.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implementar `sefaz_distribuicao_service.py`**

Criar `API/app/services/sefaz/sefaz_distribuicao_service.py`:
```python
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.sefaz.cstat_rules import decidir_paginacao
from app.domain.sefaz.doc_parser import DocumentoParseInvalidoError, calcular_direcao, parse_documento
from app.repositories.sefaz.documentos_repository import DocumentosRepository
from app.repositories.sefaz.eventos_repository import EventosRepository
from app.repositories.sefaz.nsu_controle_repository import NsuControleRepository
from app.repositories.sefaz.sync_log_repository import SyncLogRepository
from app.services.sefaz.certificado_service import CertificadoService
from app.services.sefaz.distribuicao_dfe_client import DistribuicaoDFeClient
from app.workers.celery_app import celery_app

logger = logging.getLogger("services.sefaz")

NSU_INICIAL_PADRAO = "000000000000000"


class CertificadoAusenteError(ValueError):
    pass


@dataclass(frozen=True)
class ResultadoSincronizacao:
    status: str
    documentos_novos: int
    nsu_inicial: str
    nsu_final: str
    erro_detalhe: str | None = None


class SefazDistribuicaoService:
    def __init__(
        self,
        certificado_service: CertificadoService | None = None,
        nsu_repository: NsuControleRepository | None = None,
        documentos_repository: DocumentosRepository | None = None,
        eventos_repository: EventosRepository | None = None,
        sync_log_repository: SyncLogRepository | None = None,
        client_factory=DistribuicaoDFeClient,
    ) -> None:
        self.certificado_service = certificado_service or CertificadoService()
        self.nsu_repository = nsu_repository or NsuControleRepository()
        self.documentos_repository = documentos_repository or DocumentosRepository()
        self.eventos_repository = eventos_repository or EventosRepository()
        self.sync_log_repository = sync_log_repository or SyncLogRepository()
        self.client_factory = client_factory

    def sincronizar_empresa(
        self, empresa_id: int, cnpj_empresa: str, ambiente: int = 1
    ) -> ResultadoSincronizacao:
        iniciado_em = datetime.now(timezone.utc)

        credenciais = self.certificado_service.obter_credenciais_descriptografadas(empresa_id)
        if credenciais is None:
            raise CertificadoAusenteError(f"Empresa {empresa_id} nao possui certificado SEFAZ ativo.")
        certificado_pfx, senha = credenciais

        cursor = self.nsu_repository.obter(empresa_id, ambiente)
        nsu_inicial = cursor["ultimo_nsu"] if cursor else NSU_INICIAL_PADRAO
        ultimo_nsu = nsu_inicial

        cliente = self.client_factory(certificado_pfx, senha, cnpj_empresa, ambiente)
        documentos_novos = 0
        iteracao = 1
        status_final = "sucesso"
        erro_detalhe: str | None = None

        try:
            while True:
                resposta = cliente.consultar(ultimo_nsu)
                decisao = decidir_paginacao(resposta.cstat, iteracao)

                for documento_bruto in resposta.documentos:
                    documentos_novos += self._persistir_documento(empresa_id, cnpj_empresa, documento_bruto)

                ultimo_nsu = resposta.ultimo_nsu

                if decisao.bloqueado:
                    status_final = "bloqueado"
                    erro_detalhe = "Consumo indevido (cStat 656) -- aguardando janela de espera."
                    break
                if not decisao.continuar:
                    break
                iteracao += 1
        except Exception as exc:
            status_final = "erro"
            erro_detalhe = str(exc)
            logger.exception(
                "sefaz_sync_falhou", extra={"empresa_id": empresa_id, "iteracao": iteracao}
            )
            self.nsu_repository.upsert_execucao(empresa_id, ambiente, ultimo_nsu, status_final)
            self.sync_log_repository.registrar(
                empresa_id=empresa_id,
                iniciado_em=iniciado_em,
                finalizado_em=datetime.now(timezone.utc),
                documentos_novos=documentos_novos,
                nsu_inicial=nsu_inicial,
                nsu_final=ultimo_nsu,
                status=status_final,
                erro_detalhe=erro_detalhe,
            )
            raise

        self.nsu_repository.upsert_execucao(empresa_id, ambiente, ultimo_nsu, status_final)
        self.sync_log_repository.registrar(
            empresa_id=empresa_id,
            iniciado_em=iniciado_em,
            finalizado_em=datetime.now(timezone.utc),
            documentos_novos=documentos_novos,
            nsu_inicial=nsu_inicial,
            nsu_final=ultimo_nsu,
            status=status_final,
            erro_detalhe=erro_detalhe,
        )

        return ResultadoSincronizacao(
            status=status_final,
            documentos_novos=documentos_novos,
            nsu_inicial=nsu_inicial,
            nsu_final=ultimo_nsu,
            erro_detalhe=erro_detalhe,
        )

    def _persistir_documento(self, empresa_id: int, cnpj_empresa: str, documento_bruto) -> int:
        if documento_bruto.schema == "resEvento":
            self._persistir_evento(empresa_id, documento_bruto)
            return 0

        try:
            parseado = parse_documento(documento_bruto.schema, documento_bruto.xml_bytes)
        except DocumentoParseInvalidoError:
            logger.warning(
                "sefaz_documento_parse_invalido",
                extra={"empresa_id": empresa_id, "schema": documento_bruto.schema, "nsu": documento_bruto.nsu},
            )
            return 0

        direcao = calcular_direcao(parseado.cnpj_emitente, cnpj_empresa)
        inseriu = self.documentos_repository.inserir_se_novo(
            empresa_id=empresa_id,
            chave_acesso=parseado.chave_acesso,
            tipo_documento=parseado.tipo_documento,
            direcao=direcao,
            cnpj_emitente=parseado.cnpj_emitente,
            cnpj_destinatario=parseado.cnpj_destinatario,
            nsu=documento_bruto.nsu,
            data_emissao=parseado.data_emissao,
            valor_total=parseado.valor_total,
            situacao=parseado.situacao,
            xml_armazenado=documento_bruto.xml_bytes if documento_bruto.schema == "nfeProc" else None,
            manifestacao_status="pendente" if direcao == "recebida" else None,
        )
        if inseriu:
            self._publicar_evento_documento_novo(empresa_id, parseado.chave_acesso)
        return 1 if inseriu else 0

    def _publicar_evento_documento_novo(self, empresa_id: int, chave_acesso: str) -> None:
        """Hook desacoplado pro modulo fiscal/NCM reagir a documento novo no futuro --
        disparo por nome de task (sem importar workers/sefaz_tasks, mantendo services sem
        depender de workers -- so de celery_app, que e infraestrutura compartilhada). Falha
        aqui e best-effort e nunca derruba a sincronizacao."""
        try:
            celery_app.send_task(
                "sefaz_evento_documento_novo_task",
                args=[empresa_id, chave_acesso],
                queue="sefaz",
            )
        except Exception:
            logger.warning(
                "sefaz_publicar_evento_documento_novo_falhou",
                extra={"empresa_id": empresa_id, "chave_acesso": chave_acesso},
            )

    def _persistir_evento(self, empresa_id: int, documento_bruto) -> None:
        try:
            parseado = parse_documento("resEvento", documento_bruto.xml_bytes)
        except DocumentoParseInvalidoError:
            logger.warning(
                "sefaz_evento_parse_invalido", extra={"empresa_id": empresa_id, "nsu": documento_bruto.nsu}
            )
            return

        documento = self.documentos_repository.obter_por_chave(empresa_id, parseado.chave_acesso)
        if documento is None:
            logger.info(
                "sefaz_evento_sem_documento_correspondente",
                extra={"empresa_id": empresa_id, "chave_acesso": parseado.chave_acesso},
            )
            return

        self.eventos_repository.inserir(
            documento_id=documento["id"],
            empresa_id=empresa_id,
            tipo_evento=parseado.tipo_evento or "desconhecido",
            protocolo=parseado.protocolo,
            status="recebido",
            payload_xml=documento_bruto.xml_bytes.decode("utf-8", errors="replace"),
        )
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_distribuicao_service.py -v`
Expected: PASS (9 testes).

- [ ] **Step 5: Commit**

```bash
git add API/app/services/sefaz/sefaz_distribuicao_service.py \
  API/app/tests/test_sefaz_distribuicao_service.py
git commit -m "feat(sefaz): sefaz_distribuicao_service orquestra paginacao/persistencia/cstat"
```

---

### Task 8: `manifestacao_destinatario_service.py`

**Files:**
- Create: `API/app/services/sefaz/manifestacao_destinatario_service.py`
- Test: `API/app/tests/test_sefaz_manifestacao_service.py`

**Interfaces:**
- Consumes: `DocumentosRepository` (Task 4).
- Produces: `ManifestacaoDestinatarioService.manifestar(empresa_id, documento_id, tipo_manifestacao) -> dict`,
  `ManifestacaoDestinatarioService.listar_pendentes_proximas_do_prazo(empresa_id, dias_restantes_max=3) -> list[dict]`,
  `montar_texto_alerta_prazo(chave_acesso, dias_restantes) -> str`,
  `ManifestacaoInvalidaError(ValueError)`, `DocumentoNaoPertenceEmpresaError(ValueError)` — usados
  pela Task 10 (`api/sefaz/routes.py`).

- [ ] **Step 1: Escrever os testes (falham — módulo não existe)**

Criar `API/app/tests/test_sefaz_manifestacao_service.py`:
```python
from datetime import datetime, timedelta, timezone

import pytest


class FakeDocumentosRepository:
    def __init__(self, documentos: dict[int, dict]):
        self.documentos = documentos
        self.atualizados: list[tuple[int, str]] = []

    def obter_por_id(self, empresa_id, documento_id):
        doc = self.documentos.get(documento_id)
        if doc is None or doc.get("empresa_id") != empresa_id:
            return None
        return doc

    def atualizar_manifestacao(self, documento_id, manifestacao_status):
        self.atualizados.append((documento_id, manifestacao_status))

    def listar(self, *, empresa_id, manifestacao_pendente=None, limit=50, offset=0, **_ignorados):
        pendentes = [
            doc for doc in self.documentos.values()
            if doc["empresa_id"] == empresa_id and doc.get("manifestacao_status") == "pendente"
        ]
        return len(pendentes), pendentes


def test_manifestar_documento_recebido_atualiza_status():
    from app.services.sefaz.manifestacao_destinatario_service import ManifestacaoDestinatarioService

    repo = FakeDocumentosRepository({10: {"id": 10, "empresa_id": 1, "direcao": "recebida"}})
    servico = ManifestacaoDestinatarioService(documentos_repository=repo)

    resultado = servico.manifestar(empresa_id=1, documento_id=10, tipo_manifestacao="ciencia")

    assert resultado == {"documento_id": 10, "manifestacao_status": "ciencia"}
    assert repo.atualizados == [(10, "ciencia")]


def test_manifestar_tipo_invalido_recusa():
    from app.services.sefaz.manifestacao_destinatario_service import (
        ManifestacaoDestinatarioService,
        ManifestacaoInvalidaError,
    )

    repo = FakeDocumentosRepository({10: {"id": 10, "empresa_id": 1, "direcao": "recebida"}})
    servico = ManifestacaoDestinatarioService(documentos_repository=repo)

    with pytest.raises(ManifestacaoInvalidaError):
        servico.manifestar(empresa_id=1, documento_id=10, tipo_manifestacao="tipo-invalido")


def test_manifestar_documento_emitido_recusa():
    from app.services.sefaz.manifestacao_destinatario_service import (
        ManifestacaoDestinatarioService,
        ManifestacaoInvalidaError,
    )

    repo = FakeDocumentosRepository({10: {"id": 10, "empresa_id": 1, "direcao": "emitida"}})
    servico = ManifestacaoDestinatarioService(documentos_repository=repo)

    with pytest.raises(ManifestacaoInvalidaError, match="recebidos"):
        servico.manifestar(empresa_id=1, documento_id=10, tipo_manifestacao="ciencia")


def test_manifestar_documento_inexistente_ou_de_outra_empresa_recusa():
    from app.services.sefaz.manifestacao_destinatario_service import (
        DocumentoNaoPertenceEmpresaError,
        ManifestacaoDestinatarioService,
    )

    repo = FakeDocumentosRepository({10: {"id": 10, "empresa_id": 2, "direcao": "recebida"}})
    servico = ManifestacaoDestinatarioService(documentos_repository=repo)

    with pytest.raises(DocumentoNaoPertenceEmpresaError):
        servico.manifestar(empresa_id=1, documento_id=10, tipo_manifestacao="ciencia")


def test_listar_pendentes_proximas_do_prazo_filtra_por_dias_restantes():
    from app.services.sefaz.manifestacao_destinatario_service import (
        ManifestacaoDestinatarioService,
        PRAZO_MANIFESTACAO_DIAS,
    )

    hoje = datetime.now(timezone.utc)
    documentos = {
        1: {
            "id": 1, "empresa_id": 1, "manifestacao_status": "pendente",
            "data_emissao": hoje - timedelta(days=PRAZO_MANIFESTACAO_DIAS - 1),
        },
        2: {
            "id": 2, "empresa_id": 1, "manifestacao_status": "pendente",
            "data_emissao": hoje - timedelta(days=1),
        },
    }
    repo = FakeDocumentosRepository(documentos)
    servico = ManifestacaoDestinatarioService(documentos_repository=repo)

    alerta = servico.listar_pendentes_proximas_do_prazo(empresa_id=1, dias_restantes_max=3)

    assert len(alerta) == 1
    assert alerta[0]["id"] == 1


def test_montar_texto_alerta_prazo_vencido():
    from app.services.sefaz.manifestacao_destinatario_service import montar_texto_alerta_prazo

    texto = montar_texto_alerta_prazo("35260812345678000190550010000000011234567890", dias_restantes=0)
    assert "vencido" in texto


def test_montar_texto_alerta_prazo_nao_vencido():
    from app.services.sefaz.manifestacao_destinatario_service import montar_texto_alerta_prazo

    texto = montar_texto_alerta_prazo("35260812345678000190550010000000011234567890", dias_restantes=2)
    assert "2 dias" in texto
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_manifestacao_service.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implementar `manifestacao_destinatario_service.py`**

Criar `API/app/services/sefaz/manifestacao_destinatario_service.py`:
```python
from __future__ import annotations

from datetime import date, timedelta

from app.repositories.sefaz.documentos_repository import DocumentosRepository

MANIFESTACOES_VALIDAS = {"ciencia", "confirmada", "desconhecida", "nao_realizada"}
PRAZO_MANIFESTACAO_DIAS = 10


class ManifestacaoInvalidaError(ValueError):
    pass


class DocumentoNaoPertenceEmpresaError(ValueError):
    pass


def montar_texto_alerta_prazo(chave_acesso: str, dias_restantes: int) -> str:
    if dias_restantes <= 0:
        return (
            f"Documento {chave_acesso}: prazo de manifestacao do destinatario vencido. "
            "Manifeste-se o quanto antes para nao perder o direito ao credito."
        )

    plural = "dia" if dias_restantes == 1 else "dias"
    return (
        f"Documento {chave_acesso}: faltam {dias_restantes} {plural} para o prazo de "
        "manifestacao do destinatario."
    )


class ManifestacaoDestinatarioService:
    def __init__(self, documentos_repository: DocumentosRepository | None = None) -> None:
        self.documentos_repository = documentos_repository or DocumentosRepository()

    def manifestar(self, empresa_id: int, documento_id: int, tipo_manifestacao: str) -> dict:
        if tipo_manifestacao not in MANIFESTACOES_VALIDAS:
            raise ManifestacaoInvalidaError(
                f"Tipo de manifestacao invalido: {tipo_manifestacao!r}. "
                f"Esperado um de {sorted(MANIFESTACOES_VALIDAS)}."
            )

        documento = self.documentos_repository.obter_por_id(empresa_id, documento_id)
        if documento is None:
            raise DocumentoNaoPertenceEmpresaError(
                f"Documento {documento_id} nao encontrado para a empresa {empresa_id}."
            )
        if documento["direcao"] != "recebida":
            raise ManifestacaoInvalidaError("Manifestacao so se aplica a documentos recebidos.")

        # Envio do evento assinado ao SEFAZ reaproveita a mesma fronteira de
        # DistribuicaoDFeClient (Task 6) -- fica para quando o fluxo de emissao de evento
        # for conectado; por ora, persiste a intencao local (fonte de verdade da UI/consulta).
        self.documentos_repository.atualizar_manifestacao(documento_id, tipo_manifestacao)

        return {"documento_id": documento_id, "manifestacao_status": tipo_manifestacao}

    def listar_pendentes_proximas_do_prazo(
        self, empresa_id: int, dias_restantes_max: int = 3
    ) -> list[dict]:
        _, pendentes = self.documentos_repository.listar(
            empresa_id=empresa_id, manifestacao_pendente=True, limit=500, offset=0
        )
        hoje = date.today()
        alerta: list[dict] = []
        for documento in pendentes:
            data_emissao = documento.get("data_emissao")
            if not data_emissao:
                continue
            prazo_final = data_emissao.date() + timedelta(days=PRAZO_MANIFESTACAO_DIAS)
            dias_restantes = (prazo_final - hoje).days
            if dias_restantes <= dias_restantes_max:
                alerta.append({**documento, "dias_restantes_manifestacao": dias_restantes})
        return alerta
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_manifestacao_service.py -v`
Expected: PASS (7 testes).

- [ ] **Step 5: Commit**

```bash
git add API/app/services/sefaz/manifestacao_destinatario_service.py \
  API/app/tests/test_sefaz_manifestacao_service.py
git commit -m "feat(sefaz): manifestacao_destinatario_service"
```

---

### Task 9: `workers/sefaz_tasks.py` + registro no `celery_app.py`

**Files:**
- Create: `API/app/workers/sefaz_tasks.py`
- Modify: `API/app/workers/celery_app.py`
- Test: `API/app/tests/test_sefaz_task.py`

**Interfaces:**
- Consumes: `CertificadosRepository.listar_ativos_com_validade()` (Task 4),
  `SefazDistribuicaoService.sincronizar_empresa()` (Task 7).
- Produces: `sefaz_sync_diario_task` (Celery task, sem args, dispara uma
  `sefaz_sync_empresa_task` por certificado ativo), `sefaz_sync_empresa_task(empresa_id, cnpj_titular)`
  (Celery task, `autoretry_for=(ConnectionError, TimeoutError)`) — `sefaz_sync_empresa_task` é
  usado pela Task 10 (`POST /api/sefaz/sync`, disparado com `.apply_async`).
  `sefaz_evento_documento_novo_task(empresa_id, chave_acesso)` (Celery task registrada com esse
  nome exato -- é o alvo do `celery_app.send_task("sefaz_evento_documento_novo_task", ...)` da
  Task 7; por ora só loga, sem reação -- integração com o módulo fiscal/NCM fica pra um ciclo
  futuro, spec explicita isso em "Fora de escopo").

- [ ] **Step 1: Escrever os testes (falham — módulo não existe)**

Criar `API/app/tests/test_sefaz_task.py`:
```python
from app.services.sefaz.sefaz_distribuicao_service import ResultadoSincronizacao
from app.workers import sefaz_tasks


class FakeCertificadosRepository:
    def __init__(self, certificados):
        self._certificados = certificados

    def listar_ativos_com_validade(self):
        return self._certificados


def test_sync_diario_dispara_uma_task_por_certificado_ativo(monkeypatch):
    monkeypatch.setattr(
        sefaz_tasks,
        "_repositorio_certificados",
        lambda: FakeCertificadosRepository(
            [
                {"empresa_id": 1, "cnpj_titular": "11111111000191"},
                {"empresa_id": 2, "cnpj_titular": "22222222000192"},
            ]
        ),
    )
    chamadas = []
    monkeypatch.setattr(
        sefaz_tasks.sefaz_sync_empresa_task,
        "apply_async",
        lambda args, queue: chamadas.append((args, queue)),
    )

    resultado = sefaz_tasks.sefaz_sync_diario_task.run()

    assert resultado["status"] == "SUCCESS"
    assert resultado["empresas_disparadas"] == 2
    assert chamadas == [
        ([1, "11111111000191"], "sefaz"),
        ([2, "22222222000192"], "sefaz"),
    ]


def test_sync_diario_sem_certificados_dispara_zero():
    from app.workers import sefaz_tasks as modulo

    original = modulo._repositorio_certificados
    modulo._repositorio_certificados = lambda: FakeCertificadosRepository([])
    try:
        resultado = modulo.sefaz_sync_diario_task.run()
    finally:
        modulo._repositorio_certificados = original

    assert resultado == {"status": "SUCCESS", "empresas_disparadas": 0}


def test_sync_empresa_task_retorna_resultado_do_service(monkeypatch):
    monkeypatch.setattr(
        sefaz_tasks,
        "_sincronizar_empresa",
        lambda empresa_id, cnpj_titular: ResultadoSincronizacao(
            status="sucesso", documentos_novos=5, nsu_inicial="0", nsu_final="10"
        ),
    )

    resultado = sefaz_tasks.sefaz_sync_empresa_task.run(1, "11111111000191")

    assert resultado == {"status": "sucesso", "documentos_novos": 5, "empresa_id": 1}


def test_sync_empresa_task_propaga_excecao_para_autoretry(monkeypatch):
    import pytest

    def _levanta_erro_transiente(empresa_id, cnpj_titular):
        raise ConnectionError("Falha ao consultar distDFeInt: timeout")

    monkeypatch.setattr(sefaz_tasks, "_sincronizar_empresa", _levanta_erro_transiente)

    with pytest.raises(ConnectionError):
        sefaz_tasks.sefaz_sync_empresa_task.run(1, "11111111000191")


def test_evento_documento_novo_task_roda_sem_erro():
    resultado = sefaz_tasks.sefaz_evento_documento_novo_task.run(1, "35260812345678000190550010000000011234567890")

    assert resultado == {"status": "SUCCESS"}
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_task.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implementar `workers/sefaz_tasks.py`**

Criar `API/app/workers/sefaz_tasks.py`:
```python
from __future__ import annotations

import logging

from app.repositories.sefaz.certificados_repository import CertificadosRepository
from app.services.sefaz.sefaz_distribuicao_service import SefazDistribuicaoService
from app.workers.celery_app import celery_app

logger = logging.getLogger("workers.sefaz")

AMBIENTE_PRODUCAO = 1


def _repositorio_certificados() -> CertificadosRepository:
    return CertificadosRepository()


def _sincronizar_empresa(empresa_id: int, cnpj_titular: str):
    return SefazDistribuicaoService().sincronizar_empresa(empresa_id, cnpj_titular, ambiente=AMBIENTE_PRODUCAO)


@celery_app.task(
    name="sefaz_sync_empresa_task",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def sefaz_sync_empresa_task(empresa_id: int, cnpj_titular: str) -> dict:
    resultado = _sincronizar_empresa(empresa_id, cnpj_titular)
    return {
        "status": resultado.status,
        "documentos_novos": resultado.documentos_novos,
        "empresa_id": empresa_id,
    }


@celery_app.task(name="sefaz_sync_diario_task")
def sefaz_sync_diario_task() -> dict:
    """Roda diariamente (beat_schedule em celery_app.py): dispara uma task por empresa
    com certificado sefaz.certificados ativo -- falha de uma empresa nao trava as outras
    (mesmo padrao de conta_azul_tasks.sincronizar_kpis_conta_azul_task)."""
    certificados = _repositorio_certificados().listar_ativos_com_validade()
    disparados = 0
    for certificado in certificados:
        sefaz_sync_empresa_task.apply_async(
            args=[certificado["empresa_id"], certificado["cnpj_titular"]],
            queue="sefaz",
        )
        disparados += 1

    logger.info("sefaz_sync_diario_disparado", extra={"empresas": disparados})
    return {"status": "SUCCESS", "empresas_disparadas": disparados}


@celery_app.task(name="sefaz_evento_documento_novo_task")
def sefaz_evento_documento_novo_task(empresa_id: int, chave_acesso: str) -> dict:
    """Hook disparado por SefazDistribuicaoService a cada documento novo persistido
    (app/services/sefaz/sefaz_distribuicao_service.py, _publicar_evento_documento_novo).
    Por ora so loga -- integracao com o modulo fiscal/NCM fica pra um ciclo futuro (fora de
    escopo desta fase, ver docs/superpowers/specs/2026-08-14-sefaz-distribuicao-dfe-design.md)."""
    logger.info(
        "sefaz_documento_novo_evento_recebido",
        extra={"empresa_id": empresa_id, "chave_acesso": chave_acesso},
    )
    return {"status": "SUCCESS"}
```

- [ ] **Step 4: Registrar a fila `sefaz`, a task e o beat schedule em `celery_app.py`**

Em `API/app/workers/celery_app.py`, no bloco `include=[...]` (linha ~53-58), adicionar
`"app.workers.sefaz_tasks",` à lista.

No bloco `task_queues=(...)` (linha ~70-75), adicionar após a linha da fila `conta_azul`:
```python
            Queue("sefaz", Exchange("sefaz"), routing_key="sefaz"),
```

No bloco `beat_schedule={...}` (linha ~76-87), adicionar uma nova entrada (horário 2:00,
antes do Conta Azul às 3:00 e de indicadores às 4:00, pra não competir no mesmo minuto):
```python
            "sefaz-sync-diario": {
                "task": "sefaz_sync_diario_task",
                "schedule": crontab(hour=2, minute=0),
                "options": {"queue": "sefaz"},
            },
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_task.py -v`
Expected: PASS (5 testes).

- [ ] **Step 6: Confirmar que a suíte rápida inteira continua passando**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests -q`
Expected: nenhuma regressão nos testes já existentes (`celery_app.py` só ganhou uma fila/task/beat
novos, não alterou nada existente).

- [ ] **Step 7: Commit**

```bash
git add API/app/workers/sefaz_tasks.py API/app/workers/celery_app.py API/app/tests/test_sefaz_task.py
git commit -m "feat(sefaz): tasks Celery sefaz_sync_diario/sefaz_sync_empresa e fila sefaz"
```

---

### Task 10: `models/sefaz/schemas.py` + `api/sefaz/routes.py`

**Files:**
- Create: `API/app/models/sefaz/schemas.py`
- Create: `API/app/api/sefaz/routes.py`
- Modify: `API/app/api/routes.py`
- Test: `API/app/tests/test_sefaz_routes.py`

**Interfaces:**
- Consumes: `CertificadoService`/`CertificadoInvalidoError` (Task 5),
  `ManifestacaoDestinatarioService`/`ManifestacaoInvalidaError`/`DocumentoNaoPertenceEmpresaError`
  (Task 8), `sefaz_sync_empresa_task` (Task 9), `DocumentosRepository`/`SyncLogRepository`
  (Task 4), `require_company_scope`/`AuthenticatedUser` (`app.core.security`, já existente).
- Produces: `router` (FastAPI `APIRouter`) montado em `/api/sefaz/*` — consumido pelo Painel na
  Fase 3 (fora do escopo deste plano).

- [ ] **Step 1: Criar `models/sefaz/schemas.py`**

Criar `API/app/models/sefaz/schemas.py`:
```python
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class CertificadoStatusResponse(BaseModel):
    ativo: bool
    cnpj_titular: str | None = None
    data_validade: date | None = None
    dias_restantes: int | None = None


class SefazSyncResponse(BaseModel):
    status: str


class SefazDocumentoResponse(BaseModel):
    id: int
    chave_acesso: str
    tipo_documento: str
    direcao: str
    cnpj_emitente: str
    cnpj_destinatario: str | None = None
    nsu: str
    data_emissao: datetime | None = None
    valor_total: Decimal | None = None
    situacao: str | None = None
    manifestacao_status: str | None = None
    criado_em: datetime


class SefazDocumentoListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    resultados: list[SefazDocumentoResponse]


class SefazDocumentoDetalheResponse(SefazDocumentoResponse):
    xml_armazenado: str | None = None


class ManifestacaoRequest(BaseModel):
    tipo_manifestacao: str


class ManifestacaoResponse(BaseModel):
    documento_id: int
    manifestacao_status: str


class SefazSyncLogResponse(BaseModel):
    id: int
    iniciado_em: datetime
    finalizado_em: datetime | None = None
    documentos_novos: int
    nsu_inicial: str | None = None
    nsu_final: str | None = None
    status: str
    erro_detalhe: str | None = None


class SefazSyncLogListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    resultados: list[SefazSyncLogResponse]
```

- [ ] **Step 2: Escrever os testes de rota (falham — módulo não existe)**

Criar `API/app/tests/test_sefaz_routes.py`:
```python
import io

import pytest


def test_status_certificado_sem_certificado(client, monkeypatch):
    class FakeCertificadoService:
        def status(self, empresa_id):
            from app.services.sefaz.certificado_service import CertificadoStatus

            return CertificadoStatus(ativo=False, cnpj_titular=None, data_validade=None, dias_restantes=None)

    monkeypatch.setattr("app.api.sefaz.routes.CertificadoService", FakeCertificadoService)

    response = client.get("/api/sefaz/certificados/status")

    assert response.status_code == 200
    assert response.json() == {
        "ativo": False, "cnpj_titular": None, "data_validade": None, "dias_restantes": None,
    }


def test_cadastrar_certificado_invalido_retorna_400(client, monkeypatch):
    class FakeCertificadoService:
        def cadastrar(self, empresa_id, arquivo_pfx, senha, cnpj_esperado):
            from app.services.sefaz.certificado_service import CertificadoInvalidoError

            raise CertificadoInvalidoError("senha incorreta")

    monkeypatch.setattr("app.api.sefaz.routes.CertificadoService", FakeCertificadoService)

    response = client.post(
        "/api/sefaz/certificados",
        files={"arquivo": ("cert.pfx", io.BytesIO(b"conteudo"), "application/x-pkcs12")},
        data={"senha": "errada"},
    )

    assert response.status_code == 400


def test_cadastrar_certificado_extensao_invalida_retorna_400(client):
    response = client.post(
        "/api/sefaz/certificados",
        files={"arquivo": ("cert.txt", io.BytesIO(b"conteudo"), "text/plain")},
        data={"senha": "qualquer"},
    )

    assert response.status_code == 400


def test_disparar_sync_retorna_202(client, monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        "app.workers.sefaz_tasks.sefaz_sync_empresa_task.apply_async",
        lambda args, queue: chamadas.append((args, queue)),
    )

    response = client.post("/api/sefaz/sync")

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    assert chamadas == [([1, "12345678000190"], "sefaz")]


def test_listar_documentos(client, monkeypatch):
    from datetime import datetime, timezone

    class FakeDocumentosRepository:
        def listar(self, **kwargs):
            assert kwargs["empresa_id"] == 1
            return 1, [
                {
                    "id": 1, "chave_acesso": "3526" + "0" * 40, "tipo_documento": "resNFe",
                    "direcao": "recebida", "cnpj_emitente": "98765432000199", "cnpj_destinatario": None,
                    "nsu": "1", "data_emissao": datetime.now(timezone.utc), "valor_total": "10.00",
                    "situacao": "autorizada", "manifestacao_status": "pendente",
                    "criado_em": datetime.now(timezone.utc),
                }
            ]

    monkeypatch.setattr("app.api.sefaz.routes.DocumentosRepository", FakeDocumentosRepository)

    response = client.get("/api/sefaz/documentos")

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_obter_documento_inexistente_retorna_404(client, monkeypatch):
    class FakeDocumentosRepository:
        def obter_por_id(self, empresa_id, documento_id):
            return None

    monkeypatch.setattr("app.api.sefaz.routes.DocumentosRepository", FakeDocumentosRepository)

    response = client.get("/api/sefaz/documentos/999")

    assert response.status_code == 404


def test_manifestar_documento_sucesso(client, monkeypatch):
    class FakeManifestacaoService:
        def manifestar(self, empresa_id, documento_id, tipo_manifestacao):
            return {"documento_id": documento_id, "manifestacao_status": tipo_manifestacao}

    monkeypatch.setattr("app.api.sefaz.routes.ManifestacaoDestinatarioService", FakeManifestacaoService)

    response = client.post("/api/sefaz/documentos/1/manifestacao", json={"tipo_manifestacao": "ciencia"})

    assert response.status_code == 200
    assert response.json() == {"documento_id": 1, "manifestacao_status": "ciencia"}


def test_manifestar_documento_de_outra_empresa_retorna_404(client, monkeypatch):
    class FakeManifestacaoService:
        def manifestar(self, empresa_id, documento_id, tipo_manifestacao):
            from app.services.sefaz.manifestacao_destinatario_service import DocumentoNaoPertenceEmpresaError

            raise DocumentoNaoPertenceEmpresaError("nao encontrado")

    monkeypatch.setattr("app.api.sefaz.routes.ManifestacaoDestinatarioService", FakeManifestacaoService)

    response = client.post("/api/sefaz/documentos/1/manifestacao", json={"tipo_manifestacao": "ciencia"})

    assert response.status_code == 404


def test_manifestar_tipo_invalido_retorna_400(client, monkeypatch):
    class FakeManifestacaoService:
        def manifestar(self, empresa_id, documento_id, tipo_manifestacao):
            from app.services.sefaz.manifestacao_destinatario_service import ManifestacaoInvalidaError

            raise ManifestacaoInvalidaError("tipo invalido")

    monkeypatch.setattr("app.api.sefaz.routes.ManifestacaoDestinatarioService", FakeManifestacaoService)

    response = client.post("/api/sefaz/documentos/1/manifestacao", json={"tipo_manifestacao": "x"})

    assert response.status_code == 400


def test_listar_sync_log(client, monkeypatch):
    from datetime import datetime, timezone

    class FakeSyncLogRepository:
        def listar(self, empresa_id, *, limit, offset):
            return 1, [
                {
                    "id": 1, "iniciado_em": datetime.now(timezone.utc), "finalizado_em": None,
                    "documentos_novos": 0, "nsu_inicial": "0", "nsu_final": "0",
                    "status": "sucesso", "erro_detalhe": None,
                }
            ]

    monkeypatch.setattr("app.api.sefaz.routes.SyncLogRepository", FakeSyncLogRepository)

    response = client.get("/api/sefaz/sync-log")

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_rotas_exigem_login(unauthenticated_client):
    response = unauthenticated_client.get("/api/sefaz/certificados/status")
    assert response.status_code == 401
```

- [ ] **Step 3: Rodar e confirmar que falha**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_routes.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 4: Implementar `api/sefaz/routes.py`**

Criar `API/app/api/sefaz/routes.py`:
```python
from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.core.security import AuthenticatedUser, require_company_scope
from app.models.sefaz.schemas import (
    CertificadoStatusResponse,
    ManifestacaoRequest,
    ManifestacaoResponse,
    SefazDocumentoDetalheResponse,
    SefazDocumentoListResponse,
    SefazDocumentoResponse,
    SefazSyncLogListResponse,
    SefazSyncLogResponse,
    SefazSyncResponse,
)
from app.repositories.sefaz.documentos_repository import DocumentosRepository
from app.repositories.sefaz.sync_log_repository import SyncLogRepository
from app.services.sefaz.certificado_service import CertificadoInvalidoError, CertificadoService
from app.services.sefaz.manifestacao_destinatario_service import (
    DocumentoNaoPertenceEmpresaError,
    ManifestacaoDestinatarioService,
    ManifestacaoInvalidaError,
)

router = APIRouter()
sefaz_router = APIRouter(prefix="/sefaz", tags=["SEFAZ"], dependencies=[Depends(require_company_scope)])

TAMANHO_MAXIMO_CERTIFICADO_BYTES = 10_000


@sefaz_router.post("/certificados", response_model=CertificadoStatusResponse)
async def cadastrar_certificado(
    arquivo: UploadFile = File(...),
    senha: str = Form(...),
    current_user: AuthenticatedUser = Depends(require_company_scope),
):
    nome = (arquivo.filename or "").lower()
    if not (nome.endswith(".pfx") or nome.endswith(".p12")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O certificado deve ter extensao .pfx ou .p12.",
        )

    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo de certificado vazio.")
    if len(conteudo) > TAMANHO_MAXIMO_CERTIFICADO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificado excede o limite de {TAMANHO_MAXIMO_CERTIFICADO_BYTES} bytes.",
        )

    try:
        resultado = CertificadoService().cadastrar(current_user.empresa_id, conteudo, senha, current_user.cnpj)
    except CertificadoInvalidoError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return CertificadoStatusResponse(**resultado.__dict__)


@sefaz_router.get("/certificados/status", response_model=CertificadoStatusResponse)
def status_certificado(current_user: AuthenticatedUser = Depends(require_company_scope)):
    resultado = CertificadoService().status(current_user.empresa_id)
    return CertificadoStatusResponse(**resultado.__dict__)


@sefaz_router.post("/sync", response_model=SefazSyncResponse, status_code=status.HTTP_202_ACCEPTED)
def disparar_sync(current_user: AuthenticatedUser = Depends(require_company_scope)):
    from app.workers.sefaz_tasks import sefaz_sync_empresa_task

    sefaz_sync_empresa_task.apply_async(args=[current_user.empresa_id, current_user.cnpj], queue="sefaz")
    return SefazSyncResponse(status="accepted")


@sefaz_router.get("/documentos", response_model=SefazDocumentoListResponse)
def listar_documentos(
    direcao: str | None = Query(default=None),
    situacao: str | None = Query(default=None),
    manifestacao_pendente: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: AuthenticatedUser = Depends(require_company_scope),
):
    total, rows = DocumentosRepository().listar(
        empresa_id=current_user.empresa_id,
        direcao=direcao,
        situacao=situacao,
        manifestacao_pendente=manifestacao_pendente,
        limit=limit,
        offset=offset,
    )
    return SefazDocumentoListResponse(
        total=total,
        limit=limit,
        offset=offset,
        resultados=[SefazDocumentoResponse(**row) for row in rows],
    )


@sefaz_router.get("/documentos/{documento_id}", response_model=SefazDocumentoDetalheResponse)
def obter_documento(documento_id: int, current_user: AuthenticatedUser = Depends(require_company_scope)):
    documento = DocumentosRepository().obter_por_id(current_user.empresa_id, documento_id)
    if documento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento nao encontrado.")

    xml_armazenado = documento.get("xml_armazenado")
    if xml_armazenado is not None and hasattr(xml_armazenado, "tobytes"):
        xml_armazenado = xml_armazenado.tobytes()

    return SefazDocumentoDetalheResponse(
        **{
            **documento,
            "xml_armazenado": base64.b64encode(bytes(xml_armazenado)).decode("ascii") if xml_armazenado else None,
        }
    )


@sefaz_router.post("/documentos/{documento_id}/manifestacao", response_model=ManifestacaoResponse)
def manifestar_documento(
    documento_id: int,
    payload: ManifestacaoRequest,
    current_user: AuthenticatedUser = Depends(require_company_scope),
):
    try:
        resultado = ManifestacaoDestinatarioService().manifestar(
            current_user.empresa_id, documento_id, payload.tipo_manifestacao
        )
    except DocumentoNaoPertenceEmpresaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento nao encontrado.") from exc
    except ManifestacaoInvalidaError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ManifestacaoResponse(**resultado)


@sefaz_router.get("/sync-log", response_model=SefazSyncLogListResponse)
def listar_sync_log(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: AuthenticatedUser = Depends(require_company_scope),
):
    total, rows = SyncLogRepository().listar(current_user.empresa_id, limit=limit, offset=offset)
    return SefazSyncLogListResponse(
        total=total,
        limit=limit,
        offset=offset,
        resultados=[SefazSyncLogResponse(**row) for row in rows],
    )


router.include_router(sefaz_router)
```

- [ ] **Step 5: Registrar o router em `api/routes.py`**

Em `API/app/api/routes.py`, adicionar o import (junto dos outros, ordem alfabética por domínio):
```python
from app.api.sefaz.routes import router as sefaz_router
```
E adicionar `router.include_router(sefaz_router)` junto das outras chamadas (após
`router.include_router(reforma_tributaria_router)`).

- [ ] **Step 6: Rodar e confirmar que passa**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_sefaz_routes.py -v`
Expected: PASS (11 testes).

- [ ] **Step 7: Commit**

```bash
git add API/app/models/sefaz/schemas.py API/app/api/sefaz/routes.py API/app/api/routes.py \
  API/app/tests/test_sefaz_routes.py
git commit -m "feat(sefaz): rotas /api/sefaz/* (certificados, sync, documentos, manifestacao, sync-log)"
```

---

### Task 11: Suíte completa + revisão final da Fase 2

**Files:** nenhum arquivo novo — só execução e verificação (mesmo formato da Task 2 do plano da
Fase 1, `docs/superpowers/plans/2026-08-14-sefaz-fase1-migration.md`).

**Interfaces:** nenhuma — é o gate de saída da Fase 2.

- [ ] **Step 1: Rodar a suíte rápida inteira**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests -q`
Expected: todos os testes passam, incluindo os 12 arquivos novos desta Fase 2 (domínio, crypto,
repositories, services, task, rotas). Testes de repository ficam `SKIPPED` se
`PLATAFORMA_FISCAL_TEST_DATABASE_URL` não estiver definida — não é falha.

- [ ] **Step 2: Rodar a suíte de repositories contra Postgres real, se disponível**

Run:
```powershell
$env:PLATAFORMA_FISCAL_TEST_DATABASE_URL = "postgresql://<usuario>:<senha>@localhost:<porta>/plataforma_fiscal_test"
cd API
.\.venv-local\Scripts\python.exe -m pytest app/tests -k sefaz -v
```
Expected: todos os testes `test_sefaz_*` passam contra o schema `sefaz` real (migration da Fase 1
já aplicada via `migrated_db`).

- [ ] **Step 3: Checklist de segurança final (releitura manual, sem código novo)**

Confirmar manualmente, lendo os arquivos criados nesta fase:
- Nenhuma rota em `api/sefaz/routes.py` aceita `empresa_id` vindo do cliente (só
  `current_user.empresa_id`).
- `CertificadoStatusResponse`/`SefazDocumentoResponse`/`SefazSyncLogResponse` nunca expõem
  `senha_criptografada` nem `arquivo_certificado`.
- Nenhum `logger.info`/`logger.warning`/`logger.exception` em `services/sefaz/*` ou
  `workers/sefaz_tasks.py` inclui `certificado_pfx`, `senha` ou `arquivo_certificado` no `extra`.

- [ ] **Step 4: Commit final (se o Step 3 encontrar algo pra ajustar)**

Se o Step 3 não encontrar nada, não há commit nesta task (nenhum arquivo mudou). Se encontrar
algo, corrigir e commitar com `git commit -m "fix(sefaz): remove dado sensivel de log em <arquivo>"`.

Fase 2 está completa quando as Tasks 1-10 estiverem commitadas e a Task 11 passar sem
ajustes. Fase 3 (frontend, `Painel/src/features/integracoes-sefaz/`) fica pra depois da
validação do usuário sobre este backend.
