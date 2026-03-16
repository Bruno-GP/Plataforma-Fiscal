# Painel Plataforma Fiscal (React + Vite)

Documentação oficial do front-end da plataforma, responsável por autenticação, operação de importações fiscais e visualização de análises/KPIs.

URL local padrão: `http://localhost:5173`

---

## Sumário

- [1. Visão geral](#1-visão-geral)
- [2. Stack e requisitos](#2-stack-e-requisitos)
- [3. Instalação e execução](#3-instalação-e-execução)
- [4. Configuração de ambiente](#4-configuração-de-ambiente)
- [5. Rotas da aplicação](#5-rotas-da-aplicação)
- [6. Funcionalidades por página](#6-funcionalidades-por-página)
- [7. Integração com a API](#7-integração-com-a-api)
- [8. Build, preview e testes](#8-build-preview-e-testes)
- [9. Troubleshooting](#9-troubleshooting)

---

## 1. Visão geral

O Painel é a interface operacional da plataforma e cobre:

- Login e cadastro interno de empresa.
- Importação fiscal por perfil de empresa (**XML** ou **SPED**).
- Visualização de análises (vendas, compras, clientes).
- Consulta de relatórios com IA.
- Navegação protegida e contextual por sessão.

---

## 2. Stack e requisitos

- **React + TypeScript**
- **Vite**
- **React Router**
- **TanStack Query**
- **Tailwind + componentes UI**
- **Node.js 18+**
- **Yarn** (recomendado)

---

## 3. Instalação e execução

No diretório `Painel`:

```bash
yarn install
yarn dev
```

Aplicação em: `http://localhost:5173`

---

## 4. Configuração de ambiente

Crie `Painel/.env`:

```env
VITE_API_URL=http://localhost:8000
```

### Observação importante

O front-end normaliza automaticamente a URL da API:

- Se você informar `http://localhost:8000`, ele usa `http://localhost:8000/api`.
- Se você informar `http://localhost:8000/api`, ele mantém como está.

---

## 5. Rotas da aplicação

### 5.1 Rotas ativas

- `/login`
- `/interno/cadastro-empresa`
- `/analise-vendas`
- `/analise-compras`
- `/analise-clientes`
- `/relatorios-ia`
- `/importacao-xml`
- `/importacao-sped`

### 5.2 Regras de redirecionamento

- `/` redireciona para `/analise-vendas`.
- `/clientes` redireciona para `/analise-clientes`.
- Empresa com `tem_sped=true` não acessa fluxo XML (redireciona para SPED).
- Empresa com `tem_sped=false` não acessa fluxo SPED (redireciona para XML).

### 5.3 Rotas atualmente fora da navegação

- Configurações (`/configuracoes`) está comentada no roteador.
- Atualizações (`/atualizacoes`) está comentada no roteador.

---

## 6. Funcionalidades por página

## Login (`/login`)

- Autenticação via API.
- Persistência de contexto de sessão do usuário.

## Cadastro interno (`/interno/cadastro-empresa`)

- Cadastro de empresa + usuário.
- Define perfil de operação (`tem_sped`).

## Importação XML (`/importacao-xml`)

- Upload em lote de XML.
- Consulta de pendências.
- Processamento dos importados.

## Importação SPED (`/importacao-sped`)

- Upload em lote de TXT SPED.
- Consulta de pendências.
- Processamento dos importados.

## Análise de vendas (`/analise-vendas`)

- Indicadores e rankings por período.
- Integração com dados NFe ou SPED conforme perfil.

## Análise de compras (`/analise-compras`)

- Total comprado, principais fornecedores e produtos.
- Suporte a geração opcional de relatório IA.

## Análise de clientes (`/analise-clientes`)

- Indicadores e concentrações por cliente.

## Relatórios IA (`/relatorios-ia`)

- Interface para leitura de análises com texto gerado por IA (quando disponível na API).

---

## 7. Integração com a API

Principais endpoints consumidos pelo Painel:

### Autenticação

- `POST /api/auth/entrar`
- `POST /api/auth/registrar`

### NFe (XML)

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
- `POST /api/sped/importar`
- `GET /api/sped/pendencias`
- `POST /api/sped/processar-importados`

---

## 8. Build, preview e testes

### Build de produção

```bash
yarn build
```

### Preview da build

```bash
yarn preview
```

### Testes

```bash
yarn test
```

> Caso a suíte seja expandida, manter testes de serviços HTTP e rotas protegidas como prioridade.

---

## 9. Troubleshooting

- **Tela sem dados:** validar `VITE_API_URL` e API ativa.
- **Erro de CORS:** ajustar `CORS_ALLOW_ORIGINS` na API.
- **Importação negada:** conferir se perfil da empresa bate com o tipo de importação (XML x SPED).
- **Falha em relatórios IA:** validar disponibilidade de `OPENAI_API_KEY` no backend.
- **Erro de autenticação:** revisar credenciais e resposta da rota `/api/auth/entrar`.