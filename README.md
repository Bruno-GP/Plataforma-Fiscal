# Plataforma Fiscal

Repositorio com duas aplicacoes que operam em conjunto:

- `API/`: backend em FastAPI para autenticacao, importacao fiscal, processamento e consultas analiticas.
- `Painel/`: frontend em React + Vite para operacao diaria, importacoes, dashboards e relatorios.

Cada modulo possui seu proprio guia:

- [API/README.md](C:\Users\supor\OneDrive\Área de Trabalho\Github\Plataforma-Fiscal\API\README.md)
- [Painel/README.md](C:\Users\supor\OneDrive\Área de Trabalho\Github\Plataforma-Fiscal\Painel\README.md)

## Atualizacao da documentacao

### O que foi atualizado

- A documentacao foi alinhada com as rotas ativas do painel e com os modulos reais publicados pela API.
- As secoes de funcionalidades agora refletem o fluxo atual de XML, SPED, analise fiscal, inconsistencias e integracao com NCM/IBPT.
- As observacoes operacionais foram revisadas para deixar claro o que segue ativo, o que esta desabilitado e o que ficou fora do roteador principal.

### O que foi adicionado

- Registro da pagina de analise fiscal por hierarquia `Estado > Cidade > NCM > Produto`.
- Registro da central de inconsistencias, com pendencias fiscais e historico local das ultimas operacoes.
- Registro do modulo NCM/IBPT da API, incluindo consulta tributaria e sincronizacao de catalogo.
- Referencia ao guia operacional do cron IBPT em `API/docs/ibpt-cron.md`.

### O que foi tirado

- A documentacao antiga deixava implicito que apenas vendas, compras e clientes estavam disponiveis como analise principal; isso foi substituido pela lista real de telas ativas.
- As paginas `Atualizacoes` e `Configuracoes` continuam no codigo, mas foram retiradas do fluxo ativo do roteador principal e agora isso esta documentado explicitamente.
- O chat permanece fora do layout principal e foi removido da descricao de funcionalidades ativas.

## Visao geral

Fluxo principal da plataforma:

1. A empresa e cadastrada e passa a ter um perfil fiscal definido por `tem_sped`.
2. O Painel autentica o usuario e direciona o fluxo conforme o perfil:
   - `tem_sped=false`: operacao com XML/NFe
   - `tem_sped=true`: operacao com SPED Fiscal
3. Os arquivos sao importados para staging.
4. A API processa os arquivos pendentes e consolida KPIs.
5. O Painel exibe dashboards, analises fiscais e acompanhamentos operacionais.
6. Relatorios narrativos podem ser gerados via OpenAI nas analises suportadas.

## Estrutura

```text
.
|-- API/
|   |-- app/
|   |-- docs/
|   |-- migrations/
|   |-- scripts/
|   `-- README.md
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
- KPIs consolidados por periodo
- Analises de compras, vendas e clientes
- Analise fiscal hierarquica por estado, cidade, NCM e produto
- Comparativo mensal de KPIs para NFe
- GeoJSON de municipios
- Consulta tributaria NCM/IBPT e sincronizacao de catalogo
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
- Dashboard de clientes
- Central de inconsistencias com historico local de operacoes
- Central de relatorios com IA e exportacao para PDF

## Observacoes importantes

- Empresas configuradas para SPED nao devem usar o fluxo XML.
- Empresas configuradas para XML nao devem usar o fluxo SPED.
- O painel possui paginas de `Atualizacoes` e `Configuracoes` implementadas no codigo, mas elas nao estao ativas no roteador principal.
- O chat do frontend existe como componente/contexto local, porem esta desabilitado no layout e hoje nao conversa com a API.

## Requisitos

- Python 3.11+
- Node.js 18+
- PostgreSQL

## Troubleshooting rapido

- CORS: revise `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_CREDENTIALS` e `CORS_ALLOW_ORIGIN_REGEX` na API.
- Tela sem dados: confirme `VITE_API_URL`, API ativa e sessao valida.
- Importacao rejeitada: valide o perfil da empresa (`tem_sped`) e o tipo de arquivo enviado.
- Relatorios IA indisponiveis: configure `OPENAI_API_KEY` no backend.
