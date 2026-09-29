# Conta Azul — Fase 1 (produtos, vendedores, itens de venda) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar suporte a produtos (`/v1/produto/busca`), vendedores (`/v1/venda/vendedores`) e itens de venda (`/v1/venda/{id_venda}/itens`) na integração `API/contaazul-integracao`, seguindo os padrões já existentes no client/models/CLI.

**Architecture:** Extensão aditiva do client HTTP existente (`ContaAzulClient`) e dos schemas Pydantic (`ContaAzulBaseModel`). Sem mudança nos mecanismos de retry/backoff/paginação já implementados — só reuso.

**Tech Stack:** Python, httpx, tenacity, pydantic, typer, respx (testes), pytest.

## Global Constraints

- Todo modelo Pydantic novo herda `ContaAzulBaseModel` (`extra="allow"` + campo `raw: dict` com o payload original) — nenhum dado pode ser perdido mesmo que um campo não esteja mapeado.
- Nenhuma chamada real à API nos testes — sempre `respx.mock`.
- `/v1/produto/busca` **não tem** campo fiscal (NCM/CEST/origem) nem `GET /v1/produto/{id}` — não inventar esses campos nos modelos nem no client.
- `python main.py sync` continua funcionando como hoje (backward-compatible); os comandos novos são aditivos.
- Base URL: `https://api-v2.contaazul.com`. Autenticação: `Authorization: Bearer <access_token>` (já implementado em `ContaAzulClient._do_request`, não mexer.

---

### Task 1: Modelo e client method para produtos

**Files:**
- Modify: `API/contaazul-integracao/contaazul/models.py` (adicionar classe `Produto` no final do arquivo, após `ContaPagar` — linha 104)
- Modify: `API/contaazul-integracao/contaazul/client.py:39-46` (`ENDPOINTS`), e final da classe `ContaAzulClient` (após `listar_contas_a_pagar`, linha 217)
- Test: `API/contaazul-integracao/tests/test_client.py`

**Interfaces:**
- Consumes: `ContaAzulBaseModel` (`contaazul/models.py:17-20`), `ContaAzulClient._get(resource_key, params)` (`contaazul/client.py:155-156`), `ENDPOINTS` dict, `PAGE_PARAM`/`PAGE_SIZE_PARAM`/`DEFAULT_PAGE_SIZE` (`contaazul/client.py:48-50`).
- Produces: `Produto` (pydantic model, campos `id: str`, `id_legado: Optional[int]`, `nome: str`, `codigo_sku: Optional[str]`, `codigo_ean: Optional[str]`, `tipo: Optional[str]`, `status: Optional[str]`, `estoque: Optional[float]`, `valor_venda: Optional[float]`, `custo_medio: Optional[float]`, `filhos: Optional[list[dict]]`). `ContaAzulClient.listar_produtos(pagina: int = 1, tamanho_pagina: int = DEFAULT_PAGE_SIZE, busca: Optional[str] = None, status: Optional[str] = None, campo_ordenacao: Optional[str] = None, direcao_ordenacao: Optional[str] = None, inicio: Optional[float] = None, fim: Optional[float] = None) -> list[Produto]`.

- [ ] **Step 1: Escrever o teste que falha**

Adicionar em `API/contaazul-integracao/tests/test_client.py`, na seção `# ---------- ContaAzulClient ----------`:

```python
@respx.mock
def test_listar_produtos_normaliza_campos():
    payload = {
        "itens": [
            {
                "id": "p1",
                "id_legado": 12345,
                "nome": "Produto Exemplo",
                "codigo_sku": "SKU123",
                "codigo_ean": "1234567890123",
                "tipo": "PRODUTO",
                "status": "ATIVO",
                "estoque": 50,
                "valor_venda": 99.99,
                "custo_medio": 50,
            }
        ],
        "itens_totais": 1,
    }
    respx.get(f"{BASE_URL}{ENDPOINTS['produtos']}").mock(return_value=httpx.Response(200, json=payload))
    client = ContaAzulClient(auth=StubAuth())

    produtos = client.listar_produtos(pagina=1, busca="Exemplo", status="ATIVO")

    assert len(produtos) == 1
    assert produtos[0].id == "p1"
    assert produtos[0].nome == "Produto Exemplo"
    assert produtos[0].valor_venda == 99.99
    assert produtos[0].raw["codigo_ean"] == "1234567890123"


@respx.mock
def test_listar_produtos_so_envia_filtros_informados():
    route = respx.get(f"{BASE_URL}{ENDPOINTS['produtos']}").mock(
        return_value=httpx.Response(200, json={"itens": []})
    )
    client = ContaAzulClient(auth=StubAuth())

    client.listar_produtos(pagina=2)

    sent_params = dict(route.calls[0].request.url.params)
    assert sent_params["pagina"] == "2"
    assert "busca" not in sent_params
    assert "status" not in sent_params
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd API/contaazul-integracao && python -m pytest tests/test_client.py -k test_listar_produtos -v`
Expected: FAIL — `KeyError: 'produtos'` (ENDPOINTS não tem a chave) e/ou `AttributeError: 'ContaAzulClient' object has no attribute 'listar_produtos'`.

- [ ] **Step 3: Adicionar o modelo `Produto`**

No final de `API/contaazul-integracao/contaazul/models.py` (depois da classe `ContaPagar`):

```python
class Produto(ContaAzulBaseModel):
    """GET /v1/produto/busca. Sem campo fiscal (NCM/CEST/origem) — a API real
    nao expoe isso. Sem GET /v1/produto/{id} tambem — so ha listagem por filtro."""

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
    filhos: Optional[list[dict]] = None
```

- [ ] **Step 4: Adicionar endpoint e método no client**

Em `API/contaazul-integracao/contaazul/client.py`, no dict `ENDPOINTS` (linha 39-46), adicionar:

```python
    "produtos": "/v1/produto/busca",
```

No import de `contaazul.models` (linha 25-33), adicionar `Produto` à lista.

No final da classe `ContaAzulClient` (depois de `listar_contas_a_pagar`, linha 217), adicionar:

```python
    def listar_produtos(
        self,
        pagina: int = 1,
        tamanho_pagina: int = DEFAULT_PAGE_SIZE,
        busca: Optional[str] = None,
        status: Optional[str] = None,
        campo_ordenacao: Optional[str] = None,
        direcao_ordenacao: Optional[str] = None,
        inicio: Optional[float] = None,
        fim: Optional[float] = None,
    ) -> list[Produto]:
        params = {PAGE_PARAM: pagina, PAGE_SIZE_PARAM: tamanho_pagina}
        opcionais = {
            "busca": busca,
            "status": status,
            "campo_ordenacao": campo_ordenacao,
            "direcao_ordenacao": direcao_ordenacao,
            "inicio": inicio,
            "fim": fim,
        }
        params.update({k: v for k, v in opcionais.items() if v is not None})
        items = self._get("produtos", params)
        return [Produto(**item, raw=item) for item in items]
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

Run: `cd API/contaazul-integracao && python -m pytest tests/test_client.py -k test_listar_produtos -v`
Expected: PASS (2 testes).

- [ ] **Step 6: Commit**

```bash
git add API/contaazul-integracao/contaazul/models.py API/contaazul-integracao/contaazul/client.py API/contaazul-integracao/tests/test_client.py
git commit -m "Adiciona listar_produtos (GET /v1/produto/busca)"
```

---

### Task 2: Modelo e client method para vendedores

**Files:**
- Modify: `API/contaazul-integracao/contaazul/models.py` (adicionar classe `Vendedor` após `Produto`)
- Modify: `API/contaazul-integracao/contaazul/client.py:39-46` (`ENDPOINTS`), final da classe (após `listar_produtos`, adicionado na Task 1)
- Test: `API/contaazul-integracao/tests/test_client.py`

**Interfaces:**
- Consumes: `ContaAzulClient._request_json(path, params)` (`contaazul/client.py:124-153` — retorna o JSON bruto decodificado, sem passar por `_extract_items`).
- Produces: `Vendedor` (`id: str`, `nome: str`, `id_legado: Optional[int]`). `ContaAzulClient.listar_vendedores() -> list[Vendedor]`.

**Nota:** a resposta de `GET /v1/venda/vendedores` é um **array JSON bruto** (`[{...}, {...}]`), não um envelope `{"itens": [...]}`. Não usar `_get`/`_extract_items` — eles esperam um dict. Chamar `_request_json` direto e iterar a lista retornada.

- [ ] **Step 1: Escrever o teste que falha**

```python
@respx.mock
def test_listar_vendedores_aceita_array_bruto():
    payload = [
        {"id": "vend1", "nome": "João da Silva", "id_legado": 123456},
        {"id": "vend2", "nome": "Maria Souza"},
    ]
    respx.get(f"{BASE_URL}{ENDPOINTS['vendedores']}").mock(return_value=httpx.Response(200, json=payload))
    client = ContaAzulClient(auth=StubAuth())

    vendedores = client.listar_vendedores()

    assert len(vendedores) == 2
    assert vendedores[0].nome == "João da Silva"
    assert vendedores[0].id_legado == 123456
    assert vendedores[1].id_legado is None
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd API/contaazul-integracao && python -m pytest tests/test_client.py -k test_listar_vendedores -v`
Expected: FAIL — `KeyError: 'vendedores'` e/ou `AttributeError`.

- [ ] **Step 3: Adicionar o modelo `Vendedor`**

Em `API/contaazul-integracao/contaazul/models.py`, após `Produto`:

```python
class Vendedor(ContaAzulBaseModel):
    """GET /v1/venda/vendedores. Resposta e array bruto, sem paginacao."""

    id: str
    nome: str
    id_legado: Optional[int] = None
```

- [ ] **Step 4: Adicionar endpoint e método no client**

Em `ENDPOINTS` (`contaazul/client.py`), adicionar:

```python
    "vendedores": "/v1/venda/vendedores",
```

Importar `Vendedor` junto de `Produto` no bloco de import de `contaazul.models`.

Depois de `listar_produtos` (Task 1):

```python
    def listar_vendedores(self) -> list[Vendedor]:
        payload = self._request_json(ENDPOINTS["vendedores"], {})
        return [Vendedor(**item, raw=item) for item in payload]
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `cd API/contaazul-integracao && python -m pytest tests/test_client.py -k test_listar_vendedores -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add API/contaazul-integracao/contaazul/models.py API/contaazul-integracao/contaazul/client.py API/contaazul-integracao/tests/test_client.py
git commit -m "Adiciona listar_vendedores (GET /v1/venda/vendedores)"
```

---

### Task 3: Modelos e client method para itens de venda

**Files:**
- Modify: `API/contaazul-integracao/contaazul/models.py` (adicionar `ItemVenda` e `TotaisItensVenda` após `Vendedor`)
- Modify: `API/contaazul-integracao/contaazul/client.py` (final da classe, após `listar_vendedores`)
- Test: `API/contaazul-integracao/tests/test_client.py`

**Interfaces:**
- Consumes: `ContaAzulClient._request_json(path, params)`.
- Produces: `ItemVenda` (`id: Optional[str]`, `id_item: Optional[str]`, `nome: Optional[str]`, `descricao: Optional[str]`, `tipo: Optional[str]`, `quantidade: Optional[float]`, `valor: Optional[float]`, `custo: Optional[float]`). `TotaisItensVenda` (`quantidade_produtos: Optional[int]`, `quantidade_servicos: Optional[int]`, `quantidade_nao_conciliados: Optional[int]`). `ContaAzulClient.obter_itens_venda(id_venda: str, pagina: int = 1, tamanho_pagina: int = DEFAULT_PAGE_SIZE) -> tuple[list[ItemVenda], TotaisItensVenda]`.

**Nota:** o envelope de resposta é `{"itens": [...], "itens_totais": N, "totais": {...}}`. `_get`/`_extract_items` descartariam `totais` — por isso este método chama `_request_json` direto, igual `listar_vendedores`.

- [ ] **Step 1: Escrever o teste que falha**

```python
@respx.mock
def test_obter_itens_venda_retorna_itens_e_totais():
    payload = {
        "itens": [
            {"id": "i1", "id_item": "prod1", "nome": "Produto 1", "tipo": "PRODUTO", "quantidade": 2, "valor": 100.0, "custo": 60.0},
        ],
        "itens_totais": 1,
        "totais": {"quantidade_produtos": 1, "quantidade_servicos": 0, "quantidade_nao_conciliados": 0},
    }
    respx.get(f"{BASE_URL}/v1/venda/venda-123/itens").mock(return_value=httpx.Response(200, json=payload))
    client = ContaAzulClient(auth=StubAuth())

    itens, totais = client.obter_itens_venda("venda-123")

    assert len(itens) == 1
    assert itens[0].nome == "Produto 1"
    assert itens[0].quantidade == 2
    assert totais.quantidade_produtos == 1
    assert totais.quantidade_nao_conciliados == 0
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `cd API/contaazul-integracao && python -m pytest tests/test_client.py -k test_obter_itens_venda -v`
Expected: FAIL — `AttributeError: 'ContaAzulClient' object has no attribute 'obter_itens_venda'`.

- [ ] **Step 3: Adicionar os modelos**

Em `API/contaazul-integracao/contaazul/models.py`, após `Vendedor`:

```python
class ItemVenda(ContaAzulBaseModel):
    """Item de GET /v1/venda/{id_venda}/itens."""

    id: Optional[str] = None
    id_item: Optional[str] = None
    nome: Optional[str] = None
    descricao: Optional[str] = None
    tipo: Optional[str] = None
    quantidade: Optional[float] = None
    valor: Optional[float] = None
    custo: Optional[float] = None


class TotaisItensVenda(ContaAzulBaseModel):
    """Campo `totais` de GET /v1/venda/{id_venda}/itens."""

    quantidade_produtos: Optional[int] = None
    quantidade_servicos: Optional[int] = None
    quantidade_nao_conciliados: Optional[int] = None
```

- [ ] **Step 4: Adicionar o método no client**

Importar `ItemVenda` e `TotaisItensVenda` no bloco de import de `contaazul.models` em `client.py`.

Depois de `listar_vendedores` (Task 2):

```python
    def obter_itens_venda(
        self, id_venda: str, pagina: int = 1, tamanho_pagina: int = DEFAULT_PAGE_SIZE
    ) -> tuple[list[ItemVenda], TotaisItensVenda]:
        payload = self._request_json(
            f"/v1/venda/{id_venda}/itens",
            {PAGE_PARAM: pagina, PAGE_SIZE_PARAM: tamanho_pagina},
        )
        itens = [ItemVenda(**item, raw=item) for item in payload.get("itens", [])]
        totais_raw = payload.get("totais") or {}
        totais = TotaisItensVenda(**totais_raw, raw=totais_raw)
        return itens, totais
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `cd API/contaazul-integracao && python -m pytest tests/test_client.py -k test_obter_itens_venda -v`
Expected: PASS.

- [ ] **Step 6: Rodar a suíte inteira**

Run: `cd API/contaazul-integracao && python -m pytest tests/ -v`
Expected: todos os testes (existentes + novos das Tasks 1-3) passam.

- [ ] **Step 7: Commit**

```bash
git add API/contaazul-integracao/contaazul/models.py API/contaazul-integracao/contaazul/client.py API/contaazul-integracao/tests/test_client.py
git commit -m "Adiciona obter_itens_venda (GET /v1/venda/{id_venda}/itens)"
```

---

### Task 4: CLI — comandos `produtos`, `itens-venda`, e vendedores no `sync`

**Files:**
- Modify: `API/contaazul-integracao/main.py`

**Interfaces:**
- Consumes: `ContaAzulClient.listar_produtos` (Task 1), `ContaAzulClient.listar_vendedores` (Task 2), `ContaAzulClient.obter_itens_venda` (Task 3), `_coletar_todas_paginas` (`main.py:45-55`), `_load_auth` (`main.py:31-42`), `JsonExporter` (`exporters/json_exporter.py`).
- Produces: comandos typer `produtos` e `itens-venda` (visíveis em `python main.py --help`); `sync` passa a incluir `vendedores` no dict `dados` e no JSON exportado.

Este task não usa TDD com pytest (é CLI/integração manual) — a verificação é rodar os comandos e inspecionar a saída, igual ao padrão já usado pelos comandos `auth`/`sync` existentes neste arquivo (não há testes de CLI no repo hoje).

- [ ] **Step 1: Adicionar `vendedores` ao comando `sync`**

Em `API/contaazul-integracao/main.py`, dentro do dict `dados` da função `sync` (`main.py:114-121`), adicionar a linha:

```python
            "vendedores": client.listar_vendedores(),
```

(fica junto de `"pessoas"`, `"categorias"`, `"centros_custo"` — sem paginação, chamada única).

- [ ] **Step 2: Adicionar comando `produtos`**

Depois da função `sync` (`main.py`, após linha 134), adicionar:

```python
@app.command()
def produtos(
    busca: str = typer.Option(None, "--busca", help="Filtra por nome ou código do produto."),
    status: str = typer.Option(None, "--status", help="ATIVO, INATIVO ou TODOS."),
    saida: Path = typer.Option(Path("output"), "--saida", help="Diretorio de saida"),
):
    """Lista produtos (GET /v1/produto/busca). Sem dado fiscal (NCM/CEST) -- a API nao expoe."""
    auth_client = _load_auth()
    client = ContaAzulClient(auth_client)

    try:
        items = _coletar_todas_paginas(lambda p: client.listar_produtos(pagina=p, busca=busca, status=status))
    except AuthError as exc:
        typer.secho(f"Erro de autenticacao: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except ApiError as exc:
        typer.secho(f"Erro da API Conta Azul (status {exc.status_code}): {exc.payload}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    finally:
        client.close()

    JsonExporter().export({"produtos": items}, saida)
    typer.secho(f"Exportado {len(items)} produtos para {saida}/produtos.json", fg=typer.colors.GREEN)
```

- [ ] **Step 3: Adicionar comando `itens-venda`**

Depois do comando `produtos`, adicionar:

```python
@app.command(name="itens-venda")
def itens_venda(
    id_venda: str = typer.Option(..., "--id-venda", help="UUID ou id legado da venda."),
    saida: Path = typer.Option(Path("output"), "--saida", help="Diretorio de saida"),
):
    """Lista itens de uma venda + totais agregados (GET /v1/venda/{id_venda}/itens)."""
    auth_client = _load_auth()
    client = ContaAzulClient(auth_client)

    try:
        pagina = 1
        todos_itens = []
        totais = None
        while True:
            itens, totais = client.obter_itens_venda(id_venda, pagina=pagina)
            todos_itens.extend(itens)
            if len(itens) < DEFAULT_PAGE_SIZE:
                break
            pagina += 1
    except AuthError as exc:
        typer.secho(f"Erro de autenticacao: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except ApiError as exc:
        typer.secho(f"Erro da API Conta Azul (status {exc.status_code}): {exc.payload}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    finally:
        client.close()

    saida.mkdir(parents=True, exist_ok=True)
    payload = {
        "itens": [item.model_dump(mode="json") for item in todos_itens],
        "totais": totais.model_dump(mode="json") if totais else None,
    }
    caminho = saida / f"itens_venda_{id_venda}.json"
    caminho.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    typer.secho(f"Exportado {len(todos_itens)} itens para {caminho}", fg=typer.colors.GREEN)
```

Adicionar `import json` no topo de `main.py` junto dos outros imports (`main.py:8-21`).

- [ ] **Step 4: Rodar `--help` pra confirmar que os comandos aparecem**

Run: `cd API/contaazul-integracao && python main.py --help`
Expected: lista mostra `auth`, `sync`, `produtos`, `itens-venda`.

- [ ] **Step 5: Rodar a suíte de testes inteira de novo (garante que nada quebrou)**

Run: `cd API/contaazul-integracao && python -m pytest tests/ -v`
Expected: todos passam (CLI não tem teste automatizado, mas o client/models usados por ela sim).

- [ ] **Step 6: Commit**

```bash
git add API/contaazul-integracao/main.py
git commit -m "Adiciona comandos CLI produtos e itens-venda; inclui vendedores no sync"
```

---

### Task 5: Atualizar README

**Files:**
- Modify: `API/contaazul-integracao/README.md`

- [ ] **Step 1: Atualizar a tabela de endpoints (`README.md:14-21`)**

Adicionar 3 linhas na tabela:

```markdown
| Produtos | `GET /v1/produto/busca` | — (sem `data_alteracao`; sem GET por ID; **sem NCM/CEST/fiscal**) |
| Vendedores | `GET /v1/venda/vendedores` | — (resposta é array bruto, não paginada) |
| Itens de venda | `GET /v1/venda/{id_venda}/itens` | `id_venda` no path |
```

- [ ] **Step 2: Adicionar nota explícita sobre a ausência de dado fiscal**

Logo após a tabela, adicionar parágrafo:

```markdown
**Atenção:** `/v1/produto/busca` (confirmado contra o OpenAPI real, `inventory-apis-openapi`)
não tem `GET /v1/produto/{id}` nem qualquer campo fiscal (NCM, CEST, origem) — só
nome/SKU/EAN/estoque/valor/status. Não serve para o fluxo de correção fiscal de produtos;
precisa de outra fonte de dado pra isso.
```

- [ ] **Step 3: Atualizar seção "Comandos" / exemplos de uso**

Adicionar após o exemplo de `sync` (`README.md:79-84`):

```markdown
Comandos adicionais:

```bash
python main.py produtos --status ATIVO
python main.py itens-venda --id-venda <uuid-ou-id-legado>
```

`produtos` gera `output/produtos.json`. `itens-venda` gera `output/itens_venda_<id_venda>.json`
com `{"itens": [...], "totais": {...}}`.
```

- [ ] **Step 4: Commit**

```bash
git add API/contaazul-integracao/README.md
git commit -m "Documenta endpoints de produtos, vendedores e itens de venda no README"
```

---

## Verificação final

- [ ] Rodar `cd API/contaazul-integracao && python -m pytest tests/ -v` — todos os testes passam (existentes + novos).
- [ ] Rodar `python main.py --help` e confirmar os 4 comandos (`auth`, `sync`, `produtos`, `itens-venda`).
- [ ] Conferir que nenhum modelo novo referencia campo fiscal (`grep -i "ncm\|cest\|fiscal" contaazul/models.py` deve retornar só o comentário de aviso da classe `Produto`, não um campo real).
