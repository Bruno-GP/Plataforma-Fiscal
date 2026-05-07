# Painel Plataforma Fiscal

Frontend em React + Vite para operacao da plataforma fiscal, com autenticacao, importacoes, dashboards analiticos e central de relatorios.

## Atualizacao da documentacao

### O que foi atualizado

- A lista de rotas foi revisada para refletir o roteador principal configurado em `src/App.tsx`.
- As secoes de comportamento agora descrevem o fluxo real de XML, SPED, analise fiscal e inconsistencias.
- O texto sobre recursos auxiliares foi ajustado para diferenciar o que esta ativo do que continua apenas implementado no codigo.

### O que foi adicionado

- Documentacao da pagina `Analise Fiscal` com drill-down por estado, cidade, NCM e produto.
- Documentacao da `Central de inconsistencias`, com pendencias fiscais e historico salvo em `localStorage`.
- Documentacao da tela `Reforma Tributaria`, com apuracao por tributo e memoria de calculo.
- Registro das rotas de detalhamento de vendas e de compras no panorama do painel.
- Registro do changelog local consumido pela pagina `Atualizacoes`.

### O que foi tirado

- As paginas `Configuracoes` e `Atualizacoes` deixaram de aparecer como rotas ativas no README e passaram a constar como implementadas, mas fora do roteador principal.
- O chat deixou de ser apresentado como funcionalidade do painel e passou a ser tratado como recurso desabilitado.
- A documentacao antiga resumia a navegacao a dashboards principais; agora ela mostra tambem telas operacionais e de suporte ao processo fiscal.

## Stack

- React 18
- TypeScript
- Vite 5
- React Router 6
- TanStack Query 5
- Tailwind CSS
- Radix UI
- Recharts

## Scripts disponiveis

```bash
npm install
npm run dev
npm run build
npm run lint
npm run preview
```

Se preferir, os comandos equivalentes com `yarn` tambem funcionam.

Observacao:

- O projeto possui `vitest.config.ts` e arquivos de teste base, mas ainda nao ha script `test` definido em `package.json`.
- Para detalhes de lacunas e recomendacoes de qualidade, veja [../docs/testing.md](../docs/testing.md).

## Ambiente

Para desenvolvimento local, crie `Painel/.env`:

```env
VITE_API_URL=http://localhost:8000
```

Para producao, o projeto pode usar `Painel/.env.production`:

```env
VITE_API_URL=https://api-plataforma-fiscal.onrender.com
```

Normalizacao automatica:

- `http://localhost:8000` -> `http://localhost:8000/api`
- `http://localhost:8000/api` -> mantido como esta

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
- `/analise-fiscal-cfop`
- `/reforma-tributaria`
- `/analise-clientes`
- `/detalhamento-vendas`
- `/detalhamento-compras`
- `/relatorios-ia`
- `/inconsistencias`
- `/importacao-xml`
- `/importacao-sped`
- `/`
- `/clientes` redireciona para `/analise-clientes`

## Rotas implementadas, mas fora do roteador principal

- `/configuracoes`
- `/atualizacoes`

Essas paginas existem no codigo, mas hoje estao comentadas em `src/App.tsx`.

## Status das funcionalidades

| Funcionalidade | Status | Observacao |
| --- | --- | --- |
| Login | Ativa | Usa `/api/auth/entrar`. |
| Cadastro de empresa | Ativa | Define `tem_sped`. |
| Importacao XML | Ativa para empresas XML | Redireciona empresas SPED. |
| Importacao SPED | Ativa para empresas SPED | Redireciona empresas XML. |
| Processamento assincrono | Ativo | Processamentos retornam `job_id` e sao acompanhados pela API de jobs. |
| Analises de vendas/compras/clientes | Ativas | Service escolhe NFe ou SPED conforme perfil. |
| Analise fiscal | Ativa | Drill-down por estado, cidade, NCM e produto. |
| Reforma Tributaria | Ativa como consulta | Depende de dados persistidos na API. |
| Relatorios IA | Dependente de configuracao | Exige IA habilitada na API. |
| Inconsistencias | Ativa | Usa pendencias da API e historico local. |
| Atualizacoes | Implementada, fora do fluxo | Rota comentada no `App.tsx`. |
| Configuracoes | Implementada, fora do fluxo | Rota comentada no `App.tsx`. |
| Chat | Desabilitado | Componentes existem, mas o widget nao esta ativo no layout. |

## Comportamento da aplicacao

- Sessao persistida em `localStorage`
- Protecao de rotas via `MainLayout`
- Redirecionamento automatico por perfil fiscal:
  - empresa SPED -> bloqueia fluxo XML
  - empresa XML -> bloqueia fluxo SPED
- Aviso superior quando existem arquivos pendentes de processamento
- Processamento de importados via jobs assincronos, com acompanhamento por status/progresso na API
- Historico local das ultimas operacoes fiscais utilizado pela central de inconsistencias
- Consulta da Reforma Tributaria habilitada para usuarios com `emitente_cnpj` valido

Risco conhecido: `localStorage` pode ser lido em caso de XSS. O token sensivel deve permanecer no cookie HttpOnly emitido pela API; os dados locais devem ser tratados como conveniencia de UI, nao como fronteira de seguranca.

## Paginas principais

### Login

- Autenticacao via `POST /api/auth/entrar`
- Normalizacao de erros de API para exibicao amigavel

### Cadastro de empresa

- Cadastro via `POST /api/auth/registrar`
- Define o perfil operacional com `tem_sped`

### Importacao XML

- Upload de XML
- Consulta de pendencias
- Processamento de XMLs importados via `POST /api/nfe/xml/processar-importados`, que retorna `job_id`

### Importacao SPED

- Upload de arquivos TXT
- Consulta de pendencias
- Processamento de arquivos importados via `POST /api/sped/processar-importados`, que retorna `job_id`

### Analise de vendas

- KPIs por periodo
- Rankings de clientes, produtos e cidades
- Evolucao temporal
- Comparativo com periodo anterior
- Secao de analise ABC

### Analise de compras

- Total comprado por periodo
- Rankings de fornecedores e produtos
- Evolucao mensal
- Comparativo com periodo anterior

### Analise fiscal

- KPIs de faturamento, impostos e percentual tributario
- Drill-down hierarquico em `Estado > Cidade > NCM > Produto`
- Busca no nivel atual e expansao controlada dos grupos
- Consumo de rotas especificas de NFe ou SPED conforme o perfil da empresa

### Reforma Tributaria

- Acompanhamento de CBS, IBS, Imposto Seletivo, apuracao e memoria de calculo
- Filtros por periodo e tributo
- Cards de debitos, creditos, saldo e total de memorias
- Tabela de apuracao por tributo com debitos, creditos, ajustes, saldo e status
- Tabela de memoria de calculo com etapa, base, aliquota, valor, fonte e hash
- Busca local na memoria por tributo, etapa, fonte, formula ou hash
- A tela nao calcula regra legal completa; ela exibe dados retornados pela API. Veja [../docs/reforma-tributaria.md](../docs/reforma-tributaria.md).

### Analise de clientes

- Busca de clientes
- Concentracao de receita
- Identificacao de risco de perda por comparacao entre periodos

### Inconsistencias

- Consulta de pendencias fiscais abertas
- Leitura do historico local das ultimas operacoes
- Atalho para retomar o fluxo XML ou SPED correspondente

### Relatorios IA

- Geracao de relatorio para compras, vendas ou clientes
- Formato `executivo` ou `analitico`
- Campo livre de layout para orientar a resposta em compras e vendas
- Exportacao do relatorio para PDF via impressao do navegador
- O relatorio e apoio analitico e precisa de validacao humana. Veja [../docs/relatorios-ia.md](../docs/relatorios-ia.md).

## Integracao com a API

Contratos completos com parametros, exemplos e erros comuns estao em [../docs/api-contracts.md](../docs/api-contracts.md).

### Auth

- `POST /api/auth/entrar`
- `POST /api/auth/registrar`
- `GET /api/auth/sessao`
- `POST /api/auth/sair`

### NFe

- `GET /api/nfe/kpis`
- `GET /api/nfe/kpis/comparativo/atual`
- `GET /api/nfe/analise/compras`
- `GET /api/nfe/analise/vendas`
- `GET /api/nfe/analise/clientes`
- `GET /api/nfe/analise/fiscal/cfop`
- `GET /api/nfe/analise/fiscal/ncm`
- `GET /api/nfe/analise/fiscal/hierarquia`
- `GET /api/nfe/analise/compras/dashboard`
- `GET /api/nfe/analise/vendas/dashboard`
- `GET /api/nfe/notas/detalhado`
- `POST /api/nfe/xml/importar`
- `GET /api/nfe/xml/pendencias`
- `POST /api/nfe/xml/processar-importados`

### SPED

- `GET /api/sped/kpis`
- `GET /api/sped/analise/compras`
- `GET /api/sped/analise/vendas`
- `GET /api/sped/analise/clientes`
- `GET /api/sped/analise/fiscal/cfop`
- `GET /api/sped/analise/fiscal/ncm`
- `GET /api/sped/analise/fiscal/hierarquia`
- `GET /api/sped/analise/compras/dashboard`
- `GET /api/sped/analise/vendas/dashboard`
- `POST /api/sped/importar`
- `GET /api/sped/pendencias`
- `POST /api/sped/processar-importados`

### Jobs

- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/metrics`

### Reforma Tributaria

- `GET /api/reforma-tributaria/tributos`
- `GET /api/reforma-tributaria/apuracao`
- `GET /api/reforma-tributaria/memoria-calculo`

## Recursos auxiliares no codigo

- `ChatContext` e `ChatWidget` existem, mas o widget esta desabilitado no layout.
- O chat atual usa respostas simuladas no frontend e nao integra com a API.
- A pagina de atualizacoes le um changelog local em `src/contexts/updates.ts`.

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
- CORS: ajuste a configuracao no backend.
- Erro ao importar: confirme se a empresa esta no fluxo correto de XML ou SPED.
- Processamento nao avanca: valide Redis, workers Celery e status em `/api/jobs/{job_id}`.
- Reforma Tributaria vazia: confirme `emitente_cnpj` na sessao e dados nas tabelas de apuracao/memoria.
- Relatorio IA indisponivel: valide `OPENAI_API_KEY` na API.
- PDF nao gerado: confirme se o navegador permite a janela de impressao.
