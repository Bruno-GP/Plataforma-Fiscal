# API Plataforma Fiscal

Backend em FastAPI responsável por autenticação, importação fiscal, processamento e consultas analíticas.

## Resumo

- Base local: `http://localhost:8000`
- Prefixo da API: `/api`
- Swagger: `/docs`
- Health check: `/health`

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
|   |   |-- nfe/
|   |   `-- sped/
|   |-- core/
|   |-- domain/
|   |-- models/
|   |-- services/
|   |-- file/
|   |-- requirements.txt
|   `-- main.py
`-- README.md
```

## Como executar

Na raiz do repositório:

```bash
pip install -r API/app/requirements.txt
cd API
python -m uvicorn app.main:app --reload
```

Endpoints locais:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## Configuração de ambiente

As variáveis são carregadas de `API/app/.env`.

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

Observações:

- A aplicação expande automaticamente aliases `localhost` e `127.0.0.1`.
- Se `CORS_ALLOW_ORIGINS=*`, `allow_credentials` é desativado por segurança.
- Existe regex local padrão para suportar portas variáveis em desenvolvimento.

### OpenAI

```env
OPENAI_API_KEY=<sua-chave>
OPENAI_REPORT_MODEL=gpt-4o-mini
```

`OPENAI_API_KEY` só é obrigatória quando `gerar_relatorio_ia=true`.

## Módulos de rota

- `/api/auth`
- `/api/nfe`
- `/api/sped`
- `/api/geo`

## Endpoints principais

### Sistema

- `GET /health`

### Auth

- `POST /api/auth/registrar`
- `POST /api/auth/entrar`

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

### Geo

- `GET /api/geo/municipios`
- `GET /api/geo/municipios/{uf}`

## Regras de negócio

- Empresa com `tem_sped=true` não pode usar rotas XML.
- Empresa com `tem_sped=false` não pode usar rotas SPED.
- NFe aceita até `10.000` arquivos por importação e apenas `.xml`.
- SPED aceita até `500` arquivos por importação e apenas `.txt`.
- A validação de CNPJ ocorre em vários endpoints com janela mínima e máxima de tamanho.

## Relatórios com IA

As rotas de análise aceitam geração opcional de relatório:

- `gerar_relatorio_ia=true`
- `formato_relatorio=executivo|analitico`
- `layout` disponível para compras e vendas

Implementação atual:

- O serviço usa `OpenAI().responses.create(...)`
- Modelo padrão: `gpt-4o-mini`
- Prompts ficam em `API/app/services/AI/Agents/`

## Arquivos e dados auxiliares

- Scripts SQL: `API/app/file/sql/`
- Prompt templates: `API/app/services/AI/Agents/`
- GeoJSON local: `API/app/services/Municipios/`
- Arquivos de exemplo e massa de teste: `API/app/file/`

## Banco de dados

- Não há mecanismo de migração automatizado no repositório.
- A estrutura SQL está distribuída entre scripts em `file/sql/` e `models/`.
- Há suporte para separação entre base NFe e base SPED.

## Respostas e erros comuns

- `400 Bad Request`: parâmetros inválidos, empresa em fluxo errado, arquivo inválido
- `401 Unauthorized`: falha de autenticação
- `404 Not Found`: sem dados, sem pendências ou período inexistente
- `502 Bad Gateway`: falha ao gerar relatório com IA
- `503 Service Unavailable`: indisponibilidade de banco ou OpenAI

## Observações de manutenção

- O nome exibido no `FastAPI(...)` ainda está como `API - Agente Extrator NFe`, embora a API hoje cubra NFe e SPED.
- Consulte sempre `/docs` para confirmar schemas e contratos atualizados.
