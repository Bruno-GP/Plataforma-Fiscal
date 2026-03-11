# API NFe (FastAPI) — Processamento de XML e KPIs

API em FastAPI para processar XMLs de Nota Fiscal eletrônica (NFe), consolidar dados e gerar indicadores (KPIs) para relatórios executivos e fiscais. O fluxo cobre leitura dos XMLs, extração de notas e itens, consolidação, cálculo de KPIs por período e persistência em banco PostgreSQL.

> **Resumo rápido**: a API expõe endpoints para processamento em lote de XMLs e consulta/ comparação de KPIs, além de endpoints de autenticação (login/registro). A base de rotas da aplicação fica sob `/api`, e a documentação interativa do FastAPI pode ser acessada em `/docs`.

## Atualizações recentes (itens adicionados e removidos)

### ✅ Adicionado

- **Processamento inicial de SPED Fiscal**:
  - `POST /api/sped/processar` para ler arquivo TXT do SPED, validar conexão do banco SPED e retornar resumo por tipo de registro.

- **Fluxo de importação de XML por upload** na API:
  - `POST /api/nfe/xml/importar` para envio em lote (até 10.000 arquivos por requisição).
  - `GET /api/nfe/xml/pendencias` para consultar quantidade pendente por CNPJ emitente.
  - `POST /api/nfe/xml/processar-importados` para processar XMLs importados e marcar como processados.
- **Cadastro com dados da empresa no Auth**:
  - `POST /api/auth/registrar` agora recebe também `empresa_nome`.
  - Respostas de login/registro incluem `empresa_nome`.
- **Página de Importação de XML no painel** (`/importacao-xml`), integrada aos novos endpoints da API.
- **Cadastro interno de empresa no painel** (`/interno/cadastro-empresa`).

### ❌ Removido / descontinuado

- **Rotas de NFC-e não estão ativas no roteador principal**: atualmente a API expõe os grupos `/api/nfe`, `/api/sped` e `/api/auth`.
- **Páginas de `Clientes` e `Configurações` foram retiradas da navegação ativa** no front-end (rotas comentadas em `App.tsx`).

### 🔎 Observações de compatibilidade

- O painel continua aceitando `VITE_API_URL` com ou sem sufixo `/api`.
- O endpoint `GET /api/nfe/notas` permanece mapeado, porém retorna **501 Not Implemented**.

---

## Sumário

- [Requisitos](#requisitos)
- [Guia rápido da plataforma (API + Painel)](#guia-rápido-da-plataforma-api--painel)
- [Instalação e execução](#instalação-e-execução)
- [Configuração por variáveis de ambiente](#configuração-por-variáveis-de-ambiente)
- [Preparação do banco de dados](#preparação-do-banco-de-dados)
- [URLs importantes](#urls-importantes)
- [Documentação do Painel (Front-end)](#documentação-do-painel-front-end)
- [Arquitetura e fluxo de processamento](#arquitetura-e-fluxo-de-processamento)
- [Regras de negócio e validações](#regras-de-negócio-e-validações)
- [Fluxo completo (XML → KPIs → Painel)](#fluxo-completo-xml--kpis--painel)
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
- [Observabilidade e logs](#observabilidade-e-logs)
- [FAQ e solução de problemas](#faq-e-solução-de-problemas)

---

## Requisitos

- Python **3.11+**
- Pip
- PostgreSQL (necessário para persistência e consultas de KPIs)

---

## Guia rápido da plataforma (API + Painel)

Se você quer subir todo o ambiente local com o mínimo de passos:

1. **Prepare o banco PostgreSQL** e aplique os scripts de schema em `API/app/file/sql/`.
2. **Suba a API**:

  ```bash
  pip install -r API/app/requirements.txt
  cd API
  python -m uvicorn app.main:app --reload
  ```

3. **Suba o painel em outro terminal**:

  ```bash
  cd Painel
  yarn install
  yarn dev
  ```

4. **Configure a conexão do painel com a API** em `Painel/.env`:

  ```bash
  VITE_API_URL=http://localhost:8000
  ```

5. **Acesse os serviços**:
  - API: `http://localhost:8000`
  - Swagger: `http://localhost:8000/docs`
  - Painel: `http://localhost:5173`

> O painel normaliza `VITE_API_URL` e aceita o valor com ou sem o sufixo `/api`.

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
| `POSTGRES_DB` | Sim* | Banco padrão/legado (fallback) | `nfe` |
| `POSTGRES_DB_NFE` | Não | Nome do banco dedicado da NFe | `nfe` |
| `POSTGRES_DB_SPED` | Não | Nome do banco dedicado do SPED Fiscal (compatibilidade) | `sped_fiscal` |
| `POSTGRES_SPED_HOST` | Não | Host dedicado do banco SPED (fallback para `POSTGRES_HOST`) | `localhost` |
| `POSTGRES_SPED_PORT` | Não | Porta dedicada do banco SPED (fallback para `POSTGRES_PORT`) | `5432` |
| `POSTGRES_SPED_DB` | Não | Banco dedicado do SPED (prioritário) | `sped_fiscal` |
| `POSTGRES_SPED_USER` | Não | Usuário dedicado do banco SPED (fallback para `POSTGRES_USER`) | `postgres` |
| `POSTGRES_SPED_PASSWORD` | Não | Senha dedicada do banco SPED (fallback para `POSTGRES_PASSWORD`) | `postgres` |
| `POSTGRES_USER` | Sim | Usuário do banco | `postgres` |
| `POSTGRES_PASSWORD` | Sim | Senha do banco | `postgres` |

> \* A aplicação mantém compatibilidade com `POSTGRES_DB`. Se `POSTGRES_DB_NFE`/`POSTGRES_DB_SPED` forem informados, cada contexto passa a usar seu banco dedicado.

### CORS (Cross-Origin Resource Sharing)

| Variável | Obrigatória | Padrão | Descrição |
| --- | --- | --- | --- |
| `CORS_ALLOW_ORIGINS` | Não | `*` | Lista separada por vírgula de origens permitidas (ex.: `https://app.exemplo.com, http://localhost:3000`). `*` libera todas as origens. |
| `CORS_ALLOW_CREDENTIALS` | Não | `true` | Controla se o CORS permitirá credenciais. Se `CORS_ALLOW_ORIGINS=*`, a aplicação força `allow_credentials=False` para evitar configuração inválida. |

---

## Preparação do banco de dados

O projeto **não possui migrações** automatizadas. Portanto, você deve criar o schema no PostgreSQL antes de iniciar a API. Abaixo está um **exemplo de script SQL** compatível com as tabelas e colunas utilizadas pelo código. Ajuste nomes/tipos conforme sua política interna.

Para ambientes com bancos separados por domínio, utilize primeiro `API/app/file/sql/create_databases.sql` e depois aplique os schemas de cada módulo (`NFe` e `SPED`).

> **Dica:** rode o SQL no banco definido nas variáveis `POSTGRES_*`.

```sql
create table if not exists public.empresas (
  id serial primary key,
  cnpj varchar(20) not null unique,
  nome varchar(255) not null
);

create table if not exists public.login (
  id serial primary key,
  empresa_id int not null references public.empresas(id),
  cnpj varchar(20) not null,
  email varchar(255) not null unique,
  senha varchar(255) not null
);

create table if not exists public.nfe_processamentos (
  id serial primary key,
  empresa_id int,
  cnpj_emitente varchar(20) not null,
  periodo_ano int not null,
  periodo_mes int not null,
  origem varchar(50),
  pasta_xml text,
  periodo_solicitado varchar(10),
  periodos_encontrados jsonb,
  notas_processadas int,
  itens_processados int,
  status varchar(50),
  data_processamento timestamp
);

create table if not exists public.nfe_kpis (
  id serial primary key,
  processamento_id int not null unique references public.nfe_processamentos(id),
  emitente_cnpj varchar(20) not null,
  periodo_ano int not null,
  periodo_mes int not null,
  total_vendas numeric,
  quantidade_notas int,
  ticket_medio numeric,
  maior_nota numeric,
  menor_nota numeric,
  total_icms numeric,
  total_ipi numeric,
  total_pis numeric,
  total_cofins numeric,
  top_clientes jsonb,
  top_produtos jsonb,
  top_cidades jsonb
);

create table if not exists public.nfe_notas (
  id serial primary key,
  processamento_id int references public.nfe_processamentos(id),
  numero_nf varchar(30),
  emitente_cnpj varchar(20),
  data_emissao timestamp,
  natureza_operacao varchar(255),
  destinatario_documento varchar(30),
  destinatario_nome varchar(255),
  destinatario_cidade varchar(100),
  destinatario_uf varchar(10),
  valor_produtos numeric,
  valor_desconto numeric,
  valor_frete numeric,
  valor_icms numeric,
  valor_ipi numeric,
  valor_pis numeric,
  valor_cofins numeric,
  valor_total_nf numeric
);

create table if not exists public.nfe_itens (
  id serial primary key,
  nota_id int not null references public.nfe_notas(id),
  item_numero int,
  produto_codigo varchar(60),
  descricao varchar(255),
  ncm varchar(20),
  cfop varchar(10),
  quantidade numeric,
  valor_unitario numeric,
  valor_total numeric
);
```

### Validando a conexão com o banco

Antes de rodar a API, valide a conexão para evitar erros de runtime:

```bash
psql "host=$POSTGRES_HOST port=$POSTGRES_PORT dbname=$POSTGRES_DB user=$POSTGRES_USER password=$POSTGRES_PASSWORD"
```

---


## URLs importantes

- **Base da API:** `http://127.0.0.1:8000`
- **Docs (Swagger UI):** `http://127.0.0.1:8000/docs`

---

## Documentação do Painel (Front-end)

### Visão geral

Front-end em React + Vite para visualizar KPIs de NFe, com autenticação, rankings e comparativos de períodos. Ele consome a API descrita neste README e normaliza automaticamente a URL base quando necessário.

Principais objetivos do painel:

- Autenticação de usuários (login/registro) vinculados a empresas.
- Visualização de KPIs e comparativos por período.
- Rankings de clientes, produtos e cidades.
- Navegação por páginas de dashboard, faturamento e clientes.

### Requisitos

- Node.js **18+**
- Yarn (recomendado) ou npm

### Instalação

Na pasta `Painel`:

```bash
yarn install
```

> Se preferir npm: `npm install`.

### Configuração de ambiente

Crie um arquivo `.env` em `Painel/.env` com a URL base da API:

```bash
VITE_API_URL=http://localhost:8000
```

Observações:

- Se a URL não terminar com `/api`, o painel adiciona automaticamente.
- Exemplo alternativo já com prefixo: `VITE_API_URL=http://localhost:8000/api`.
- Ajuste a variável de CORS na API para permitir a origem do painel (ex.: `http://localhost:5173`).

### Checklist rápido de integração

1. **API rodando** em `http://localhost:8000` (ou outro host/porta).
2. **CORS configurado** no `.env` da API com o domínio do painel (ex.: `http://localhost:5173`).
3. **Painel com `VITE_API_URL`** apontando para a API.
4. **Banco populado** com KPIs para o CNPJ/usuário do painel (necessário para as páginas de indicadores).

### Executando em desenvolvimento

```bash
yarn dev
```

O painel ficará disponível em `http://localhost:5173`.

### Build e preview

```bash
yarn build
yarn preview
```

### Scripts úteis

| Script | Descrição |
| --- | --- |
| `yarn dev` | Inicia o servidor de desenvolvimento. |
| `yarn build` | Gera build de produção. |
| `yarn preview` | Preview do build. |
| `yarn lint` | Executa ESLint. |

### Endpoints da API utilizados

O painel consome os seguintes endpoints (prefixo `/api`):

- `POST /auth/entrar` — login.
- `POST /auth/registrar` — cadastro de acesso.
- `GET /nfe/kpis` — consulta de KPIs por período.
- `GET /nfe/kpis/comparativo/atual` — comparativo dos dois períodos mais recentes.

#### Detalhes de uso por funcionalidade

- **Login/Registro:** as telas de autenticação usam `POST /auth/entrar` e `POST /auth/registrar`.
  - Em caso de erro, o painel exibe mensagens como "Credenciais inválidas" ou "E-mail já cadastrado".
- **Dashboard:** utiliza `GET /nfe/kpis/comparativo/atual` para exibir a comparação dos dois períodos mais recentes.
  - O painel resolve o CNPJ a partir do login e, quando necessário, usa o `email` como fallback.
- **Faturamento:** utiliza `GET /nfe/kpis` para obter o período atual e montar cards e gráficos.
  - Requer `emitente_cnpj` válido.
- **Clientes/Rankings:** usa `GET /nfe/kpis` para exibir rankings a partir de `top_clientes`.

### Estrutura do painel

Organização principal (pasta `Painel/src`):

- `pages/` — páginas do app (ex.: dashboard, faturamento, clientes).
- `contexts/` — contexto de autenticação (login, registro e dados do usuário).
- `services/` — serviços de integração com a API (ex.: `nfe.ts`).
- `components/` — componentes reutilizáveis (cartões, gráficos, tabelas, etc).
- `routes/` — definição de rotas e navegação.
- `styles/` ou configurações de Tailwind — estilos globais e classes utilitárias.

### Comportamentos e formatação de dados

- **Normalização de valores monetários:** o painel aceita KPIs numéricos ou formatados (`"R$ 1.234,56"`).
- **Conversão de strings monetárias:** há conversão de strings para número quando necessário (por exemplo, para gráficos).
- **Comparativo:** quando `variacao_percentual` é `null`, o painel representa crescimento a partir de base zero.
- **Rankings:** itens podem não conter todas as chaves (`cliente`, `produto`, `cidade`); o painel trata campos ausentes.

### Erros comuns e solução de problemas

- **Erro de CORS:** confira `CORS_ALLOW_ORIGINS` na API.
- **Sem dados:** garanta que há KPIs persistidos antes de abrir o dashboard.
- **CNPJ inválido:** o painel ignora CNPJs vazios ou com dígitos zerados.
- **Erro ao buscar KPIs:** confirme se o endpoint `/api/nfe/kpis` está acessível e se o `emitente_cnpj` é válido.
  - Em ambientes de teste, execute o processamento de XML antes para gerar KPIs.

### Build de produção

1. Gere o build:

   ```bash
   yarn build
   ```

2. Sirva o build:

   ```bash
   yarn preview
   ```

3. Configure a variável `VITE_API_URL` no ambiente de deploy (ex.: `.env.production`).

### Observações de segurança

- Nunca commite o arquivo `.env` com credenciais reais.
- Em ambientes públicos, configure `CORS_ALLOW_ORIGINS` com a origem exata do painel.

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

## Fluxo completo (XML → KPIs → Painel)

Esta seção resume o caminho **de ponta a ponta**, do XML até o dashboard:

1. **Preparar os XMLs**  
   Coloque os arquivos `.xml` em uma pasta local no servidor (ex.: `./xmls`). Somente arquivos `.xml` serão considerados.
2. **Processar via API**  
   Envie `POST /api/nfe/processar` indicando `pasta_xml` e `origem`. A API irá:
   - Ler os XMLs, extrair notas/itens.
   - Consolidar dados e persistir em `nfe_notas` e `nfe_itens`.
   - Calcular KPIs e salvar em `nfe_kpis`.
3. **Consumir KPIs**  
   Use `GET /api/nfe/kpis` (ou endpoints de comparativo) para consultar os indicadores.
4. **Exibir no painel**  
   Configure `VITE_API_URL` no front-end e acesse o dashboard.

### Exemplo rápido com `curl`

```bash
curl -X POST http://localhost:8000/api/nfe/processar \
  -H "Content-Type: application/json" \
  -d '{
    "origem": "pasta_local",
    "pasta_xml": "./xmls",
    "periodo": "2024-05"
  }'
```

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

## Observabilidade e logs

- A aplicação utiliza o logger padrão do Python (ver `API/app/core/logger.py`).
- Em produção, considere:
  - **Nível de log** configurável por variável de ambiente.
  - **Log estruturado** (JSON) para ferramentas como ELK, Datadog ou Grafana Loki.
  - **Rotação de logs** via `logrotate` ou driver do runtime de containers.

---

## FAQ e solução de problemas

### 1) A API sobe, mas não conecta no banco

Verifique:

- Se as variáveis `POSTGRES_*` estão corretas.
- Se o PostgreSQL está aceitando conexões externas.
- Se o usuário tem permissão nas tabelas.

### 2) Erro de CORS no painel

Garanta que `CORS_ALLOW_ORIGINS` inclui o domínio do painel. Exemplo:

```
CORS_ALLOW_ORIGINS=http://localhost:5173
```

### 3) Nenhum KPI aparece no dashboard

- Confirme se o `POST /api/nfe/processar` foi executado com sucesso.
- Verifique se `nfe_kpis` contém registros para o CNPJ esperado.
- No painel, valide se o usuário autenticado tem vínculo com o CNPJ correto.

### 4) XMLs ignorados

Motivos comuns:

- Falta de `<emit>` ou `xNome`.
- `dhEmi` ausente.
- Falta de `<total><ICMSTot>`.

---

## Observações finais

- Para produção, configure CORS com origens específicas em `CORS_ALLOW_ORIGINS`.
- Em ambientes com múltiplos períodos, a API retorna um KPI por período encontrado.
- A consulta detalhada de notas ainda não está disponível; utilize `GET /api/nfe/kpis` para indicadores.

### Exemplo de `.env`

Use o arquivo `API/app/.env.example` como base para o seu `API/app/.env`.

```bash
cp API/app/.env.example API/app/.env
```