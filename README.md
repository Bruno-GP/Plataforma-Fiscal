# Plataforma Fiscal

Repositorio com duas aplicacoes que operam em conjunto:

- `API/`: backend em FastAPI para autenticacao, importacao fiscal, processamento e consultas analiticas.
- `Painel/`: frontend em React + Vite para operacao diaria, importacoes, dashboards e relatorios.

Cada modulo possui seu proprio guia e a documentacao operacional fica em `docs/`:

- [API/README.md](API/README.md)
- [Painel/README.md](Painel/README.md)
- [Contratos de API](docs/api-contracts.md)
- [Banco de dados](docs/database.md)
- [Migrations](docs/migrations.md)
- [Reforma Tributaria](docs/reforma-tributaria.md)
- [Seguranca](docs/security.md)
- [Importacao e processamento](docs/importacao-processamento.md)
- [Relatorios com IA](docs/relatorios-ia.md)
- [Matriz XML versus SPED](docs/matriz-xml-sped.md)
- [Testes](docs/testing.md)
- [Setup local](docs/setup.md)
- [Processamento de dados](docs/data-processing.md)
- [Jobs assincronos](docs/jobs.md)
- [Troubleshooting de jobs](docs/troubleshooting-jobs.md)
- [Deploy](docs/deploy.md)
- [Checklist de producao](docs/production-checklist.md)
- [Auditoria operacional](docs/auditoria-operacional.md)

## Leitura recomendada

Para manutencao ou deploy, leia primeiro:

1. [Banco de dados](docs/database.md)
2. [Migrations](docs/migrations.md)
3. [Seguranca](docs/security.md)
4. [Contratos de API](docs/api-contracts.md)
5. [Importacao e processamento](docs/importacao-processamento.md)

Para auditoria fiscal e evolucao de produto, leia tambem [Reforma Tributaria](docs/reforma-tributaria.md), [Relatorios com IA](docs/relatorios-ia.md) e [Matriz XML versus SPED](docs/matriz-xml-sped.md).

## Visao geral

Fluxo principal da plataforma:

1. A empresa e cadastrada e passa a ter um perfil fiscal definido por `tem_sped`.
2. O Painel autentica o usuario e direciona o fluxo conforme o perfil:
   - `tem_sped=false`: operacao com XML/NFe
   - `tem_sped=true`: operacao com SPED Fiscal
3. Os arquivos sao importados para staging.
4. A API enfileira o processamento dos arquivos pendentes em jobs assincronos.
5. Workers Celery processam XML/NFe ou SPED, atualizam o status do job e consolidam KPIs.
6. O Painel exibe dashboards, analises fiscais e acompanhamentos operacionais.
7. Relatorios narrativos podem ser gerados via OpenAI nas analises suportadas.

## Estrutura

```text
.
|-- API/
|   |-- app/
|   |-- docs/
|   |-- scripts/
|   |-- SQL/
|   `-- README.md
|-- Painel/
|   |-- src/
|   |-- public/
|   `-- README.md
`-- README.md
```

## Stack

- Backend: FastAPI, Pydantic v2, Psycopg v3, PostgreSQL, Redis, Celery, OpenAI SDK
- Frontend: React 18, TypeScript, Vite, React Router, TanStack Query, Tailwind

## Quick start

### API

Execucao apenas da API:

```bash
pip install -r API/app/requirements.txt
cd API
python -m uvicorn app.main:app --reload
```

- API local: `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- Health DB: `http://localhost:8000/health/db`
- Health Redis: `http://localhost:8000/health/redis`
- Swagger: `http://localhost:8000/docs`

Esse comando sobe somente a API. Para usar os processamentos assincronos de importados, mantenha Redis e workers Celery ativos em paralelo.

Redis via Docker Compose:

```bash
docker compose up -d redis
```

Redis compativel no Windows sem Docker/WSL, usando Garnet:

```powershell
cd "C:\Users\supor\OneDrive\Área de Trabalho\Garnet\garnet-main"
dotnet run -c Release --project .\main\GarnetServer\GarnetServer.csproj -- --port 6379 --lua
```

Workers Celery em terminais separados:

```bash
cd API
celery -A app.workers.celery_app worker --loglevel=info -Q nfe
celery -A app.workers.celery_app worker --loglevel=info -Q sped
```

No Windows, use a venv local e `--pool=solo`:

```powershell
cd "C:\Users\supor\OneDrive\Área de Trabalho\Github\Plataforma-Fiscal\API"
.\.venv-local\Scripts\celery.exe -A app.workers.celery_app worker --loglevel=info -Q nfe --pool=solo
```

Se preferir subir o ambiente completo de uma vez:

```bash
docker compose up --build
```

O Compose sobe PostgreSQL, Redis, API, workers e Painel.

### Painel

```bash
cd Painel
npm install
npm run dev
```

Se preferir, `yarn install` e `yarn dev` tambem funcionam.

- Painel local: `http://localhost:5173`

### Integracao

Crie `Painel/.env`:

```env
VITE_API_URL=http://localhost:8000
```

O frontend normaliza a URL automaticamente:

- `http://localhost:8000` -> `http://localhost:8000/api`
- `http://localhost:8000/api` -> mantido como esta

## Funcionalidades atuais

### API

- Autenticacao com cadastro e login
- Processamento de XML/NFe
- Processamento de SPED Fiscal
- Importacao para staging com consulta de pendencias
- Jobs assincronos para processar importados XML/NFe e SPED
- KPIs consolidados por periodo
- Analises de compras, vendas e clientes
- Analise fiscal hierarquica por estado, cidade, NCM e produto
- Comparativo mensal de KPIs para NFe
- GeoJSON de municipios
- Consulta tributaria NCM/IBPT e sincronizacao de catalogo
- Consultas da Reforma Tributaria para tributos, apuracao, documentos, itens e memoria de calculo
- Relatorios narrativos via OpenAI

### Painel

- Login e cadastro de empresa
- Controle de sessao em `localStorage`
- Navegacao condicionada por perfil XML/SPED
- Importacao e processamento de XML
- Importacao e processamento de SPED
- Dashboard de vendas
- Dashboard de compras
- Analise fiscal por hierarquia
- Reforma Tributaria com filtros por periodo e tributo
- Dashboard de clientes
- Central de inconsistencias com historico local de operacoes
- Central de relatorios com IA e exportacao para PDF

## Status das funcionalidades

| Funcionalidade | Status | Observacao |
| --- | --- | --- |
| Login e cadastro de empresa | Ativa | Sessao persistida no frontend e cookie HttpOnly na API. |
| Importacao XML/NFe | Ativa para `tem_sped=false` | Bloqueada para empresas SPED. |
| Importacao SPED | Ativa para `tem_sped=true` | Bloqueada para empresas XML. |
| Jobs de processamento | Ativos | `processar-importados` retorna `202` com `job_id`; status em `/api/jobs`. |
| Dashboards e analises | Ativas | Usam endpoints NFe ou SPED conforme perfil. |
| Analise fiscal hierarquica | Ativa | Estado, cidade, NCM e produto. |
| Reforma Tributaria | Ativa como consulta de dados persistidos | Nao e motor legal completo de CBS/IBS/IS. |
| NCM/IBPT | Ativa | Sincronizacao depende de fonte externa e catalogos. |
| Relatorios IA | Dependente de configuracao | Exige `OPENAI_API_KEY`; apoio analitico, nao parecer fiscal. |
| Inconsistencias | Ativa | Combina pendencias da API e historico local. |
| Atualizacoes e Configuracoes | Implementadas, fora do fluxo | Paginas existem, mas rotas estao comentadas no roteador principal. |
| Chat | Desabilitado | Componentes existem, sem integracao ativa com API. |

## Observacoes importantes

- Empresas configuradas para SPED nao devem usar o fluxo XML.
- Empresas configuradas para XML nao devem usar o fluxo SPED.
- O projeto usa Alembic no ambiente Docker e mantem guias operacionais em [Migrations](docs/migrations.md).
- Dados fiscais e relatorios IA exigem validacao humana antes de uso oficial.
- O painel possui paginas de `Atualizacoes` e `Configuracoes` implementadas no codigo, mas elas nao estao ativas no roteador principal.
- O chat do frontend existe como componente/contexto local, porem esta desabilitado no layout e hoje nao conversa com a API.

## Requisitos

- Python 3.11+
- Node.js 18+
- PostgreSQL
- Redis para filas Celery

## Troubleshooting rapido

- CORS: revise `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_CREDENTIALS` e `CORS_ALLOW_ORIGIN_REGEX` na API.
- Tela sem dados: confirme `VITE_API_URL`, API ativa e sessao valida.
- Importacao rejeitada: valide o perfil da empresa (`tem_sped`) e o tipo de arquivo enviado.
- Job parado ou falhando: verifique Redis, workers Celery e consulte [Troubleshooting de jobs](docs/troubleshooting-jobs.md).
- Reforma Tributaria sem dados: confirme se o usuario possui `emitente_cnpj` valido e se as migracoes `004` a `006` foram aplicadas.
- Relatorios IA indisponiveis: configure `OPENAI_API_KEY` no backend.
