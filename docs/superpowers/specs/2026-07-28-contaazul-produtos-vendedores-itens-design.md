# Conta Azul — Fase 1: produtos, vendedores, itens de venda

## Contexto

`API/contaazul-integracao` já tem OAuth2 funcionando e sync de vendas/pessoas/categorias/
centros de custo/contas a receber/contas a pagar. Este documento cobre a fase 1 do pedido de
expansão: produtos, vendedores e itens de venda.

## Achado que muda o escopo original

O pedido original assumia `GET /v1/produtos` com filtro `data_alteracao_de/ate` e campos
`fiscal.ncm`, `fiscal.cest`, `fiscal.origem`. Conferido contra o OpenAPI real
(`https://developers.contaazul.com/_bundle/docs/inventory-apis-openapi.json?download`):

- Path real é `GET /v1/produto/busca` (singular), não `/v1/produtos`.
- **Não existe** `GET /v1/produto/{id}` — só `POST /v1/produto` (criar), `DELETE /v1/produto/{id}`,
  `POST /v1/produto/desativar`. Sem endpoint de detalhe por ID.
- **Não existe** `data_alteracao_de`/`data_alteracao_ate` — sem sync incremental por data.
  Params reais: `pagina`, `tamanho_pagina`, `campo_ordenacao` (NOME/CODIGO/VALOR_VENDA/ESTOQUE),
  `direcao_ordenacao`, `busca`, `status` (ATIVO/INATIVO/TODOS), `inicio`/`fim` (numérico —
  faixa de `valor_venda`, não data).
- **Zero campo fiscal** no schema de produto (`ProductListResponse`/`ProdutoResponse`) — sem
  NCM, CEST, origem. Confirmado por busca case-insensitive de `ncm|cest|fiscal` no spec inteiro:
  nenhuma ocorrência.
- Testados ~35 slugs de bundle OpenAPI atrás de endpoints de serviços/notas fiscais/CEST/NCM
  isolados — todos 404. As únicas 4 áreas públicas encontradas: `inventory` (produto), `sales`
  (venda), `financial`, `protocol`.

Decisão do usuário: implementar `produto/busca` como ele realmente é (sem dado fiscal). Essa
API não serve para o fluxo de correção de NCM/CEST — precisa de outra fonte.

Endpoints de vendedores e itens de venda batem exatamente com o que o usuário já tinha
confirmado no prompt original (validado contra `sales-apis-openapi.json`).

## Escopo desta fase

1. `GET /v1/produto/busca` — listagem de produtos (sem detalhe por ID, sem dado fiscal).
2. `GET /v1/venda/vendedores` — lista de vendedores.
3. `GET /v1/venda/{id_venda}/itens` — itens de uma venda + totais agregados.

Fora de escopo (fase 2, se necessário): serviços, notas fiscais, categorias-dre, conta-financeira,
transferências contábeis, alterações de eventos financeiros — endpoints existem no
`financial-apis-openapi` mas não foram pedidos nesta fase.

## Modelos (`contaazul/models.py`)

```python
class Produto(ContaAzulBaseModel):
    id: str
    id_legado: Optional[int] = None
    nome: str
    codigo_sku: Optional[str] = None
    codigo_ean: Optional[str] = None
    tipo: Optional[str] = None          # PRODUTO | VARIACAO | KIT_PRODUTOS
    status: Optional[str] = None        # ATIVO | INATIVO | TODOS
    estoque: Optional[float] = None
    valor_venda: Optional[float] = None
    custo_medio: Optional[float] = None
    filhos: Optional[list[dict]] = None

class Vendedor(ContaAzulBaseModel):
    id: str
    nome: str
    id_legado: Optional[int] = None

class ItemVenda(ContaAzulBaseModel):
    id: Optional[str] = None
    id_item: Optional[str] = None
    nome: Optional[str] = None
    descricao: Optional[str] = None
    tipo: Optional[str] = None          # PRODUTO | SERVICO | ATIVOS_IMOBILIZADOS | FINANCEIRO | KIT_PRODUTOS
    quantidade: Optional[float] = None
    valor: Optional[float] = None
    custo: Optional[float] = None

class TotaisItensVenda(ContaAzulBaseModel):
    quantidade_produtos: Optional[int] = None
    quantidade_servicos: Optional[int] = None
    quantidade_nao_conciliados: Optional[int] = None
```

Todos herdam `ContaAzulBaseModel` (`extra="allow"` + `raw`), igual aos modelos existentes.

## Client (`contaazul/client.py`)

- `ENDPOINTS["produtos"] = "/v1/produto/busca"`.
- `listar_produtos(pagina=1, tamanho_pagina=DEFAULT_PAGE_SIZE, busca=None, status=None, campo_ordenacao=None, direcao_ordenacao=None, inicio=None, fim=None) -> list[Produto]`
  — usa `_get("produtos", params)`, monta `params` só com os campos não-`None` (todos opcionais
  na API real).
- `listar_vendedores() -> list[Vendedor]` — chama `_request_json("/v1/venda/vendedores", {})`
  diretamente (não passa por `_get`/`_extract_items`: resposta é array bruto `[...]`, não
  envelope `{"itens": [...]}`). Sem paginação (API não pagina esse endpoint).
- `obter_itens_venda(id_venda, pagina=1, tamanho_pagina=DEFAULT_PAGE_SIZE) -> tuple[list[ItemVenda], TotaisItensVenda]`
  — chama `_request_json(f"/v1/venda/{id_venda}/itens", params)` diretamente (não usa `_get`,
  que descartaria a chave `totais`). Retorna `(itens, totais)`.

Nenhuma mudança em `_do_request`/retry/backoff — reaproveita o que já existe.

## CLI (`main.py`)

- `python main.py produtos [--busca TEXTO] [--status ATIVO|INATIVO|TODOS] [--saida output]`
  — comando novo. Pagina até página incompleta (reusa `_coletar_todas_paginas`). Exporta
  `produtos.json`. Sem `--desde` (API não suporta).
- `python main.py itens-venda --id-venda <uuid> [--saida output]` — comando novo. Exporta
  `itens_venda_<id_venda>.json` com `{"itens": [...], "totais": {...}}`.
- `vendedores` entra no comando `sync` existente (junto de pessoas/categorias/centros_custo),
  por ser lista de referência simples sem parâmetros — roda em toda sincronização por período.

## Testes

`tests/test_client.py` (respx, sem chamada real):
1. `listar_produtos` — paginação normal, envelope `{"itens": [...], "itens_totais": N}`.
2. `listar_vendedores` — resposta é array bruto (não dict), garante que o client não tenta
   `_extract_items` nele.
3. `obter_itens_venda` — envelope com `totais` presente, garante que `totais` não é descartado.

## Documentação

`README.md`: tabela de endpoints ganha as 3 linhas novas + nota explícita que `produto/busca`
não tem campo fiscal (NCM/CEST) — evita retrabalho futuro tentando usar essa API pra correção
fiscal de produtos.
