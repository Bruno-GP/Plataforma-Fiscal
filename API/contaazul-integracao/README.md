# Integração Conta Azul API v2 → Plataforma Fiscal

Extrai dados financeiros/fiscais da API oficial da Conta Azul (OAuth2) e exporta em JSON,
prontos para consumo pela plataforma fiscal.

> **Ambiente**: pensado para conta de desenvolvedor de teste (sandbox 30 dias), não produção.

## Endpoints usados

Confirmados contra o OpenAPI oficial de cada área (baixado direto do portal,
`https://developers.contaazul.com/_bundle/docs/<pagina>.json?download` — o link
`/openapi` genérico dá 403/404, mas cada página de área tem seu próprio spec):

| Recurso | Método/Path | Params obrigatórios além de paginação |
|---|---|---|
| Vendas | `GET /v1/venda/busca` | — |
| Pessoas | `GET /v1/pessoas` | — |
| Categorias | `GET /v1/categorias` | `permite_apenas_filhos` (bool) |
| Centro de custo | `GET /v1/centro-de-custo` | `pagina`/`tamanho_pagina` obrigatórios |
| Contas a receber | `GET /v1/financeiro/eventos-financeiros/contas-a-receber/buscar` | `data_vencimento_de`/`data_vencimento_ate` |
| Contas a pagar | `GET /v1/financeiro/eventos-financeiros/contas-a-pagar/buscar` | `data_vencimento_de`/`data_vencimento_ate` |
| Produtos | `GET /v1/produto/busca` | — (sem `data_alteracao`; sem GET por ID; **sem NCM/CEST/fiscal**) |
| Vendedores | `GET /v1/venda/vendedores` | — (resposta é array bruto, não paginada) |
| Itens de venda | `GET /v1/venda/{id_venda}/itens` | `id_venda` no path |

**Atenção:** `/v1/produto/busca` (confirmado contra o OpenAPI real, `inventory-apis-openapi`)
não tem `GET /v1/produto/{id}` nem qualquer campo fiscal (NCM, CEST, origem) — só
nome/SKU/EAN/estoque/valor/status. Não serve para o fluxo de correção fiscal de produtos;
precisa de outra fonte de dado pra isso.

Envelope de paginação: a maioria usa `{"itens": [...]}`, mas `/v1/pessoas` e
`/v1/centro-de-custo` usam `{"items": [...]}` (inglês). `contaazul/client.py:_extract_items`
já trata os dois.

Itens de linha de uma venda (produto/quantidade/valor) **não vêm** no resultado de busca —
é um endpoint separado (`GET /v1/venda/{id_venda}/itens`), ainda não implementado aqui.

Todos os modelos em `contaazul/models.py` guardam o payload original em `raw`, então nenhum
campo é perdido mesmo que um nome específico não esteja mapeado no schema Pydantic.

## Setup

### 1. Criar app no portal de desenvolvedores

1. Acesse https://portaldevs.contaazul.com/ e crie uma aplicação.
2. Defina a **Redirect URI** (ex: `http://localhost:8765/callback`) — precisa bater
   exatamente com `CONTAAZUL_REDIRECT_URI` no `.env`.
3. Anote `client_id` e `client_secret`.

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar `.env`

```bash
cp .env.example .env
```

Preencha:

```
CONTAAZUL_CLIENT_ID=seu_client_id
CONTAAZUL_CLIENT_SECRET=seu_client_secret
CONTAAZUL_REDIRECT_URI=http://localhost:8765/callback
```

`.env` e `.tokens.json` já estão no `.gitignore` — nunca commitar.

### 4. Autenticar (primeira vez)

```bash
python main.py auth
```

Abre a URL de autorização (cole no navegador se não abrir sozinho), você loga na Conta Azul
e autoriza o app. Um servidor local sobe temporariamente em `CONTAAZUL_REDIRECT_URI` para
capturar o `code` do callback. Tokens ficam salvos em `.tokens.json`.

Renovação de `access_token` (expira em 1h) é automática via `refresh_token` a cada chamada.
Se o `refresh_token` também expirar/for revogado, rode `python main.py auth` de novo.

### 5. Sincronizar dados

```bash
python main.py sync --inicio 2026-01-01 --fim 2026-01-31
```

Gera em `output/`: `vendas.json`, `pessoas.json`, `categorias.json`, `centros_custo.json`,
`contas_receber.json`, `contas_pagar.json`.

Comandos adicionais:

```bash
python main.py produtos --status ATIVO
python main.py itens-venda --id-venda <uuid-ou-id-legado>
```

`produtos` gera `output/produtos.json`. `itens-venda` gera `output/itens_venda_<id_venda>.json`
com `{"itens": [...], "totais": {...}}`.

## Estrutura

```
contaazul-integracao/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── main.py                  # CLI (auth / sync)
├── contaazul/
│   ├── auth.py               # OAuth2 + refresh + servidor local de callback
│   ├── client.py             # ContaAzulClient (paginação, retry/backoff, logging)
│   └── models.py             # Schemas Pydantic normalizados
├── exporters/
│   └── json_exporter.py      # Exportador JSON (ponto de extensão para outros formatos)
└── tests/
    └── test_client.py        # Testes com mocks (respx) — nunca chama a API real
```

## Rodar os testes

```bash
python -m pytest tests/ -v
```

## Próximos passos (não implementados ainda)

- Exportador CSV (`exporters/csv_exporter.py`) — por ora só JSON.
- Exporter específico da plataforma fiscal final (plugar em `exporters/`, mesma interface
  `export(data, output_dir)` de `JsonExporter`).
