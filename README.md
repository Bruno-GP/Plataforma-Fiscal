API em FastAPI para processar XMLs de Nota Fiscal eletrônica (NFe) e gerar indicadores consolidados para relatórios executivos e fiscais.

## Requisitos

- Python 3.11+
- Pip

## Configuração rápida
2. Instale as dependências:
  ```bash
  pip install -r API/app/requirements.txt
  ```

## Como executar

- Ambiente local (hot-reload):
  ```bash
  python -m uvicorn app.main:app --reload
  ```
- Exposição externa (exemplo com ngrok):
  ```bash
  ngrok http 8000
  ```

Após iniciar, a documentação interativa estará em `http://localhost:8000/docs` e o JSON schema em `http://localhost:8000/openapi.json`.

## Endpoints principais

- `GET /health` – Verificação de disponibilidade.
- `POST /api/nfe/processar` – Processa um conjunto de XMLs e retorna consolidação e KPIs.
- `GET /api/nfe/kpis` – Consulta KPIs consolidados com filtros opcionais e paginação.
- `GET /api/nfe/kpis/comparativo` – Compara KPIs do mês atual com o mês anterior.
- `GET /api/nfe/notas` – Endpoint reservado para consulta detalhada (não implementado).

### Visão geral de URLs

- **Base URL (local):** `http://127.0.0.1:8000/docs#/`
- **Swagger/Docs:** `http://127.0.0.1:8000/docs`
- **OpenAPI JSON:** `http://127.0.0.1:8000/openapi.json`
- **Prefixo das rotas de API:** `/api`

### Notas das rotas

- `POST /api/nfe/processar`
  - Lê XMLs a partir de `pasta_xml` e retorna KPIs formatados em moeda pt-BR.
  - `periodo_ano`/`periodo_mes` só são preenchidos quando todas as notas estão no mesmo mês. Se houver múltiplos meses, a resposta traz apenas `periodos_encontrados`.
  - Registra automaticamente a empresa quando `empresa_id` não é informado (usa CNPJ e nome do emitente).
  - Processa e registra KPIs **por período encontrado**, retornando uma lista `kpis` com `{ano, mes, kpis}`.
- `GET /api/nfe/kpis`
  - Filtros opcionais: `emitente_cnpj`, `periodo_ano`, `periodo_mes`.
  - Paginação via `limite` (1–500) e `offset`.
- `GET /api/nfe/kpis/comparativo`
  - Parâmetros obrigatórios: `periodo_ano` e `periodo_mes`.
  - Retorna 404 quando não há KPIs para o período atual e/ou anterior.
- `GET /api/nfe/notas`
  - Retorna 501 (Not Implemented). Use `GET /api/nfe/kpis` para indicadores consolidados.

## Regras de negócio (processamento de NFe)

- É obrigatório haver pelo menos um XML válido na pasta informada.
- As notas extraídas precisam conter data de emissão válida (`dhEmi`) e totais (`ICMSTot`); XMLs sem essas informações são ignorados.
- XMLs sem `infNFe`, `ide` ou `emit` também são descartados.
- Todas as notas processadas devem pertencer ao mesmo CNPJ de emitente (senão o processamento falha).
- O nome do emitente é obrigatório para cadastro automático.
- O destinatário é opcional: quando ausente, a nota é processada com campos vazios e o cliente entra como "CLIENTE NÃO IDENTIFICADO".
- Quando há múltiplos períodos (mês/ano) nos XMLs, o processamento é feito por período e cada período gera um KPI separado.
- Deduplicação de notas usa a combinação: número da NF, data de emissão, documento do destinatário e valor total.
- KPIs consolidam top 5 clientes, produtos e cidades por valor total, além dos totais de impostos.

## Contratos de API (detalhado)

### `POST /api/nfe/processar`

**Finalidade:** Processar XMLs de NFe, consolidar dados, persistir resultados e retornar KPIs.

**Payload (JSON)**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `empresa_id` | string | Não | Identificador interno da empresa. Se ausente, a empresa é criada/identificada pelo CNPJ do emitente. |
| `origem` | string | Sim | Origem dos XMLs (ex.: `pasta_local`, `s3`, `upload`). |
| `pasta_xml` | string | Sim | Caminho da pasta com os arquivos XML. |
| `periodo` | string | Não | Período esperado no formato `YYYY-MM` (informativo). |

**Resposta (sucesso)**

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `status` | string | `"processado"` quando o fluxo conclui sem erro. |
| `cnpj_emitente` | string | CNPJ identificado nos XMLs. |
| `periodo_ano` | int | Ano consolidado. `0` se houver múltiplos períodos. |
| `periodo_mes` | int | Mês consolidado. `0` se houver múltiplos períodos. |
| `periodos_encontrados` | array | Lista de `{ "ano": int, "mes": int }` detectados nos XMLs. |
| `notas_processadas` | int | Quantidade de notas processadas após consolidação. |
| `itens_processados` | int | Quantidade total de itens processados. |
| `kpis` | array | KPIs por período com `{ "ano": int, "mes": int, "kpis": object }`.  |
| `erros` | array | Lista de erros (vazia no sucesso). |
| `data_processamento` | string | Timestamp ISO-8601 do processamento. |

**KPIs no retorno**

- Cada item de `kpis` traz o objeto `kpis` com valores monetários (`total_vendas`, `ticket_medio`, `maior_nota`, `menor_nota`, `total_icms`, `total_ipi`, `total_pis`, `total_cofins`) como **string** formatada em moeda pt-BR (ex.: `"R$ 1.234,56"`).
- `top_clientes`, `top_produtos`, `top_cidades` retornam até 5 itens, cada um com `valor_total` em moeda pt-BR e `percentual` numérico.
- Em caso de falha, a resposta traz `status = "erro"`, `kpis` vazio e contagens zeradas.


**Resposta (erro)**

Em caso de falha, o serviço retorna `status = "erro"` com `erros` preenchido. Cada item contém:

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `codigo` | string | Código interno do erro. |
| `mensagem` | string | Mensagem legível com a causa. |
| `detalhe` | string | Informações adicionais (quando aplicável). |

### `GET /api/nfe/kpis`

**Finalidade:** Consultar KPIs já persistidos, com filtros e paginação.

**Query params**

| Param | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `emitente_cnpj` | string | Não | CNPJ do emitente para filtrar resultados. |
| `periodo_ano` | int | Não | Ano para filtrar resultados (2000–2100). |
| `periodo_mes` | int | Não | Mês para filtrar resultados (1–12). |
| `limite` | int | Não | Máximo de registros retornados (1–500). |
| `offset` | int | Não | Deslocamento para paginação. |

**Resposta (sucesso)**

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `status` | string | `"ok"` quando a consulta é bem-sucedida. |
| `total` | int | Quantidade de registros retornados no payload. |
| `resultados` | array | Lista de KPIs agrupados por período (`periodo_ano`, `periodo_mes`). |

**Observações**

- Os KPIs retornados nesta rota são numéricos (não formatados), pois refletem o payload persistido.
- Se não houver resultados, `resultados` é uma lista vazia e `total` é `0`.

### `GET /api/nfe/kpis/comparativo`

**Finalidade:** Comparar KPIs do mês informado com o mês anterior.

**Query params**

| Param | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `emitente_cnpj` | string | Não | Filtra por CNPJ do emitente. |
| `periodo_ano` | int | Sim | Ano do período atual (2000–2100). |
| `periodo_mes` | int | Sim | Mês do período atual (1–12). |

**Resposta (sucesso)**

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `status` | string | `"ok"` quando o comparativo é gerado. |
| `periodo_atual_ano` | int | Ano consultado. |
| `periodo_atual_mes` | int | Mês consultado. |
| `periodo_anterior_ano` | int | Ano do período anterior. |
| `periodo_anterior_mes` | int | Mês do período anterior. |
| `emitente_cnpj` | string | CNPJ filtrado (quando enviado). |
| `kpis` | object | Estrutura comparativa (valores atuais, anteriores e variação percentual). |

**Regra de variação**

- Quando o valor anterior é `0`, a `variacao_percentual` é:
  - `0.00` se o valor atual também for `0`;
  - `null` quando não é possível calcular a variação (divisão por zero).

### `GET /api/nfe/notas`

**Finalidade:** Reservada para consulta detalhada de notas.

**Status atual:** Não implementada. Retorna `HTTP 501` com mensagem orientando o uso de `GET /api/nfe/kpis`.

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

## Fluxo de processamento

1. **Leitura de XMLs** pela classe `XmlReader`.
2. **Extração** de notas via `NFeExtractor`.
3. **Consolidação** das notas e itens com `NFeConsolidator`.
4. **Cálculo de KPIs por período** pelo `KPICalculator` (um bloco por ano/mês encontrado).
5. **Persistência por período** via `NFeProcessamentosService` + registro de KPIs associados.
6. **Resposta** no formato `ProcessarNFeResponse`, incluindo status, períodos encontrados, contagens e lista de indicadores.

## Estrutura do projeto

- `API/app/main.py` – Inicialização da aplicação FastAPI e healthcheck.
- `API/app/api/routes.py` – Rotas expostas pela API (inclui `/api/nfe/processar`).
- `API/app/services/` – Orquestração do processamento de XMLs (ex.: `process_nfe.py`).
- `API/app/domain/` – Regras de domínio: leitura de XML, extração, consolidação e cálculo de KPIs.
- `API/app/models/` – Schemas Pydantic para requests e responses.
- `API/app/adapters/` – Integrações auxiliares (por exemplo, leitura de arquivos).
- `API/app/core/` – Configurações e constantes da aplicação.