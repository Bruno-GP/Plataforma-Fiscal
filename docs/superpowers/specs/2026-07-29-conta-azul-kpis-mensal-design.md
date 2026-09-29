# Conta Azul — conectar ao banco e validar com card de faturamento mensal

## Contexto

Pedido: conectar a integração Conta Azul (`API/integracoes/conta_azul/`, CLI standalone que hoje
só exporta JSON) ao banco de dados cujas tabelas estão em
`API/integracoes/conta_azul/SQL/Tables/`. Em seguida, consultar a tabela `conta_azul_kpis` e
mostrar no painel só o card de faturamento mensal, para começar a validar dado real end-to-end.

Isso segue o corte de escopo já feito na sessão anterior: quando `tem_conta_azul=true`, o painel
mostra só `/dashboard` (ver `Painel/src/utils/workspaceAccess.ts`,
`isContaAzulDashboardOnly`). Este spec é o próximo passo — dar conteúdo real a esse dashboard
restrito.

### Duas linhas de trabalho conflitantes encontradas

Existe uma worktree separada `conta-azul-integracao` (branch não mergeada) implementando o plano
de `docs/superpowers/plans/2026-07-28-conta-azul-integracao-empresa.md` /
`docs/superpowers/specs/2026-07-28-conta-azul-integracao-empresa-design.md`: portar OAuth2 +
client pra dentro de `API/app`, schema Postgres dedicado `conta_azul.*` (não prefixo), tokens
cifrados com Fernet, sync via Celery. Essa é a decisão registrada em 28/07.

O SQL apontado neste pedido (`API/integracoes/conta_azul/SQL/Tables/Conta Azul DB.sql`) decide o
oposto explicitamente no cabeçalho: **sem schema separado**, tabelas `public.conta_azul_*`. Esse
arquivo já está commitado na `dev` (commit `7ff0136`, 28/07 à noite — posterior ao spec do
schema dedicado).

**Decisão do usuário nesta sessão (29/07):** seguir a linha já commitada na `dev` — CLI
standalone + `public.conta_azul_*` — para esta fatia (kpis/validação). A worktree com schema
dedicado + OAuth2 na API principal não é tocada aqui; fica como possível base para uma integração
completa (todas as entidades: pessoas, produtos, vendas, parcelas, notas fiscais) numa sessão
futura, se for retomada.

## Escopo desta fase

Só a tabela `conta_azul_kpis` (faturamento mensal). As outras 9 tabelas de
`Conta Azul DB.sql` (pessoas, produtos, vendas, categorias, eventos financeiros, parcelas, notas
fiscais...) ficam fora — não há comando de sync pra elas ainda, nem endpoint, nem UI. Isso é
follow-up explícito, não um esquecimento.

## 1. Corrige `Conta Azul KPIS.sql`

Bugs no arquivo atual:
- Vírgula sobrando antes do `)` de fechamento do `CREATE TABLE` — SQL inválido.
- Sem `empresa_id` — tabela hoje é global, não por empresa.
- `ON CONFLICT (mes)` no INSERT de teste sem `UNIQUE (mes)` correspondente — também inválido.

Correção:

```sql
CREATE TABLE IF NOT EXISTS conta_azul_kpis (
  id               SERIAL          PRIMARY KEY,
  empresa_id       BIGINT          NOT NULL,
  mes              DATE            NOT NULL,
  total_pedidos    INTEGER         NOT NULL DEFAULT 0,
  clientes_ativos  INTEGER         NOT NULL DEFAULT 0,
  receita_total    NUMERIC(15, 2)  NOT NULL DEFAULT 0,
  ticket_medio     NUMERIC(15, 2)  NOT NULL DEFAULT 0,
  criado_em        TIMESTAMPTZ     NOT NULL DEFAULT now(),
  atualizado_em    TIMESTAMPTZ     NOT NULL DEFAULT now(),
  CONSTRAINT fk_ca_kpis_empresa
      FOREIGN KEY (empresa_id) REFERENCES empresas(id)
      ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT uq_ca_kpis_empresa_mes UNIQUE (empresa_id, mes)
);
```

O INSERT de teste do arquivo original é removido — dado real passa a vir do comando `sync-kpis`
(seção 3). O unique constraint `(empresa_id, mes)` já serve de índice pra consulta ordenada por
`mes` dentro de uma empresa.

## 2. Conectividade com Postgres no CLI

Novo módulo `API/integracoes/conta_azul/contaazul/db.py`, espelhando
`API/app/services/sped/postgres_config.py` (mesma cadeia de variáveis de ambiente com fallback,
mesmo Postgres físico `plataforma_fiscal` usado pela API principal — não é um banco separado):

```python
def carregar_config_postgres_conta_azul() -> dict: ...  # POSTGRES_CONTA_AZUL_* -> POSTGRES_* -> DATABASE_URL
def conectar() -> "psycopg2.extensions.connection": ...
```

- Adiciona `psycopg2-binary` em `API/integracoes/conta_azul/requirements.txt`.
- Adiciona `POSTGRES_CONTA_AZUL_DSN` (ou host/port/db/user/password) em
  `API/integracoes/conta_azul/.env` e `.env.example`, apontando pro mesmo Postgres da API
  principal.

## 3. Novo comando `sync-kpis`

```bash
python main.py sync-kpis --empresa-id 1 --inicio 2026-01-01 --fim 2026-01-31
```

- `empresa_id`: obrigatório, BIGINT — id em `public.empresas`. A CLI é single-tenant hoje (um
  `.tokens.json`, uma conta Conta Azul via `.env`), então quem chama informa manualmente pra qual
  empresa aquele dado pertence. Sem resolução automática por CNPJ nesta fase.
- Busca vendas via `client.listar_vendas` + `_coletar_todas_paginas` (já existe, reaproveitado).
- Novo `contaazul/kpis.py`, função pura `agregar_kpis_mensais(vendas: list[Venda]) -> dict[date, KpiMensal]`:
  agrupa por `data.replace(day=1)`; por mês: `total_pedidos = len(vendas_do_mes)`,
  `clientes_ativos = len({cliente id distinto})`, `receita_total = sum(total)`,
  `ticket_medio = receita_total / total_pedidos se total_pedidos > 0 senão 0`.
- Novo `exporters/postgres_kpis_exporter.py`, `PostgresKpisExporter.export(empresa_id, kpis_por_mes, conn)`:
  upsert por mês —
  `INSERT ... ON CONFLICT (empresa_id, mes) DO UPDATE SET total_pedidos=EXCLUDED.total_pedidos, ..., atualizado_em=now()`.
- Mantém o padrão de erro dos outros comandos (`AuthError`/`ApiError` → `typer.secho` vermelho +
  `Exit(1)`).

## 4. Backend (`API/app`)

Segue a convenção existente (raw `psycopg`, camadas routes → services → repositories, sem ORM —
ver `sped_repository.py`).

- `api/shared/company_validation.py`: `validar_empresa_conta_azul(cnpj)` — espelha
  `validar_empresa_sped`, usa `CompanyProfileService.empresa_tem_conta_azul`.
- `models/conta_azul/schemas.py`: `ContaAzulKpiMensal` (`mes: date`, `total_pedidos: int`,
  `clientes_ativos: int`, `receita_total: Decimal`, `ticket_medio: Decimal`) e
  `ConsultaContaAzulKpisResponse` (`status: str`, `resultados: list[ContaAzulKpiMensal]`).
- `services/conta_azul/postgres_config.py`: mesmo padrão do `services/sped/postgres_config.py`,
  variáveis `POSTGRES_CONTA_AZUL_*` (mesmo Postgres físico).
- `repositories/conta_azul/conta_azul_repository.py`: `ContaAzulRepository(conn_params)`,
  `listar_kpis(empresa_id, limite=12) -> list[tuple]` —
  `SELECT mes, total_pedidos, clientes_ativos, receita_total, ticket_medio FROM conta_azul_kpis WHERE empresa_id = %s ORDER BY mes DESC LIMIT %s`.
- `services/conta_azul/conta_azul_consulta_service.py`: `ContaAzulConsultaService.listar_kpis(empresa_id, limite)`,
  monta os `ContaAzulKpiMensal`.
- `api/conta_azul/routes.py`: `conta_azul_router = APIRouter(prefix="/conta-azul", tags=["Conta Azul"], dependencies=[Depends(require_company_scope)])`,

  ```python
  @conta_azul_router.get("/analise/kpis", response_model=ConsultaContaAzulKpisResponse)
  def consultar_kpis_conta_azul(
      emitente_cnpj: str = Query(..., min_length=14, max_length=20),
      limite: int = Query(default=12, ge=1, le=120),
      current_user: AuthenticatedUser = Depends(get_current_user),
  ):
      validar_empresa_conta_azul(emitente_cnpj)
      resultados = ContaAzulConsultaService().listar_kpis(current_user.empresa_id, limite)
      return ConsultaContaAzulKpisResponse(status="ok", resultados=resultados)
  ```

  `require_company_scope` já garante que `emitente_cnpj` bate com a sessão; `current_user.empresa_id`
  vem pronto do JWT, sem round-trip extra pra resolver cnpj → id.
- Registra `conta_azul_router` em `api/routes.py` (`router.include_router(conta_azul_router)`).
- **Não muda nada no frontend HTTP client** — `Painel/src/services/contaAzul.ts` já chama
  exatamente `GET /conta-azul/analise/kpis?emitente_cnpj=...`.

## 5. Frontend

Hoje `/dashboard` sempre renderiza `AnaliseVendas` (`pages/AnaliseVendas.tsx`) — dashboard
completo com rankings, mapa de vendas e gráfico de evolução, todos dependendo de endpoints
`/conta-azul/analise/*` que não existem e não entram nesta fase.

- Nova página `Painel/src/pages/ContaAzulDashboard.tsx`: um único `StatCard` ("Faturamento
  Mensal"), buscando via `fetchContaAzulKpis` (já existe em `services/contaAzul.ts`, sem
  mudança), exibindo o `receita_total` do primeiro item retornado (mês mais recente, já que a
  API ordena por `mes DESC`). Estados de loading/erro seguem o padrão do `StatCard`
  (`isLoading`) e do bloco de erro já usado em `AnaliseVendas.tsx`.
- `App.tsx`: a rota `/dashboard` passa a escolher entre `<Dashboard />` (AnaliseVendas) e
  `<ContaAzulDashboard />` conforme `user?.tem_conta_azul`, mesmo padrão do `ImportacaoFiscalRoute`
  (componente wrapper que decide por flag de usuário).

## Fora de escopo (follow-up)

- Sync de pessoas/produtos/vendas/categorias/eventos financeiros/parcelas/notas fiscais pras
  outras 9 tabelas de `Conta Azul DB.sql`.
- Dashboard completo (rankings, mapa, evolução) pra origem Conta Azul.
- OAuth2 automatizado / multi-tenant / Celery — isso é o que a worktree `conta-azul-integracao`
  já está desenhando separadamente; não mexido aqui.
- Resolução automática de `empresa_id` por CNPJ no `sync-kpis` (hoje é flag manual).

## Testes

- `contaazul/kpis.py`: teste unitário puro de `agregar_kpis_mensais` (várias vendas no mesmo mês,
  vendas em meses diferentes, venda sem cliente, lista vazia).
- `exporters/postgres_kpis_exporter.py`: teste de upsert (insert novo mês, update mês existente)
  contra Postgres real ou mock de cursor.
- Backend: `ContaAzulRepository.listar_kpis` (mock de conexão) + teste de rota
  `GET /conta-azul/analise/kpis` (empresa sem `tem_conta_azul` → 400; empresa certa → 200 com
  resultados).
- Frontend: `ContaAzulDashboard.test.tsx` (loading, sucesso mostrando valor formatado, erro) +
  ajuste em `App.tsx` (ou teste de rota) garantindo que `tem_conta_azul=true` renderiza
  `ContaAzulDashboard` em vez de `AnaliseVendas`.
