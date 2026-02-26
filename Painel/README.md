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