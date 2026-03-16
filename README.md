# Plataforma Fiscal — Documentação Principal

Este repositório contém **duas aplicações principais** que trabalham em conjunto:

- **API (FastAPI)** para autenticação, importação/processamento fiscal (XML NFe e SPED), consultas analíticas e geração opcional de relatórios com IA.
- **Painel (React + Vite)** para operação do dia a dia (login, importação, análises e relatórios), consumindo os endpoints da API.

> A documentação foi separada por contexto para facilitar manutenção e onboarding:
>
> - 📘 **Documentação da API:** [`API/README.md`](API/README.md)
> - 📙 **Documentação do Painel:** [`Painel/README.md`](Painel/README.md)

---

## Sumário rápido

- [Visão geral da arquitetura](#visão-geral-da-arquitetura)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Quick start (API + Painel)](#quick-start-api--painel)
- [Fluxo operacional recomendado](#fluxo-operacional-recomendado)
- [Funcionalidades por módulo](#funcionalidades-por-módulo)
- [Ambiente e requisitos gerais](#ambiente-e-requisitos-gerais)
- [Guia de troubleshooting](#guia-de-troubleshooting)

---

## Visão geral da arquitetura

A plataforma funciona em camadas:

1. **Usuário acessa o Painel** e realiza login/cadastro.
2. O **Painel consome a API** via `VITE_API_URL`.
3. A **API valida perfil da empresa** (fluxo XML x fluxo SPED).
4. A API **importa/ processa documentos fiscais** e persiste no PostgreSQL.
5. O Painel consome **KPIs e análises** para exibir dashboards.
6. Opcionalmente, algumas análises podem ser enriquecidas com **relatório narrativo via OpenAI**.

---

## Estrutura do repositório

```text
.
├── API/
│   └── README.md        # Documentação completa da API
├── Painel/
│   └── README.md        # Documentação completa do front-end
└── README.md            # Este guia principal (orquestração da plataforma)

```

---

## Quick start (API + Painel)

### 1) Subir a API

```bash
pip install -r API/app/requirements.txt
cd API
python -m uvicorn app.main:app --reload
```

API local: `http://localhost:8000`
Swagger: `http://localhost:8000/docs`

### 2) Subir o Painel

Em outro terminal:

```bash
cd Painel
yarn install
yarn dev
```

Painel local: `http://localhost:5173`

### 3) Configurar integração

No arquivo `Painel/.env`:

```env
VITE_API_URL=http://localhost:8000
```

> O front-end aceita `VITE_API_URL` com ou sem `/api` no final.

---

## Fluxo operacional recomendado

1. **Cadastro/login** de empresa e usuário.
2. Definir se empresa trabalha com **XML NFe** ou **SPED Fiscal**.
3. Usar a tela correta de importação no Painel:
   - XML: `/importacao-xml`
   - SPED: `/importacao-sped`
4. Consultar pendências e processar importados.
5. Acompanhar dashboards:
   - Análise de vendas
   - Análise de compras
   - Análise de clientes
   - Relatórios IA

---

### API (backend)

Abaixo está o significado dos principais campos calculados:

- Health check e CORS configurável por ambiente.
- Autenticação (registro e login).
- Importação e processamento de **XML NFe**.
- Importação e processamento de **SPED Fiscal**.
- Consultas de KPIs e análises analíticas.
- Endpoints de GeoJSON para municípios.
- Integração opcional com OpenAI para relatórios narrativos.

👉 Detalhes completos em [`API/README.md`](API/README.md).

### Painel (frontend)

- Autenticação e contexto de sessão.
- Navegação protegida por perfil da empresa.
- Fluxos de importação fiscal (XML/SPED).
- Dashboards analíticos com filtros de período.
- Módulo de relatórios IA.
- Integração centralizada com serviços HTTP.

👉 Detalhes completos em [`Painel/README.md`](Painel/README.md).

---

## Ambiente e requisitos gerais

- **Python 3.11+** (API)
- **Node.js 18+** (Painel)
- **Yarn** (recomendado para o front)
- **PostgreSQL** (persistência dos módulos fiscais e autenticação)

---

## Guia de troubleshooting

- **Erro de CORS:** validar `CORS_ALLOW_ORIGINS` na API e URL do painel.
- **Painel sem dados:** conferir `VITE_API_URL`, API ativa e credenciais válidas.
- **Importação rejeitada:** confirmar tipo de empresa (XML x SPED) e formato de arquivo.
- **Relatório IA indisponível:** definir `OPENAI_API_KEY` no ambiente da API.

Para troubleshooting específico, consulte:

- API: [`API/README.md`](API/README.md)
- Painel: [`Painel/README.md`](Painel/README.md)