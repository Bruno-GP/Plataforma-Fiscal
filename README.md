# Plataforma Fiscal

Repositório com duas aplicações que operam em conjunto:

- `API/`: backend em FastAPI para autenticação, importação fiscal, processamento e consultas analíticas.
- `Painel/`: frontend em React + Vite para operação diária, importações, dashboards e relatórios.

Cada módulo possui seu próprio guia:

- [API/README.md](C:\Users\supor\OneDrive\Área de Trabalho\Github\Plataforma-Fiscal\API\README.md)
- [Painel/README.md](C:\Users\supor\OneDrive\Área de Trabalho\Github\Plataforma-Fiscal\Painel\README.md)

## Visão geral

Fluxo principal da plataforma:

1. A empresa é cadastrada e passa a ter um perfil fiscal definido por `tem_sped`.
2. O Painel autentica o usuário e direciona o fluxo conforme o perfil:
   - `tem_sped=false`: operação com XML/NFe
   - `tem_sped=true`: operação com SPED Fiscal
3. Os arquivos são importados para staging.
4. A API processa os arquivos pendentes e consolida KPIs.
5. O Painel exibe dashboards de vendas, compras e clientes.
6. Relatórios narrativos podem ser gerados via OpenAI nas análises suportadas.

## Estrutura

```text
.
|-- API/
|   |-- app/
|   |-- README.md
|   `-- Arquivo SQL para validacao de dados.sql
|-- Painel/
|   |-- src/
|   |-- public/
|   `-- README.md
`-- README.md
```

## Stack

- Backend: FastAPI, Pydantic v2, Psycopg v3, PostgreSQL, OpenAI SDK
- Frontend: React 18, TypeScript, Vite, React Router, TanStack Query, Tailwind

## Quick start

### API

```bash
pip install -r API/app/requirements.txt
cd API
python -m uvicorn app.main:app --reload
```

- API local: `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`

### Painel

```bash
cd Painel
npm install
npm run dev
```

Se preferir, `yarn install` e `yarn dev` também funcionam.

- Painel local: `http://localhost:5173`

### Integração

Crie `Painel/.env`:

```env
VITE_API_URL=http://localhost:8000
```

O frontend normaliza a URL automaticamente:

- `http://localhost:8000` -> `http://localhost:8000/api`
- `http://localhost:8000/api` -> mantido como está

## Funcionalidades atuais

### API

- Autenticação com cadastro e login
- Processamento de XML/NFe
- Processamento de SPED Fiscal
- Importação para staging com consulta de pendências
- KPIs consolidados por período
- Análises de compras, vendas e clientes
- Comparativo mensal de KPIs para NFe
- GeoJSON de municípios
- Relatórios narrativos via OpenAI

### Painel

- Login e cadastro de empresa
- Controle de sessão em `localStorage`
- Navegação condicionada por perfil XML/SPED
- Importação e processamento de XML
- Importação e processamento de SPED
- Dashboard de vendas
- Dashboard de compras
- Dashboard de clientes
- Central de relatórios com IA e exportação para PDF

## Observações importantes

- Empresas configuradas para SPED não devem usar o fluxo XML.
- Empresas configuradas para XML não devem usar o fluxo SPED.
- O painel possui páginas de `Atualizações` e `Configurações` implementadas no código, mas elas ainda não estão ativas no roteador principal.
- O chat do frontend existe como componente/contexto local, porém está desabilitado no layout e hoje não conversa com a API.

## Requisitos

- Python 3.11+
- Node.js 18+
- PostgreSQL

## Troubleshooting rápido

- CORS: revise `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_CREDENTIALS` e `CORS_ALLOW_ORIGIN_REGEX` na API.
- Tela sem dados: confirme `VITE_API_URL`, API ativa e sessão válida.
- Importação rejeitada: valide o perfil da empresa (`tem_sped`) e o tipo de arquivo enviado.
- Relatórios IA indisponíveis: configure `OPENAI_API_KEY` no backend.
