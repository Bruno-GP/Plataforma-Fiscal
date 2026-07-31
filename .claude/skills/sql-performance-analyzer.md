---
name: sql-performance-analyzer
description: Analisa queries SQL do projeto (FastAPI + PostgreSQL), mede desempenho, identifica gargalos e propõe versão otimizada com impacto explicado na Plataforma Fiscal. Use quando o usuário pedir para analisar, revisar ou otimizar uma query SQL, ou quando uma rota da API estiver lenta.
argument-hint: "<cole a query SQL aqui ou informe o arquivo/rota com problema>"
---

# /sql-performance-analyzer — Análise e Otimização de Queries SQL

Analisa queries SQL do projeto, identifica problemas de performance e entrega
uma versão otimizada com explicação clara do impacto na Plataforma Fiscal.

## Uso

```
/sql-performance-analyzer <query SQL ou caminho do arquivo>
```

---

## Workflow

### 1. Receber a Query

Aceitar a query de três formas:
- **Colada diretamente** no prompt
- **Caminho de arquivo** (ex: `app/repositories/nota_fiscal.py`) — ler o arquivo e extrair as queries relevantes
- **Nome de rota/endpoint** — localizar o arquivo no projeto e extrair a query usada

Se o usuário informar apenas uma rota lenta (ex: `/api/v1/notas`), usar `grep` recursivo para localizar a query correspondente no codebase.

---

### 2. Inspecionar o Schema (sempre que possível)

Antes de analisar, buscar no projeto:

```bash
# Localizar models e migrations
find . -path "*/migrations/*.py" | head -20
find . -name "models.py" -o -name "models/*.py" | head -10
```

Identificar:
- Tabelas envolvidas na query
- Colunas existentes e seus tipos
- Índices já definidos (checar nas migrations Alembic)
- Relacionamentos (FKs, JOINs esperados)
- Volume estimado de dados (se houver comentários ou seeds no projeto)

---

### 2.5. Coletar Volume Real de Dados (quando banco acessível)

Se houver acesso ao banco de desenvolvimento, executar **antes** da análise estática:

```sql
-- Volume de cada tabela envolvida na query
SELECT
    schemaname,
    relname AS tabela,
    n_live_tup AS linhas_estimadas,
    pg_size_pretty(pg_total_relation_size(relid)) AS tamanho_total
FROM pg_stat_user_tables
WHERE relname IN (<tabelas_da_query>)
ORDER BY n_live_tup DESC;

-- Índices existentes nas tabelas
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN (<tabelas_da_query>);
```

Usar esses números reais para calibrar a severidade do diagnóstico:
- Query com `SELECT *` em tabela de 500 rows → severidade BAIXA
- Query com `SELECT *` em tabela de 2M rows → severidade ALTA
- Índice faltando em tabela de 1k rows → ⚠️ Atenção
- Índice faltando em tabela de 500k rows → ❌ Problema crítico

Incluir os números reais na seção **Estimativa de impacto** do relatório.

---

### 3. Analisar a Query Original

Avaliar cada um dos seguintes pontos e marcar como ✅ OK, ⚠️ Atenção ou ❌ Problema:

#### 3.1 Estrutura Geral
- [ ] `SELECT *` sendo usado (nunca em produção — selecionar só o necessário)
- [ ] Subqueries correlacionadas desnecessárias (trocar por JOIN ou window function)
- [ ] CTEs vs subqueries inline (CTEs melhoram legibilidade e reuso)
- [ ] Funções aplicadas em colunas filtradas no WHERE (impedem uso de índice)

#### 3.2 JOINs
- [ ] Tipo de JOIN correto (INNER vs LEFT vs RIGHT)
- [ ] Risco de produto cartesiano (JOIN sem condição adequada)
- [ ] Cardinalidade dos JOINs (many-to-many pode explodir o resultado)
- [ ] Ordem dos JOINs (tabela menor ou mais filtrada primeiro)

#### 3.3 Filtros e Índices
- [ ] Colunas no WHERE/JOIN têm índice correspondente?
- [ ] Funções sobre colunas indexadas quebram o índice (ex: `WHERE EXTRACT(year FROM criado_em) = 2024`)
- [ ] LIKE com `%` no início impossibilita uso de índice (ex: `WHERE descricao LIKE '%nota%'`)
- [ ] IN com lista grande (substituir por JOIN em tabela temporária ou ANY)

#### 3.4 Agregações e Ordenação
- [ ] GROUP BY em colunas não indexadas com grande volume
- [ ] ORDER BY sem LIMIT em queries de listagem
- [ ] DISTINCT desnecessário (resolver na lógica de JOIN)
- [ ] Window functions mal posicionadas (filtrar antes, não depois)

#### 3.5 Padrões Específicos do Projeto
- [ ] Queries de NFC-e filtrando por `empresa_id` sem índice composto
- [ ] Busca em JSON/JSONB sem índice GIN
- [ ] Queries de relatório sem paginação (`LIMIT`/`OFFSET` ou keyset pagination)
- [ ] N+1 query pattern vindo do ORM (SQLAlchemy carregando relações em loop)

#### 3.6 Padrões SQLAlchemy ORM (quando aplicável)

Se a query vier de código SQLAlchemy (ORM), avaliar também:

- [ ] **N+1 clássico**: loop em Python fazendo query por item
  ```python
  # ❌ N+1 — 1 query pra lista + 1 por nota
  notas = session.query(Nota).all()
  for nota in notas:
      print(nota.itens)  # query disparada aqui

  # ✅ Correto — tudo em 1 query com JOIN
  notas = session.query(Nota).options(joinedload(Nota.itens)).all()
  ```

- [ ] **Lazy loading implícito**: relações sem `lazy="joined"` ou `joinedload()` explícito em endpoints que sempre precisam da relação

- [ ] **Query gerada pelo ORM é eficiente?**: ativar log de SQL para ver o que o ORM está gerando:
  ```python
  # No .env de desenvolvimento
  SQLALCHEMY_ECHO=true
  ```
  Colar a query gerada na análise se for diferente do que o código sugere.

- [ ] **`selectinload` vs `joinedload`**: para coleções grandes, `selectinload` evita produto cartesiano
  ```python
  # joinedload → 1 query com JOIN (bom para relações 1:1 ou 1:poucos)
  .options(joinedload(Nota.empresa))

  # selectinload → 2 queries separadas (bom para coleções grandes)
  .options(selectinload(Nota.itens))
  ```

- [ ] **`.count()` via ORM**: gera subquery desnecessária — usar `func.count()` diretamente
  ```python
  # ❌ Gera SELECT COUNT(*) FROM (SELECT ... FROM notas) AS anon
  session.query(Nota).filter(...).count()

  # ✅ SELECT COUNT(*) FROM notas WHERE ...
  session.query(func.count(Nota.id)).filter(...).scalar()
  ```

---

### 4. Gerar o Relatório de Análise

Apresentar sempre neste formato:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 QUERY ORIGINAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[query original aqui em bloco SQL]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 DIAGNÓSTICO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Problema 1: <descrição direta do problema>
   → Por quê impacta: <explicação em 1-2 linhas>

⚠️  Atenção 2: <descrição>
   → Por quê impacta: <explicação>

✅ OK: <o que está correto>

Severidade geral: ALTA / MÉDIA / BAIXA
Estimativa de impacto: <ex: "pode reduzir tempo de resposta de ~800ms para ~50ms">

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ QUERY OTIMIZADA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[query otimizada aqui em bloco SQL com comentários explicando cada mudança]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 O QUE MUDOU E POR QUÊ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
| Mudança           | Antes          | Depois         | Ganho esperado        |
|-------------------|----------------|----------------|-----------------------|
| SELECT *          | Todas colunas  | 5 colunas      | Menos I/O e memória   |
| JOIN order        | tabela_grande  | tabela_pequena | Menos rows processadas|
| Índice faltando   | Full scan      | Index scan     | 10x-100x mais rápido  |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🗄️  ÍNDICES RECOMENDADOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[só se necessário — migration Alembic pronta para aplicar]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏗️  IMPACTO NA PLATAFORMA FISCAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[descrever como essa query se conecta ao fluxo do sistema:
 qual endpoint usa, qual volume de dados processa, frequência de chamada,
 e o que melhora na experiência do usuário final]
```

---

### 5. Índices Recomendados

Se identificar índice faltando, gerar a migration Alembic correspondente:

```python
# migrations/versions/XXXX_add_index_<tabela>_<coluna>.py

def upgrade():
    op.create_index(
        'ix_<tabela>_<coluna>',
        '<tabela>',
        ['<coluna>'],
        unique=False
    )
    # Para índice composto:
    # op.create_index('ix_notas_empresa_emitido_em', 'notas_fiscais',
    #                 ['empresa_id', 'emitido_em'], unique=False)

def downgrade():
    op.drop_index('ix_<tabela>_<coluna>', table_name='<tabela>')
```

---

### 6. Aplicar a Otimização

Após apresentar o relatório, perguntar:

```
Deseja que eu aplique a query otimizada diretamente no arquivo?
[S] Sim — substituir no arquivo original
[N] Não — só quero ver a sugestão
[M] Mostrar diff antes de aplicar
```

Se confirmado, usar `str_replace` para substituir a query original pela otimizada
no arquivo do projeto. Nunca aplicar sem confirmação explícita.

---

### 7. EXPLAIN ANALYZE — Plano de Execução Real

Se o banco de desenvolvimento estiver acessível, executar automaticamente:

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
<query_original_aqui>;
```

Extrair e apresentar do output:
- **Tipo de scan** usado em cada tabela: `Seq Scan` (ruim em tabelas grandes) vs `Index Scan` / `Bitmap Index Scan` (bom)
- **Rows estimadas vs reais**: divergência grande indica estatísticas desatualizadas → sugerir `ANALYZE <tabela>`
- **Custo total** (o número após `cost=X..Y`) — comparar antes e depois da otimização
- **Tempo real** em ms — incluir no relatório como número concreto
- **Buffers hit vs read** — hit = cache, read = disco (read alto = problema)

Repetir o `EXPLAIN ANALYZE` com a **query otimizada** e incluir comparação:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ PLANO DE EXECUÇÃO — COMPARATIVO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
| Métrica          | Query Original | Query Otimizada | Melhoria     |
|------------------|----------------|-----------------|--------------|
| Tempo real       | 843ms          | 12ms            | 70x mais rápida |
| Tipo de scan     | Seq Scan       | Index Scan      | ✅           |
| Custo estimado   | 48320.00       | 124.50          | 388x menor   |
| Buffers (read)   | 2841           | 18              | 157x menos I/O |
```

Se o banco **não estiver acessível**, gerar o `EXPLAIN ANALYZE` como bloco de código
para o usuário rodar manualmente em staging e trazer o resultado.

---

### 8. Verificação Pós-Otimização

Após aplicar, checar automaticamente:
- Sintaxe da query (sem erros de SQL)
- Testes existentes que cobrem essa query ainda passam (`pytest -x -q`)
- Se EXPLAIN ANALYZE ainda não foi rodado, lembrar de executar em staging antes de ir pra produção

---

## Exemplos de Uso

```
/sql-performance-analyzer SELECT * FROM notas_fiscais nf JOIN itens i ON nf.id = i.nota_id WHERE nf.empresa_id = 1

/sql-performance-analyzer app/repositories/relatorio_fiscal.py

/sql-performance-analyzer a rota GET /api/v1/dashboard está lenta
```

---

## Regras Importantes

- **Nunca alterar** o arquivo original sem confirmação explícita do usuário
- **Sempre mostrar** a query original e a otimizada lado a lado
- **Migrations Alembic** geradas nunca devem alterar dados existentes, só estrutura
- **Padrão do projeto**: usar SQLAlchemy Core ou ORM — não misturar com SQL raw sem motivo
- **Dialect**: PostgreSQL — usar sintaxe e funções específicas (ex: `ILIKE`, `ANY`, `GIN index`, `RETURNING`)
- **empresa_id** é sempre chave de filtro obrigatória nas queries multi-tenant — verificar se está presente
- **EXPLAIN ANALYZE**: sempre executar se banco acessível — nunca estimar impacto sem dados reais quando possível
- **ORM vs SQL raw**: se o problema vier do ORM, corrigir no ORM (não contornar com SQL raw) — manter consistência do projeto
- **Volume importa**: severidade do diagnóstico deve ser calibrada com o volume real da tabela — um problema em 500 rows não é emergência