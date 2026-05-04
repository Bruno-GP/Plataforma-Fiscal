# API Plataforma Fiscal

Backend em FastAPI responsavel por autenticacao, importacao fiscal, processamento e consultas analiticas.

## Atualizacao da documentacao

### O que foi atualizado

- A lista de endpoints e modulos foi revisada para refletir a API atualmente exposta em `/api`.
- A secao de regras de negocio agora considera o fluxo separado entre XML/NFe e SPED.
- A documentacao de ambiente foi ajustada para incluir CORS, banco dedicado para SPED e configuracao opcional de OpenAI.

### O que foi adicionado

- Modulo `/api/ncm` com sincronizacao IBPT e consulta tributaria por NCM/UF.
- Modulo `/api/reforma-tributaria` com tributos, apuracao, documentos, itens e memoria de calculo.
- Referencia ao material operacional em `API/docs/ibpt-cron.md`.
- Registro das migracoes SQL em `API/migrations/`.
- Registro do startup que garante colunas e tabelas auxiliares no banco.

### O que foi tirado

- A descricao antiga focada apenas em XML/NFe foi substituida por uma visao mais fiel ao backend atual, que cobre tambem SPED e NCM.
- O README deixou de sugerir que a estrutura SQL esta concentrada em um unico ponto; agora o texto informa a distribuicao real entre scripts, models e migrations.

## Resumo

- Base local: `http://localhost:8000`
- Prefixo da API: `/api`
- Swagger: `/docs`
- Health check: `/health`

## Documentacao operacional

- [Contratos de API](../docs/api-contracts.md)
- [Banco de dados](../docs/database.md)
- [Migrations](../docs/migrations.md)
- [Seguranca](../docs/security.md)
- [Importacao e processamento fiscal](../docs/importacao-processamento.md)
- [Reforma Tributaria](../docs/reforma-tributaria.md)
- [Relatorios com IA](../docs/relatorios-ia.md)
- [Deploy](../docs/deploy.md)
- [Auditoria operacional](../docs/auditoria-operacional.md)

## Stack

- FastAPI `0.115.0`
- Uvicorn `0.30.6`
- Pydantic `2.8.2`
- Psycopg `3.2.1`
- OpenAI SDK `1.51.2`
- PostgreSQL

## Estrutura principal

```text
API/
|-- app/
|   |-- api/
|   |   |-- auth/
|   |   |-- geo/
|   |   |-- ncm/
|   |   |-- nfe/
|   |   |-- reforma_tributaria/
|   |   `-- sped/
|   |-- core/
|   |-- domain/
|   |-- models/
|   |-- services/
|   |-- file/
|   |-- requirements.txt
|   `-- main.py
|-- docs/
|-- migrations/
|-- scripts/
`-- README.md
```

## Como executar

Na raiz do repositorio:

```bash
pip install -r API/app/requirements.txt
cd API
python -m uvicorn app.main:app --reload
```

Endpoints locais:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## Configuracao de ambiente

As variaveis sao carregadas de `API/app/.env`.

### Banco principal

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=nfe
POSTGRES_DB_NFE=nfe
POSTGRES_DB_SPED=sped_fiscal
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

### Banco dedicado para SPED

```env
POSTGRES_SPED_HOST=localhost
POSTGRES_SPED_PORT=5432
POSTGRES_SPED_DB=sped_fiscal
POSTGRES_SPED_USER=postgres
POSTGRES_SPED_PASSWORD=postgres
```

### CORS

```env
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_ORIGIN_REGEX=
```

Observacoes:

- A aplicacao expande automaticamente aliases `localhost` e `127.0.0.1`.
- Se `CORS_ALLOW_ORIGINS=*`, `allow_credentials` e desativado por seguranca.
- Existe regex local padrao para suportar portas variaveis em desenvolvimento.

### OpenAI

```env
OPENAI_API_KEY=<sua-chave>
OPENAI_REPORT_MODEL=gpt-4o-mini
```

`OPENAI_API_KEY` so e obrigatoria quando `gerar_relatorio_ia=true`.

## Modulos de rota

- `/api/auth`
- `/api/nfe`
- `/api/sped`
- `/api/geo`
- `/api/ncm`
- `/api/reforma-tributaria`

## Endpoints principais

### Sistema

- `GET /health`

### Auth

- `POST /api/auth/registrar`
- `POST /api/auth/entrar`
- `GET /api/auth/sessao`
- `POST /api/auth/sair`

### NFe

- `POST /api/nfe/processar`
- `POST /api/nfe/xml/importar`
- `GET /api/nfe/xml/pendencias`
- `POST /api/nfe/xml/processar-importados`
- `GET /api/nfe/kpis`
- `GET /api/nfe/kpis/comparativo`
- `GET /api/nfe/kpis/comparativo/atual`
- `GET /api/nfe/analise/compras`
- `GET /api/nfe/analise/vendas`
- `GET /api/nfe/analise/clientes`
- `GET /api/nfe/analise/fiscal/cfop`
- `GET /api/nfe/analise/fiscal/ncm`
- `GET /api/nfe/analise/fiscal/hierarquia`
- `GET /api/nfe/analise/compras/dashboard`
- `GET /api/nfe/analise/vendas/dashboard`
- `GET /api/nfe/notas`
- `GET /api/nfe/notas/detalhado`

### SPED

- `POST /api/sped/processar`
- `POST /api/sped/importar`
- `GET /api/sped/pendencias`
- `POST /api/sped/processar-importados`
- `GET /api/sped/kpis`
- `GET /api/sped/clientes`
- `GET /api/sped/analise/compras`
- `GET /api/sped/analise/vendas`
- `GET /api/sped/analise/clientes`
- `GET /api/sped/analise/fiscal/cfop`
- `GET /api/sped/analise/fiscal/ncm`
- `GET /api/sped/analise/fiscal/hierarquia`
- `GET /api/sped/analise/compras/dashboard`
- `GET /api/sped/analise/vendas/dashboard`

### Geo

- `GET /api/geo/municipios`
- `GET /api/geo/municipios/{uf}`

### NCM / IBPT

- `POST /api/ncm/ibpt/sincronizar`
- `GET /api/ncm/tributacao`

### Reforma Tributaria

- `GET /api/reforma-tributaria/tributos`
- `GET /api/reforma-tributaria/apuracao`
- `GET /api/reforma-tributaria/documentos/{origem_documento}/{documento_id}/tributos`
- `GET /api/reforma-tributaria/itens/{origem_item}/{item_id}/tributos`
- `GET /api/reforma-tributaria/memoria-calculo`

Contratos detalhados, parametros, exemplos e erros comuns estao em [../docs/api-contracts.md](../docs/api-contracts.md).

## Regras de negocio

- Empresa com `tem_sped=true` nao pode usar rotas XML.
- Empresa com `tem_sped=false` nao pode usar rotas SPED.
- NFe aceita ate `10.000` arquivos por importacao e apenas `.xml`.
- SPED aceita ate `500` arquivos por importacao e apenas `.txt`.
- Uploads tambem respeitam `UPLOAD_MAX_XML_BYTES`, `UPLOAD_MAX_TXT_BYTES` e `UPLOAD_MAX_TOTAL_BYTES`.
- A validacao de CNPJ ocorre em varios endpoints com janela minima e maxima de tamanho.
- As rotas de Reforma Tributaria exigem escopo de empresa autenticada.
- `apuracao` e `memoria-calculo` exigem `emitente_cnpj` e aceitam filtros opcionais por `periodo_ano`, `periodo_mes` e `tributo_codigo`.
- A consulta de memoria de calculo limita a paginacao entre `1` e `1000` registros por chamada.
- A Reforma Tributaria exposta pela API consulta dados persistidos e estruturas de rastreabilidade; nao ha garantia de motor legal completo para CBS, IBS e IS.

## Relatorios com IA

As rotas de analise aceitam geracao opcional de relatorio:

- `gerar_relatorio_ia=true`
- `formato_relatorio=executivo|analitico`
- `layout` disponivel para compras e vendas

Implementacao atual:

- O servico usa `OpenAI().responses.create(...)`
- Modelo padrao: `gpt-4o-mini`
- Prompts ficam em `API/app/services/AI/Agents/`

## Arquivos e dados auxiliares

- Scripts SQL: `API/app/file/sql/`
- Prompt templates: `API/app/services/AI/Agents/`
- GeoJSON local: `API/app/services/Municipios/`
- Catalogo NCM e arquivos IBPT: `API/app/services/NCM/`
- Services da Reforma Tributaria: `API/app/services/reforma_tributaria/`
- Guia operacional: `API/docs/ibpt-cron.md`
- Script manual de sincronizacao: `API/scripts/sync_ibpt.py`

## Banco de dados

- Nao ha mecanismo de migracao automatizado no repositorio.
- A estrutura SQL esta distribuida entre `app/file/sql/`, `app/models/` e `migrations/`.
- Ha suporte para separacao entre base NFe e base SPED.
- No startup, a aplicacao tenta garantir a coluna `tem_sped`, tabelas auxiliares de NCM/IBPT, indices de analise fiscal e as estruturas da Reforma Tributaria.
- As migracoes da Reforma Tributaria estao em `004_add_reforma_tributaria_base.sql`, `005_add_reforma_tributaria_documentos_itens.sql` e `006_add_reforma_tributaria_creditos_debitos_memoria.sql`.
- O detalhamento de ordem, riscos e checklist esta em [../docs/database.md](../docs/database.md) e [../docs/migrations.md](../docs/migrations.md).

## Seguranca operacional

- A API aceita cookie HttpOnly e Bearer token.
- Rotas fiscais usam escopo por CNPJ para reduzir risco multiempresa.
- CORS deve ser restrito em producao.
- `AUTH_SECRET_KEY` nao pode ficar com o padrao de desenvolvimento.
- Dados enviados para relatorios IA podem conter informacoes fiscais sensiveis.

Veja [../docs/security.md](../docs/security.md) antes de publicar a API.

## Respostas e erros comuns

- `400 Bad Request`: parametros invalidos, empresa em fluxo errado, arquivo invalido
- `401 Unauthorized`: falha de autenticacao
- `404 Not Found`: sem dados, sem pendencias ou periodo inexistente
- `502 Bad Gateway`: falha ao gerar relatorio com IA ou ao sincronizar dados externos
- `503 Service Unavailable`: indisponibilidade de banco ou OpenAI

## Observacoes de manutencao

- O nome exibido no `FastAPI(...)` ainda esta como `API - Agente Extrator NFe`, embora a API hoje cubra NFe, SPED e NCM.
- Consulte sempre `/docs` para confirmar schemas e contratos atualizados.
- Nao documente um endpoint como funcional sem conferir a rota correspondente em `API/app/api/`.
