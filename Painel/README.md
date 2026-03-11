# Painel NFe (React + Vite)

Painel web para autenticação, acompanhamento de KPIs fiscais e operação de importação/processamento de XMLs de NFe.

## O que existe hoje

### Funcionalidades ativas

- Login (`/login`)
- Dashboard (`/dashboard`)
- Faturamento (`/faturamento`)
- Importação de XML (`/importacao-xml`)
- Cadastro interno de empresa (`/interno/cadastro-empresa`)

### Funcionalidades retiradas da navegação

As rotas abaixo estão fora da navegação principal (comentadas no roteador):

- Clientes (`/clientes`)
- Configurações (`/configuracoes`)

## Requisitos

- Node.js 18+
- Yarn (recomendado)

## Configuração

1. Instale dependências:

```bash
yarn install
```

## Integração com a plataforma

Para o painel funcionar corretamente, a API deve estar em execução e acessível pela `VITE_API_URL`.

Fluxo recomendado:

1. Suba a API (`python -m uvicorn app.main:app --reload` na pasta `API`).
2. Configure `VITE_API_URL` apontando para a API (ex.: `http://localhost:8000`).
3. Inicie o painel com `yarn dev`.

> Você também pode usar `VITE_API_URL=http://localhost:8000/api`; o front-end normaliza os dois formatos.

2. Configure a API em `.env`:

```bash
VITE_API_URL=http://localhost:8000
```

> O front normaliza automaticamente para incluir `/api` quando necessário.

## Execução

```bash
yarn dev
```

Aplicação disponível em `http://localhost:5173`.

## Build

```bash
yarn build
yarn preview
```

## Endpoints consumidos

- `POST /api/auth/entrar`
- `POST /api/auth/registrar`
- `GET /api/nfe/kpis`
- `GET /api/nfe/kpis/comparativo/atual`
- `POST /api/nfe/xml/importar`
- `GET /api/nfe/xml/pendencias`
- `POST /api/nfe/xml/processar-importados`