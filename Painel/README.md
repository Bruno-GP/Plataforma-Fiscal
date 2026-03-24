# Painel Plataforma Fiscal

Frontend em React + Vite para operação da plataforma fiscal, com autenticação, importações, dashboards analíticos e central de relatórios.

## Stack

- React 18
- TypeScript
- Vite 5
- React Router 6
- TanStack Query 5
- Tailwind CSS
- Radix UI
- Recharts

## Scripts disponíveis

```bash
npm install
npm run dev
npm run build
npm run lint
npm run preview
```

Se preferir, os comandos equivalentes com `yarn` também funcionam.

Observação:

- O projeto possui `vitest.config.ts` e arquivos de teste base, mas ainda não há script `test` definido em `package.json`.

## Ambiente

Crie `Painel/.env`:

```env
VITE_API_URL=http://localhost:8000
```

Normalização automática:

- `http://localhost:8000` -> `http://localhost:8000/api`
- `http://localhost:8000/api` -> mantido como está

## Estrutura principal

```text
Painel/
|-- public/
|-- src/
|   |-- components/
|   |-- contexts/
|   |-- hooks/
|   |-- pages/
|   |-- services/
|   `-- test/
|-- package.json
`-- README.md
```

## Rotas ativas

- `/login`
- `/interno/cadastro-empresa`
- `/analise-vendas`
- `/analise-compras`
- `/analise-clientes`
- `/relatorios-ia`
- `/importacao-xml`
- `/importacao-sped`
- `/`
- `/clientes` redireciona para `/analise-clientes`

## Rotas implementadas, mas fora do roteador principal

- `/configuracoes`
- `/atualizacoes`

Essas páginas existem no código, mas hoje estão comentadas em `src/App.tsx`.

## Comportamento da aplicação

- Sessão persistida em `localStorage`
- Proteção de rotas via `MainLayout`
- Redirecionamento automático por perfil fiscal:
  - empresa SPED -> bloqueia fluxo XML
  - empresa XML -> bloqueia fluxo SPED
- Aviso superior quando existem XMLs pendentes de processamento

## Páginas principais

### Login

- Autenticação via `POST /api/auth/entrar`
- Normalização de erros de API para exibição amigável

### Cadastro de empresa

- Cadastro via `POST /api/auth/registrar`
- Define o perfil operacional com `tem_sped`

### Importação XML

- Upload de XML
- Consulta de pendências
- Processamento de XMLs importados

### Importação SPED

- Upload de arquivos TXT
- Consulta de pendências
- Processamento de arquivos importados

### Análise de vendas

- KPIs por período
- Rankings de clientes, produtos e cidades
- Evolução temporal
- Comparativo com período anterior
- Seção de análise ABC

### Análise de compras

- Total comprado por período
- Rankings de fornecedores e produtos
- Evolução mensal
- Comparativo com período anterior

### Análise de clientes

- Busca de clientes
- Concentração de receita
- Identificação de risco de perda por comparação entre períodos

### Relatórios IA

- Geração de relatório para compras, vendas ou clientes
- Formato `executivo` ou `analitico`
- Campo livre de layout para orientar a resposta em compras e vendas
- Exportação do relatório para PDF via impressão do navegador

## Integração com a API

### Auth

- `POST /api/auth/entrar`
- `POST /api/auth/registrar`

### NFe

- `GET /api/nfe/kpis`
- `GET /api/nfe/kpis/comparativo/atual`
- `GET /api/nfe/analise/compras`
- `GET /api/nfe/analise/vendas`
- `GET /api/nfe/analise/clientes`
- `POST /api/nfe/xml/importar`
- `GET /api/nfe/xml/pendencias`
- `POST /api/nfe/xml/processar-importados`

### SPED

- `GET /api/sped/kpis`
- `GET /api/sped/analise/compras`
- `GET /api/sped/analise/vendas`
- `GET /api/sped/analise/clientes`
- `POST /api/sped/importar`
- `GET /api/sped/pendencias`
- `POST /api/sped/processar-importados`

## Recursos auxiliares no código

- `ChatContext` e `ChatWidget` existem, mas o widget está desabilitado no layout.
- O chat atual usa respostas simuladas no frontend e não integra com a API.
- A página de atualizações lê um changelog local em `src/contexts/updates.ts`.

## Build e qualidade

### Build

```bash
npm run build
```

### Lint

```bash
npm run lint
```

### Preview

```bash
npm run preview
```

## Troubleshooting

- Sem dados na tela: valide `VITE_API_URL`, login e disponibilidade da API.
- CORS: ajuste a configuração no backend.
- Erro ao importar: confirme se a empresa está no fluxo correto de XML ou SPED.
- Relatório IA indisponível: valide `OPENAI_API_KEY` na API.
- PDF não gerado: confirme se o navegador permite a janela de impressão.
