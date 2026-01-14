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

### Notas das rotas

- `POST /api/nfe/processar`
  - Lê XMLs a partir de `pasta_xml` e retorna KPIs formatados em moeda pt-BR.
  - `periodo_ano`/`periodo_mes` só são preenchidos quando todas as notas estão no mesmo mês. Se houver múltiplos meses, a resposta traz apenas `periodos_encontrados`.
- `GET /api/nfe/kpis`
  - Filtros opcionais: `emitente_cnpj`, `periodo_ano`, `periodo_mes`.
  - Paginação via `limite` (1–500) e `offset`.
- `GET /api/nfe/kpis/comparativo`
  - Parâmetros obrigatórios: `periodo_ano` e `periodo_mes`.
  - Retorna 404 quando não há KPIs para o período atual e/ou anterior.
- `GET /api/nfe/notas`
  - Retorna 501 (não implementado). Use `GET /api/nfe/kpis` para indicadores consolidados.

## Regras de negócio (processamento de NFe)

- É obrigatório haver pelo menos um XML válido na pasta informada.
- As notas extraídas precisam conter data de emissão válida.
- Todas as notas processadas devem pertencer ao mesmo CNPJ de emitente (senão o processamento falha).
- O nome do emitente é obrigatório para cadastro automático.
- Deduplicação de notas usa a combinação: número da NF, data de emissão, documento do destinatário e valor total.
- KPIs consolidam top 5 clientes, produtos e cidades por valor total, além dos totais de impostos.

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
  "kpis": {
    "total_vendas": "150000.00",
    "quantidade_notas": 10,
    "ticket_medio": "15000.00",
    "maior_nota": "25000.00",
    "menor_nota": "5000.00",
    "total_icms": "18000.00",
    "total_ipi": "0.00",
    "total_pis": "0.00",
    "total_cofins": "0.00",
    "top_clientes": [],
    "top_produtos": [],
    "top_cidades": []
  },
  "erros": [],
  "data_processamento": "2024-05-10T12:00:00.000Z"
}
```

## Fluxo de processamento

1. **Leitura de XMLs** pela classe `XmlReader`.
2. **Extração** de notas via `NFeExtractor`.
3. **Consolidação** das notas e itens com `NFeConsolidator`.
4. **Cálculo de KPIs** pelo `KPICalculator`.
5. **Resposta** no formato `ProcessarNFeResponse`, incluindo status, períodos encontrados, contagens e indicadores.

## Estrutura do projeto

- `API/app/main.py` – Inicialização da aplicação FastAPI e healthcheck.
- `API/app/api/routes.py` – Rotas expostas pela API (inclui `/api/nfe/processar`).
- `API/app/services/` – Orquestração do processamento de XMLs (ex.: `process_nfe.py`).
- `API/app/domain/` – Regras de domínio: leitura de XML, extração, consolidação e cálculo de KPIs.
- `API/app/models/` – Schemas Pydantic para requests e responses.
- `API/app/adapters/` – Integrações auxiliares (por exemplo, leitura de arquivos).
- `API/app/core/` – Configurações e constantes da aplicação.