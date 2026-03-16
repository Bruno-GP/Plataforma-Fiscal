# API Plataforma Fiscal (FastAPI)

Documentação oficial da API responsável por autenticação, importação fiscal (XML NFe e SPED), processamento de dados e consultas analíticas.

Base URL local (desenvolvimento): `http://localhost:8000`  
Prefixo de rotas da API: `/api`  
Documentação interativa (Swagger): `/docs`

---

## Sumário

- [1. Visão geral](#1-visão-geral)
- [2. Requisitos](#2-requisitos)
- [3. Instalação e execução](#3-instalação-e-execução)
- [4. Configuração de ambiente](#4-configuração-de-ambiente)
- [5. Banco de dados](#5-banco-de-dados)
- [6. Organização de rotas](#6-organização-de-rotas)
- [7. Contratos da API](#7-contratos-da-api)
  - [7.1 Sistema](#71-sistema)
  - [7.2 Autenticação](#72-autenticação)
  - [7.3 NFe (XML)](#73-nfe-xml)
  - [7.4 SPED Fiscal](#74-sped-fiscal)
  - [7.5 Geo](#75-geo)
- [8. Regras de negócio importantes](#8-regras-de-negócio-importantes)
- [9. Erros comuns e respostas HTTP](#9-erros-comuns-e-respostas-http)
- [10. Boas práticas de operação](#10-boas-práticas-de-operação)

---

## 1. Visão geral

A API centraliza os principais fluxos fiscais da plataforma:

- Cadastro e login de usuários/empresa.
- Importação e processamento de XML de NFe.
- Importação e processamento de arquivos SPED Fiscal.
- Consulta de KPIs e análises (compras, vendas, clientes).
- Endpoints auxiliares geográficos para mapa de municípios.
- Geração opcional de relatório textual com IA (`gerar_relatorio_ia=true`).

---

## 2. Requisitos

- Python **3.11+**
- Pip
- PostgreSQL
- Variáveis de ambiente configuradas (seção 4)

---

## 3. Instalação e execução

### 3.1 Instalar dependências

Na raiz do repositório:

```bash
pip install -r API/app/requirements.txt
```

### 3.2 Executar servidor

```bash
cd API
python -m uvicorn app.main:app --reload
```

- API: `http://127.0.0.1:8000`
- Health: `http://127.0.0.1:8000/health`
- Swagger: `http://127.0.0.1:8000/docs`

---

## 4. Configuração de ambiente

A API carrega variáveis de ambiente de `API/app/.env`.

### 4.1 Banco PostgreSQL

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=nfe
POSTGRES_DB_NFE=nfe
POSTGRES_DB_SPED=sped_fiscal
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

### 4.2 Banco SPED dedicado (opcional)

```env
POSTGRES_SPED_HOST=localhost
POSTGRES_SPED_PORT=5432
POSTGRES_SPED_DB=sped_fiscal
POSTGRES_SPED_USER=postgres
POSTGRES_SPED_PASSWORD=postgres
```

### 4.3 CORS

```env
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CORS_ALLOW_CREDENTIALS=true
# opcional
CORS_ALLOW_ORIGIN_REGEX=
```

### 4.4 OpenAI (opcional)

```env
OPENAI_API_KEY=<sua-chave>
OPENAI_REPORT_MODEL=gpt-4o-mini
```

> `OPENAI_API_KEY` só é necessária para chamadas com `gerar_relatorio_ia=true`.

---

## 5. Banco de dados

- O projeto usa PostgreSQL para autenticação, staging de importação e KPIs.
- Não há migrações automáticas no repositório.
- Scripts SQL disponíveis em `API/app/file/sql/`.
- Para ambientes com separação de domínio, criar bancos NFe e SPED e aplicar schemas correspondentes.

---

## 6. Organização de rotas

- Prefixo global: `/api`
- Módulos:
  - `/api/auth`
  - `/api/nfe`
  - `/api/sped`
  - `/api/geo`
- Endpoint fora do prefixo: `GET /health`

---

## 7. Contratos da API

## 7.1 Sistema

### `GET /health`

Verifica disponibilidade da aplicação.

**Resposta 200 (exemplo):**

```json
{ "status": "ok" }
```

---

## 7.2 Autenticação

## `POST /api/auth/registrar`

Registra login + empresa.

**Body (JSON):**

```json
{
  "empresa_nome": "Empresa Exemplo LTDA",
  "email": "contato@empresa.com",
  "senha": "senha-forte",
  "cnpj": "12345678000190",
  "tem_sped": false
}
```

**Resposta 201:**

```json
{
  "status": "cadastrado",
  "login_id": 1,
  "empresa_id": 1,
  "cnpj": "12345678000190",
  "email": "contato@empresa.com",
  "empresa_nome": "Empresa Exemplo LTDA",
  "tem_sped": false
}
```

---

## `POST /api/auth/entrar`

Autentica usuário.

**Body (JSON):**

```json
{
  "email": "contato@empresa.com",
  "senha": "senha-forte"
}
```

**Resposta 200:**

```json
{
  "status": "ok",
  "login_id": 1,
  "empresa_id": 1,
  "cnpj": "12345678000190",
  "email": "contato@empresa.com",
  "empresa_nome": "Empresa Exemplo LTDA",
  "tem_sped": false
}
```

---

## 7.3 NFe (XML)

## `POST /api/nfe/processar`

Fluxo legado/lote para processar XMLs de uma origem já disponível (sem upload).

- Usa o contrato `ProcessarNFeRequest`.
- Retorna `ProcessarNFeResponse`.

> Recomenda-se usar o fluxo de upload + processamento importado para operação no Painel.

---

## `POST /api/nfe/xml/importar`

Importa XMLs para staging (sem calcular KPI imediatamente).

**Tipo:** `multipart/form-data`  
**Query obrigatória:** `cnpj_empresa_origem`  
**Campo de arquivo:** `arquivos`

Regras:

- Máximo de **10.000 arquivos** por requisição.
- Apenas extensão `.xml` é aceita.

---

## `GET /api/nfe/xml/pendencias`

Consulta quantidade pendente por CNPJ.

**Query:** `cnpj_emitente`

---

## `POST /api/nfe/xml/processar-importados`

Processa XMLs pendentes do staging e marca como processados.

**Query:** `cnpj_emitente`

- Retorna 404 quando não existem pendências.

---

## `GET /api/nfe/kpis`

Consulta KPIs consolidados.

**Query principal:**

- `emitente_cnpj` (obrigatório efetivo)
- `periodo_ano` (opcional)
- `periodo_mes` (opcional)
- `limite` e `offset` (paginação)

---

## `GET /api/nfe/kpis/comparativo`

Compara KPI entre mês atual e anterior (manual).

- Parâmetros obrigatórios: `periodo_ano`, `periodo_mes`
- `periodo_anterior_ano/mes` opcionais (auto-cálculo se não informados)
- `emitente_cnpj` ou `email` para resolução de empresa

---

## `GET /api/nfe/kpis/comparativo/atual`

Compara automaticamente os dois períodos mais recentes disponíveis.

- Entrada: `emitente_cnpj` ou `email`

---

## `GET /api/nfe/analise/compras`
## `GET /api/nfe/analise/vendas`
## `GET /api/nfe/analise/clientes`

Análises avançadas com rankings e totais.

Parâmetros comuns:

- `emitente_cnpj` ou `email`
- `periodo_ano` / `periodo_mes` (opcional)
- `limite` (1..20)
- `gerar_relatorio_ia` (opcional)

---

## `GET /api/nfe/notas`

Atualmente retorna **501 Not Implemented**.

---

## 7.4 SPED Fiscal

> Endpoints SPED só funcionam para empresas configuradas com `tem_sped=true`.

## `POST /api/sped/processar`

Processamento direto de arquivo SPED (fluxo de serviço).

---

## `POST /api/sped/importar`

Importa arquivos TXT do SPED para staging.

**Tipo:** `multipart/form-data`  
**Query obrigatória:** `cnpj_empresa_origem`  
**Campo de arquivo:** `arquivos`

Regras:

- Máximo de **500 arquivos** por requisição.
- Apenas extensão `.txt`.

---

## `GET /api/sped/pendencias`

Retorna total de arquivos SPED pendentes por CNPJ.

---

## `POST /api/sped/processar-importados`

Processa staging SPED pendente e marca como processado.

---

## `GET /api/sped/kpis`

Consulta KPIs consolidados do SPED.

---

## `GET /api/sped/clientes`

Lista clientes (com filtros de período/paginação).

---

## `GET /api/sped/analise/compras`
## `GET /api/sped/analise/vendas`

Análises de compras e vendas no domínio SPED.

Parâmetros comuns:

- `emitente_cnpj` (obrigatório)
- `periodo_ano`, `periodo_mes` (opcional)
- `limite` (1..20)
- `gerar_relatorio_ia` (opcional)

---

## 7.5 Geo

## `GET /api/geo/municipios`

Entrega arquivo local de municípios em formato GeoJSON (quando disponível).

## `GET /api/geo/municipios/{uf}`

Retorna municípios por UF:

- Prioriza base local `LL-municipios.json`.
- Se necessário, consulta fallback no IBGE.

---

## 8. Regras de negócio importantes

- Empresa com `tem_sped=true` **não** deve usar rotas de XML NFe.
- Empresa com `tem_sped=false` **não** deve usar rotas SPED.
- CNPJ é validado com tamanho mínimo/máximo (14..20) em vários endpoints.
- Limites de upload existem para segurança de processamento (NFe 10.000, SPED 500).
- Rotas de análise com IA retornam 503 se `OPENAI_API_KEY` não estiver configurada.

---

## 9. Erros comuns e respostas HTTP

- **400 Bad Request**: entrada inválida (CNPJ, arquivo, parâmetros).
- **401 Unauthorized**: falha de login.
- **404 Not Found**: sem dados/pêndencias para o filtro.
- **501 Not Implemented**: endpoint previsto ainda sem implementação (`/api/nfe/notas`).
- **502 Bad Gateway**: erro de integração externa (ex.: geração IA).
- **503 Service Unavailable**: indisponibilidade de banco/auth/OpenAI.

---

## 10. Boas práticas de operação

1. Sempre validar perfil da empresa no login (`tem_sped`) antes do fluxo de importação.
2. Trabalhar por lote com lotes menores em produção para monitorar throughput.
3. Usar `GET /health` em monitoramento.
4. Auditar pendências antes de processamento (`/pendencias`).
5. Consultar `/docs` para schemas atualizados automaticamente.