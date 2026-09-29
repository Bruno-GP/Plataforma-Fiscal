# Metas com análise de indicadores — fase 1 (backend)

## Contexto

Pedido original: módulo de Metas que não é só "definir número e esquecer" — cada meta vem
acompanhada de análise do histórico do indicador (tendência, projeção, diagnóstico automático).
O prompt de origem trazia premissas de um projeto diferente (`empresa_id` UUID + integração
"Plataforma-Matriz"). Esse repositório não tem isso: multi-tenant é `empresas.id BIGSERIAL` +
escopo por CNPJ (`require_company_scope`, `docs/security.md`). Este spec reconcilia o pedido com
o schema e as convenções reais do projeto.

**Decisões tomadas com o usuário (13/08):**
- Seguir o modelo de tenant existente (`empresas.id` BIGINT), não UUID/Plataforma-Matriz.
- v1 cobre só perfil XML/NFe (`tem_sped=false`). SPED entra depois reaproveitando o mesmo motor
  de análise, trocando só a fonte de dado.
- `indicador_historico` é materializado por job Celery periódico (não calculado ao vivo na tela).

**Achado que muda o escopo do job:** a tabela `notas_kpis` (Alembic inicial,
`API/app/alembic/versions/20260505_0001_initial_schema.py`) já persiste KPIs por
`processamento_id`/`emitente_cnpj`/`periodo_ano`/`periodo_mes`: `total_vendas`, `ticket_medio`,
`quantidade_notas`, `maior_nota`, `menor_nota`, `total_icms`, `total_ipi`, `total_pis`,
`total_cofins`. O job de materialização de `indicador_historico` não recalcula de `notas`/
`notas_itens` — só agrega `notas_kpis` por mês (pode haver mais de um `processamento_id` no
mesmo mês, cada import gera uma linha).

## Escopo desta fase

Só backend: modelo de dados, migration, `AnaliseMetaService` com testes, job Celery de
materialização, endpoints. Frontend (lista de metas, gráfico, tela de criação) fica pra um spec
seguinte, depois que o motor de análise estiver validado com dado real.

Fora do escopo: catálogo de indicadores editável por usuário (v1 é seed fixo via migration),
perfil SPED, geração de diagnóstico via LLM (função isolada preparada, não implementada),
notificação/alerta de meta em risco.

## 1. Catálogo de indicadores v1

Perfil `xml`, fonte `notas_kpis`, todos derivados de colunas já existentes:

| chave | nome | unidade | direcao_boa | coluna em `notas_kpis` |
|---|---|---|---|---|
| `faturamento` | Faturamento | moeda | maior_melhor | `total_vendas` |
| `ticket_medio` | Ticket médio | moeda | maior_melhor | `ticket_medio` (média ponderada, ver job) |
| `quantidade_notas` | Quantidade de notas | numero | maior_melhor | `quantidade_notas` |
| `total_icms` | ICMS pago | moeda | menor_melhor | `total_icms` |
| `total_ipi` | IPI pago | moeda | menor_melhor | `total_ipi` |
| `total_pis_cofins` | PIS+COFINS pago | moeda | menor_melhor | `total_pis + total_cofins` |

Sem inadimplência / prazo médio de recebimento / margem — não existem no fluxo NFe (dado
tributário, não financeiro/contas a receber).

## 2. Modelo de dados

```sql
CREATE TABLE IF NOT EXISTS indicadores (
    id              BIGSERIAL       PRIMARY KEY,
    chave           VARCHAR(50)     NOT NULL UNIQUE,
    nome            VARCHAR(120)    NOT NULL,
    unidade         VARCHAR(20)     NOT NULL CHECK (unidade IN ('moeda','percentual','numero','dias')),
    fonte           VARCHAR(50)     NOT NULL DEFAULT 'notas_kpis',
    direcao_boa     VARCHAR(20)     NOT NULL CHECK (direcao_boa IN ('maior_melhor','menor_melhor')),
    perfil          VARCHAR(10)     NOT NULL DEFAULT 'xml' CHECK (perfil IN ('xml','sped')),
    ativo           BOOLEAN         NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS indicador_historico (
    id                  BIGSERIAL       PRIMARY KEY,
    empresa_id          BIGINT          NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    indicador_id        BIGINT          NOT NULL REFERENCES indicadores(id) ON DELETE CASCADE,
    periodo_referencia  DATE            NOT NULL,
    valor               NUMERIC(18,2)   NOT NULL,
    calculado_em        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE (empresa_id, indicador_id, periodo_referencia)
);
CREATE INDEX IF NOT EXISTS idx_indicador_historico_busca
    ON indicador_historico (empresa_id, indicador_id, periodo_referencia);

CREATE TABLE IF NOT EXISTS metas (
    id              BIGSERIAL       PRIMARY KEY,
    empresa_id      BIGINT          NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    indicador_id    BIGINT          NOT NULL REFERENCES indicadores(id),
    titulo          VARCHAR(200)    NOT NULL,
    descricao       TEXT,
    valor_alvo      NUMERIC(18,2)   NOT NULL,
    tipo_meta       VARCHAR(20)     NOT NULL CHECK (tipo_meta IN ('crescimento','reducao','manutencao')),
    periodo_tipo    VARCHAR(20)     NOT NULL CHECK (periodo_tipo IN ('mensal','trimestral','anual','custom')),
    periodo_inicio  DATE            NOT NULL,
    periodo_fim     DATE            NOT NULL,
    status          VARCHAR(20)     NOT NULL DEFAULT 'ativa' CHECK (status IN ('ativa','atingida','nao_atingida','cancelada')),
    criado_por      BIGINT          NOT NULL REFERENCES login(id),
    criado_em       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CHECK (periodo_fim >= periodo_inicio)
);
CREATE INDEX IF NOT EXISTS idx_metas_empresa_status ON metas (empresa_id, status);
```

Seed dos 6 indicadores acima entra na própria migration (`INSERT ... ON CONFLICT (chave) DO
NOTHING`).

## 3. Job de materialização (`indicador_historico`)

Task Celery nova em `app/workers/metas_tasks.py`, fila `default`, agendada no beat (diária —
mantém mês corrente atualizado e fecha meses anteriores). Para cada indicador `xml` ativo:

```sql
SELECT emitente_cnpj, periodo_ano, periodo_mes,
       SUM(total_vendas) AS faturamento,
       SUM(quantidade_notas) AS quantidade_notas,
       CASE WHEN SUM(quantidade_notas) > 0
            THEN SUM(total_vendas) / SUM(quantidade_notas) ELSE 0 END AS ticket_medio,
       SUM(total_icms) AS total_icms,
       SUM(total_ipi) AS total_ipi,
       SUM(total_pis) + SUM(total_cofins) AS total_pis_cofins
FROM notas_kpis
GROUP BY emitente_cnpj, periodo_ano, periodo_mes;
```

Resolve `empresa_id` via `empresas.cnpj = emitente_cnpj`, faz upsert em `indicador_historico`
(`ON CONFLICT (empresa_id, indicador_id, periodo_referencia) DO UPDATE`). `ticket_medio`
recalculado como faturamento/quantidade agregados (não média das médias — evita viés quando um
mês tem mais de um `processamento_id`).

Service que orquestra: `MetasHistoricoService` (`app/services/metas/`), chamado pela task e
testável isolado com repositório fake.

## 4. `AnaliseMetaService`

`app/services/metas/analise_meta_service.py` — puro, recebe a série (`list[tuple[date, Decimal]]`)
e parâmetros da meta, devolve um dataclass `AnaliseMeta`. Sem I/O, sem import de FastAPI/DB.

- **Estatística**: `statistics.mean/median/pstdev` (stdlib — sem numpy/scipy, não tem no
  `requirements.txt`) sobre os últimos N períodos anteriores ao período da meta (N=6 mensal,
  N=4 trimestral, configurável).
- **Tendência**: regressão linear simples via OLS manual (`slope = cov(x,y)/var(x)`, sem libs
  externas). Slope normalizado como % da média da série, classificado:
  `crescimento_forte` (>+10%), `crescimento_leve` (+3% a +10%), `estavel` (-3% a +3%),
  `queda_leve` (-10% a -3%), `queda_forte` (<-10%).
- **Ritmo/projeção**: `tempo_decorrido_pct = dias_decorridos / dias_totais_periodo`;
  `projecao_fim_periodo = valor_realizado_atual / tempo_decorrido_pct` (regra de ritmo linear,
  não é regressão sobre o período corrente — este é curto demais pra regressão confiável).
  `status_ritmo` compara projeção vs `valor_alvo` respeitando `direcao_boa`:
  - `maior_melhor`: projeção ≥ 95% da meta → `no_caminho`; 80–95% → `em_risco`; <80% → `fora_da_rota`.
  - `menor_melhor`: inverte (projeção ≤ 105% da meta → `no_caminho`; 105–120% → `em_risco`; >120% → `fora_da_rota`).
- **Diagnóstico**: função separada `gerar_diagnostico(analise: AnaliseMeta) -> str`, templates
  de frase por combinação tendência × ritmo × direção, sem LLM nessa v1. Preparado pra trocar por
  geração via LLM depois (mesma assinatura, outra implementação).
- **Sazonalidade**: se série ≥ 12 meses, compara mesmo mês do ano anterior; entra no retorno como
  campo opcional `comparativo_ano_anterior_pct`, não altera a classificação de tendência.

## 5. Endpoints

Sem `empresa_id` de query — todo filtro usa `current_user.empresa_id` do token
(`Depends(get_current_user)`), mesmo padrão de `/api/jobs`. Uma `meta`/`indicador_historico` que
não bate com `current_user.empresa_id` simplesmente não aparece (404), sem vazar existência.

```
POST   /api/metas                    -> cria meta (valida indicador ativo + perfil xml)
GET    /api/metas?status=&indicador_id=
GET    /api/metas/{id}
GET    /api/metas/{id}/analise       -> AnaliseMeta serializado
PATCH  /api/metas/{id}
DELETE /api/metas/{id}               -> soft delete (status='cancelada')
GET    /api/indicadores?perfil=xml
GET    /api/indicadores/{id}/historico?meses=12
```

Camadas: `api/metas/routes.py` (fino) → `services/metas/metas_service.py` (orquestra) →
`repositories/metas/metas_repository.py` (SQL) — segue `docs/backend-target-structure.md`.

## 6. Erros HTTP

- `400`: `periodo_fim < periodo_inicio`, indicador de perfil errado pra empresa (`tem_sped` não
  bate), `valor_alvo <= 0`.
- `404`: meta/indicador inexistente ou fora do escopo da empresa.
- `422`: validação Pydantic padrão.
- Sem `409` — múltiplas metas por indicador são permitidas (usuário pode ter meta mensal e
  trimestral do mesmo indicador simultâneas).

## 7. Testes

- `AnaliseMetaService`: séries sintéticas puras (sem banco) — crescimento constante, queda
  constante, estável, sazonal (12+ meses com pico repetido), série vazia/curta (< N períodos,
  deve degradar sem exceção). Cobre as 5 faixas de tendência e as 3 faixas de ritmo nos dois
  sentidos de `direcao_boa`.
- `MetasHistoricoService`: repositório fake, valida agregação SQL (mock de linhas de
  `notas_kpis` com mais de um `processamento_id` no mesmo mês).
- Rotas: `TestClient` + fake repository via `monkeypatch.setattr`, seguindo `conftest.py`
  (`require_company_scope` já sobrescrito com usuário anônimo `empresa_id=1`).

## Fora do escopo (follow-up explícito)

- Frontend (lista, gráfico, criação) — spec seguinte.
- Perfil SPED.
- Alerta/notificação de meta em risco.
- Diagnóstico via LLM.
- Catálogo de indicadores editável pelo usuário.
