# API NFe (FastAPI) — Processamento de XML e KPIs

API em FastAPI para processar XMLs de Nota Fiscal eletrônica (NFe), consolidar dados e gerar indicadores (KPIs) para relatórios executivos e fiscais. O fluxo cobre leitura dos XMLs, extração de notas e itens, consolidação, cálculo de KPIs por período e persistência em banco PostgreSQL.

> **Resumo rápido**: a API expõe endpoints para processamento em lote de XMLs e consulta/ comparação de KPIs, além de endpoints de autenticação (login/registro). A base de rotas da aplicação fica sob `/api`, e a documentação interativa do FastAPI pode ser acessada em `/docs`.

---

## Sumário

- [Requisitos](#requisitos)
- [Instalação e execução](#instalação-e-execução)
- [Configuração por variáveis de ambiente](#configuração-por-variáveis-de-ambiente)
- [URLs importantes](#urls-importantes)
- [Arquitetura e fluxo de processamento](#arquitetura-e-fluxo-de-processamento)
- [Regras de negócio e validações](#regras-de-negócio-e-validações)
- [Contratos detalhados da API](#contratos-detalhados-da-api)
  - [Saúde](#get-health)
  - [Autenticação](#auth)
  - [Processamento de XML](#post-apinfeprocessar)
  - [Consulta de KPIs](#get-apinfekpis)
  - [Comparativo mensal](#get-apinfekpiscomparativo)
  - [Comparativo automático (últimos períodos)](#get-apinfekpiscomparativoatual)
  - [Consulta de notas (não implementado)](#get-apinfenotas)
- [Formato dos KPIs](#formato-dos-kpis)
- [Persistência e tabelas esperadas](#persistência-e-tabelas-esperadas)
- [Estrutura do projeto](#estrutura-do-projeto)

---

## Requisitos

- Python **3.11+**
- Pip
- PostgreSQL (necessário para persistência e consultas de KPIs)

---

## Instalação e execução

### 1) Instale as dependências

> O arquivo de dependências está em `API/app/requirements.txt`.

```bash
pip install -r API/app/requirements.txt
```

### 2) Configure as variáveis de ambiente

Crie um arquivo `.env` em `API/app/.env` (ou exporte no shell) com as variáveis obrigatórias descritas na seção [Configuração por variáveis de ambiente](#configuração-por-variáveis-de-ambiente).

### 3) Suba a API

Execute o servidor a partir da pasta `API` (para que o pacote `app` seja resolvido corretamente):

```bash
cd API
python -m uvicorn app.main:app --reload
```

- Em produção, remova `--reload`.
- A API ficará disponível em `http://127.0.0.1:8000`.

---

## Configuração por variáveis de ambiente

A aplicação carrega um `.env` localizado em `API/app/.env` usando `python-dotenv`. As variáveis abaixo **precisam** estar definidas (ou em `.env` ou no ambiente do processo):

### Banco de dados (PostgreSQL)

| Variável | Obrigatória | Descrição | Exemplo |
| --- | --- | --- | --- |
| `POSTGRES_HOST` | Sim | Host do PostgreSQL | `localhost` |
| `POSTGRES_PORT` | Sim | Porta do PostgreSQL (inteiro) | `5432` |
| `POSTGRES_DB` | Sim | Nome do banco | `nfe` |
| `POSTGRES_USER` | Sim | Usuário do banco | `postgres` |
| `POSTGRES_PASSWORD` | Sim | Senha do banco | `postgres` |

### CORS (Cross-Origin Resource Sharing)

| Variável | Obrigatória | Padrão | Descrição |
| --- | --- | --- | --- |
| `CORS_ALLOW_ORIGINS` | Não | `*` | Lista separada por vírgula de origens permitidas (ex.: `https://app.exemplo.com, http://localhost:3000`). `*` libera todas as origens. |
| `CORS_ALLOW_CREDENTIALS` | Não | `true` | Controla se o CORS permitirá credenciais. Se `CORS_ALLOW_ORIGINS=*`, a aplicação força `allow_credentials=False` para evitar configuração inválida. |

---

## URLs importantes

- **Base da API:** `http://127.0.0.1:8000`
- **Docs (Swagger UI):** `http://127.0.0.1:8000/docs`
- **OpenAPI JSON:** `http://127.0.0.1:8000/openapi.json`
- **Prefixo das rotas de API:** `/api`
- **OpenAPI JSON:** `http://127.0.0.1:8000/openapi.json`
- **Prefixo das rotas de API:** `/api`

---

## Arquitetura e fluxo de processamento

A API segue um pipeline em camadas:

1. **Leitura de XMLs** (`XmlReader`) — varre uma pasta local, valida arquivos `.xml` e filtra aqueles que têm dados mínimos de emitente.
2. **Extração de notas** (`NFeExtractor`) — parseia os XMLs válidos e extrai cabeçalho, emitente, destinatário, totais e itens.
3. **Consolidação** (`NFeConsolidator`) — aplica deduplicação por chave (número, data, documento do destinatário e total) e prepara agregação de itens.
4. **Persistência básica** — grava notas e itens nas tabelas `nfe_notas` e `nfe_itens`.
5. **Cálculo de KPIs** (`KPICalculator`) — calcula métricas e rankings para cada período (ano/mês).
6. **Persistência por período** — salva o processamento em `nfe_processamentos` e os KPIs em `nfe_kpis`.
7. **Resposta** — retorna o resumo do processamento com KPIs formatados para relatório.

> **Observação importante**: a deduplicação é calculada internamente, mas o retorno atual da consolidação usa a lista original de notas (ver detalhes em [Regras de negócio e validações](#regras-de-negócio-e-validações)).

---

## Regras de negócio e validações

As regras abaixo refletem o comportamento **real** do código:

### Validação de XMLs (leitura)

- A leitura considera **apenas arquivos `.xml`** dentro da pasta informada.
- O XML é descartado se **não existir `<emit>`** ou se o emitente não tiver:
  - `CNPJ` ou
  - `xNome` (nome do emitente).

### Extração de notas

- O XML deve conter `<infNFe>` e `<ide>`.
- `dhEmi` é obrigatório; se ausente, a nota é ignorada.
- Totais devem existir em `<total><ICMSTot>`; se ausente, a nota é ignorada.
- Emitente (`<emit>`) é obrigatório.
- Destinatário (`<dest>`) é opcional:
  - Se ausente, a nota recebe campos vazios e o cliente é tratado como **"CLIENTE NÃO IDENTIFICADO"** no cálculo de KPIs.

### CNPJ do emitente

- Todas as notas extraídas precisam pertencer **ao mesmo CNPJ de emitente**; caso contrário, o processamento falha.
- O nome do emitente (`xNome`) é obrigatório para criação automática da empresa.

### Períodos

- O período é extraído a partir da **data de emissão** (`dhEmi`) de cada nota.
- Se houver apenas um período (ano/mês), `periodo_ano` e `periodo_mes` são preenchidos.
- Se houver múltiplos períodos, `periodo_ano` e `periodo_mes` ficam como `0` e a lista `periodos_encontrados` é retornada.

### Deduplicação e consolidação

- A chave de deduplicação é composta por:
  - número da NF,
  - data de emissão,
  - documento do destinatário,
  - valor total da nota.
- **Observação**: embora o código calcule uma lista deduplicada, o objeto de retorno da consolidação atualmente utiliza a lista original de notas. Isso significa que, na prática, `notas_processadas` e `itens_processados` refletem o conjunto completo, mesmo que haja duplicatas.

---

## Contratos detalhados da API

### `GET /health`

**Finalidade:** Verificar se a aplicação está disponível.

**Resposta (sucesso)**

```json
{
  "status": "ok"
}
```

---

## Auth

A API possui endpoints para **registro** e **login** com senhas armazenadas via PBKDF2 (SHA-256), com salt e 120.000 iterações.

### `POST /api/auth/registrar`

**Finalidade:** Registrar um login para uma empresa já cadastrada.

**Regras específicas**

- O CNPJ informado precisa existir na tabela `empresas`. Caso contrário, o endpoint retorna **400**.
- O e-mail é normalizado para lowercase e deve ser único. Se já existir, retorna **400**.

**Payload (JSON)**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `email` | string | Sim | E-mail do usuário. |
| `senha` | string | Sim | Senha com **mínimo de 8 caracteres**. |
| `cnpj` | string | Sim | CNPJ vinculado à empresa cadastrada. |

**Resposta (sucesso)**

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `status` | string | Sempre retorna `cadastrado`. |
| `login_id` | int | ID do login criado. |
| `empresa_id` | int | ID da empresa vinculada. |
| `cnpj` | string | CNPJ normalizado. |
| `email` | string | E-mail normalizado. |

**Resposta (erro)**

- `HTTP 400` com `detail` descrevendo o problema (ex.: CNPJ não encontrado, e-mail já cadastrado).

---

### `POST /api/auth/entrar`

**Finalidade:** Autenticar um login previamente registrado.

**Payload (JSON)**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `email` | string | Sim | E-mail do usuário. |
| `senha` | string | Sim | Senha de acesso. |

**Resposta (sucesso)**

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `status` | string | Sempre retorna `ok`. |
| `login_id` | int | ID do login. |
| `empresa_id` | int | ID da empresa vinculada. |
| `cnpj` | string | CNPJ normalizado. |
| `email` | string | E-mail normalizado. |

**Resposta (erro)**

- `HTTP 401` com `detail="Credenciais inválidas."` quando email/senha não conferem.

---

## `POST /api/nfe/processar`

**Finalidade:** Processar XMLs de NFe, consolidar dados, persistir resultados e retornar KPIs por período.

**Payload (JSON)**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `empresa_id` | string | Não | Identificador interno da empresa. Se ausente, a empresa é criada/identificada pelo CNPJ do emitente. |
| `origem` | string | Sim | Origem dos XMLs (ex.: `pasta_local`, `s3`, `upload`). |
| `pasta_xml` | string | Sim | Caminho da pasta com os arquivos XML. |
| `periodo` | string | Não | Período esperado no formato `YYYY-MM` (informativo). |

### Resposta (sucesso)

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `status` | string | Sempre retorna `processado` quando o fluxo conclui sem erros. |
| `cnpj_emitente` | string | CNPJ identificado nos XMLs. |
| `periodo_ano` | int | Ano consolidado; `0` se múltiplos períodos. |
| `periodo_mes` | int | Mês consolidado; `0` se múltiplos períodos. |
| `periodos_encontrados` | array | Lista de objetos `{ "ano": int, "mes": int }` detectados nos XMLs. |
| `notas_processadas` | int | Quantidade de notas processadas (pode incluir duplicatas). |
| `itens_processados` | int | Total de itens processados (pode incluir duplicatas). |
| `kpis` | array | KPIs por período com `{ "ano": int, "mes": int, "kpis": object }`. |
| `erros` | array | Lista de erros (vazia no sucesso). |
| `data_processamento` | string | Timestamp ISO-8601 do processamento. |

### KPIs no retorno

- Os KPIs retornam **valores monetários como string formatada em pt-BR** (ex.: `"R$ 1.234,56"`).
- `top_clientes`, `top_produtos` e `top_cidades` trazem até 5 itens, cada um com:
  - `valor_total` formatado em pt-BR,
  - `percentual` numérico (Decimal) com relação ao total de vendas.

### Resposta (erro)

Em caso de falha, a API retorna `status="erro"` e preenche `erros`:

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `codigo` | string | Código interno do erro (`PROCESSAMENTO_NFE_ERRO`). |
| `mensagem` | string | Mensagem legível com a causa. |
| `detalhe` | string | Informação adicional (quando disponível). |

### Exemplo de requisição

```json
POST /api/nfe/processar
Content-Type: application/json

{
  "empresa_id": "123",
  "origem": "pasta_local",
  "pasta_xml": "./meus_xmls",
  "periodo": "2024-05"
}
```

### Exemplo de resposta (sucesso)

```json
{
  "status": "processado",
  "cnpj_emitente": "12345678000199",
  "periodo_ano": 2024,
  "periodo_mes": 5,
  "periodos_encontrados": [{"ano": 2024, "mes": 5}],
  "notas_processadas": 10,
  "itens_processados": 120,
  "kpis": [
    {
      "ano": 2024,
      "mes": 5,
      "kpis": {
        "total_vendas": "R$ 150.000,00",
        "quantidade_notas": 10,
        "ticket_medio": "R$ 15.000,00",
        "maior_nota": "R$ 25.000,00",
        "menor_nota": "R$ 5.000,00",
        "total_icms": "R$ 18.000,00",
        "total_ipi": "R$ 0,00",
        "total_pis": "R$ 0,00",
        "total_cofins": "R$ 0,00",
        "top_clientes": [],
        "top_produtos": [],
        "top_cidades": []
      }
    }
  ],
  "erros": [],
  "data_processamento": "2024-05-10T12:00:00.000Z"
}
```

---

## `GET /api/nfe/kpis`

**Finalidade:** Consultar KPIs já persistidos, com filtros e paginação.

> **Importante:** Este endpoint **exige** um `emitente_cnpj` válido. Caso não seja fornecido, retorna `HTTP 400`.

### Query params

| Param | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `emitente_cnpj` | string | Sim | CNPJ do emitente para filtrar resultados. |
| `periodo_ano` | int | Não | Ano para filtrar resultados. |
| `periodo_mes` | int | Não | Mês para filtrar resultados (1–12). |
| `limite` | int | Não | Máximo de registros retornados (padrão 100). |
| `offset` | int | Não | Deslocamento para paginação (padrão 0). |

### Resposta (sucesso)

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `status` | string | Sempre retorna `ok`. |
| `total` | int | Quantidade de registros retornados. |
| `resultados` | array | Lista de KPIs agrupados por período (`periodo_ano`, `periodo_mes`). |

### Observações

- Os KPIs retornados aqui são **numéricos** (não formatados), pois refletem o payload persistido.
- Se não houver resultados, `resultados` será `[]` e `total` será `0`.

---

## `GET /api/nfe/kpis/comparativo`

**Finalidade:** Comparar KPIs do mês informado com o mês anterior (ou com um período anterior explícito).

### Query params

| Param | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `emitente_cnpj` | string | Não | CNPJ do emitente (opcional). |
| `email` | string | Não | E-mail do login para resolver o CNPJ (opcional). |
| `periodo_ano` | int | Sim | Ano do período atual (2000–2100). |
| `periodo_mes` | int | Sim | Mês do período atual (1–12). |
| `periodo_anterior_ano` | int | Não | Ano do período anterior (2000–2100). |
| `periodo_anterior_mes` | int | Não | Mês do período anterior (1–12). |

### Regras de resolução de CNPJ

- Se `emitente_cnpj` for válido e diferente de `00000000000000`, ele é usado.
- Caso contrário, o serviço tenta obter o CNPJ pelo `email` na tabela `login`.
- Se nenhum for válido, retorna `HTTP 400`.

### Resposta (sucesso)

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `status` | string | Sempre retorna `ok`. |
| `periodo_atual_ano` | int | Ano consultado. |
| `periodo_atual_mes` | int | Mês consultado. |
| `periodo_anterior_ano` | int | Ano do período anterior. |
| `periodo_anterior_mes` | int | Mês do período anterior. |
| `emitente_cnpj` | string | CNPJ resolvido (quando encontrado). |
| `kpis` | object | Estrutura comparativa (valores atuais, anteriores e variação). |

### Regra de variação

- Quando o valor anterior é `0`:
  - `variacao_percentual = 0.00` se o valor atual também for `0`.
  - `variacao_percentual = null` se o valor atual for diferente de `0`.

### Resposta (erro)

- `HTTP 404` quando não há KPIs para o período atual e/ou anterior.

---

## `GET /api/nfe/kpis/comparativo/atual`

**Finalidade:** Comparar KPIs dos **dois períodos mais recentes** encontrados para o emitente.

### Query params

| Param | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `emitente_cnpj` | string | Não | CNPJ do emitente (opcional). |
| `email` | string | Não | E-mail do login para resolver o CNPJ (opcional). |

### Regras de período

- O serviço consulta os **dois períodos mais recentes** em `nfe_kpis` para o emitente.
- Se houver **apenas um período**, o anterior é calculado automaticamente (mês anterior, com ajuste de ano em janeiro).
- Se não houver nenhum período, retorna `HTTP 404`.

---

## `GET /api/nfe/notas`

**Finalidade:** Reservada para consulta detalhada de notas.

- **Status atual:** Não implementada.
- **Resposta:** `HTTP 501` com mensagem orientando o uso de `GET /api/nfe/kpis`.

---

## Formato dos KPIs

Abaixo está o significado dos principais campos calculados:

| KPI | Descrição |
| --- | --- |
| `total_vendas` | Soma de `valor_total_nf` de todas as notas do período. |
| `quantidade_notas` | Número total de notas do período. |
| `ticket_medio` | `total_vendas / quantidade_notas`. |
| `maior_nota` | Maior valor de `valor_total_nf` no período. |
| `menor_nota` | Menor valor de `valor_total_nf` no período. |
| `total_icms` | Soma de `valor_icms`. |
| `total_ipi` | Soma de `valor_ipi`. |
| `total_pis` | Soma de `valor_pis`. |
| `total_cofins` | Soma de `valor_cofins`. |
| `top_clientes` | Top 5 clientes por valor total. Usa `destinatario_nome` (fallback para "CLIENTE NÃO IDENTIFICADO"). |
| `top_produtos` | Top 5 produtos por valor total (soma de itens). |
| `top_cidades` | Top 5 cidades por valor total. |

**Detalhe do percentual**: o campo `percentual` de cada item de `top_clientes`, `top_produtos` e `top_cidades` representa `(valor_total / total_vendas) * 100`.

---

## Persistência e tabelas esperadas

A aplicação assume as seguintes tabelas no PostgreSQL (nomes e colunas usadas no código):

### `public.empresas`

Campos utilizados:
- `id` (PK)
- `cnpj`
- `nome`

### `public.login`

Campos utilizados:
- `id` (PK)
- `empresa_id`
- `cnpj`
- `email`
- `senha`

### `public.nfe_processamentos`

Campos utilizados:
- `id` (PK)
- `empresa_id`
- `cnpj_emitente`
- `periodo_ano`, `periodo_mes`
- `origem`
- `pasta_xml`
- `periodo_solicitado`
- `periodos_encontrados` (JSON)
- `notas_processadas`, `itens_processados`
- `status`
- `data_processamento`

### `public.nfe_kpis`

Campos utilizados:
- `id` (PK)
- `processamento_id` (único, usado no `ON CONFLICT`)
- `emitente_cnpj`
- `periodo_ano`, `periodo_mes`
- `total_vendas`, `quantidade_notas`, `ticket_medio`, `maior_nota`, `menor_nota`
- `total_icms`, `total_ipi`, `total_pis`, `total_cofins`
- `top_clientes`, `top_produtos`, `top_cidades` (JSON)

### `public.nfe_notas`

Campos utilizados:
- `id` (PK)
- `processamento_id` (pode ser `NULL` quando inserido sem vinculação)
- `numero_nf`
- `emitente_cnpj`
- `data_emissao`
- `natureza_operacao`
- `destinatario_documento`, `destinatario_nome`, `destinatario_cidade`, `destinatario_uf`
- `valor_produtos`, `valor_desconto`, `valor_frete`
- `valor_icms`, `valor_ipi`, `valor_pis`, `valor_cofins`
- `valor_total_nf`

### `public.nfe_itens`

Campos utilizados:
- `id` (PK)
- `nota_id` (FK para `nfe_notas.id`)
- `item_numero`
- `produto_codigo`
- `descricao`
- `ncm`
- `cfop`
- `quantidade`
- `valor_unitario`
- `valor_total`

---

## Estrutura do projeto

- `API/app/main.py` – Inicialização da aplicação FastAPI, CORS e healthcheck.
- `API/app/api/` – Definição de rotas (auth e NFe).
- `API/app/services/` – Orquestração de processamento e persistência (PostgreSQL).
- `API/app/domain/` – Leitura de XML, extração, consolidação e cálculo de KPIs.
- `API/app/models/` – Schemas Pydantic para requests e responses.
- `API/app/core/` – Configurações e constantes gerais (quando aplicável).

---

## Observações finais

- Para produção, configure CORS com origens específicas em `CORS_ALLOW_ORIGINS`.
- Em ambientes com múltiplos períodos, a API retorna um KPI por período encontrado.
- A consulta detalhada de notas ainda não está disponível; utilize `GET /api/nfe/kpis` para indicadores.