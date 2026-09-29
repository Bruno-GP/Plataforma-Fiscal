# Integração Conta Azul — seção no cadastro de empresa

## Contexto

Pedido original: adicionar seção "Conta Azul" na tela de cadastro/edição de empresa (React),
com OAuth2, status da integração e painel de últimos dados sincronizados. O pedido assumia
que o backend já tinha as rotas de OAuth2 implementadas e que as tabelas
`conta_azul.integracoes`/`conta_azul.sincronizacoes` já existiam.

## Achados que mudam o escopo original

- **Backend não existe.** `API/app` (FastAPI principal) não tem nenhuma rota
  `/api/empresas/{id}/integracoes/conta-azul*`, nem tabelas `conta_azul.*`. O que existe é uma
  CLI standalone e desconectada em `API/contaazul-integracao/`, com OAuth2 funcional
  (`contaazul/auth.py`) e um client HTTP completo (`contaazul/client.py`, com paginação, retry
  via `tenacity` e tratamento de erro) contra a API real do Conta Azul — mas sem nenhuma
  persistência em Postgres, sem Celery, sem rotas web.
- **Projeto é TypeScript**, não JSX puro. Stack real: Vite + React 18 + TS, Tailwind + shadcn/ui
  (`Badge`, `Button`, `Dialog`, `Loader2` como spinner), hook `useToast` (`hooks/use-toast.ts`),
  wrapper `apiFetch` sobre fetch nativo (`services/api.ts`) — sem axios.
- **Não existe form multi-seção de empresa.** A tela certa pra encaixar a nova seção é
  `Painel/src/pages/Configuracoes.tsx`, que já compõe Cards independentes
  (`CompanyDataCard`, `PasswordChangeCard`) alimentados por um hook único
  (`useConfiguracoesPageData`). `ContaAzulSection` vira mais um Card nesse grid.
- **Backend não usa ORM.** Todo acesso a dados é `psycopg` (psycopg3) raw SQL, camada
  repository/service, migrations Alembic com `op.execute("""SQL""")` — sem SQLAlchemy models,
  sem `Depends(get_db)`. Tabela `public.empresas` já existe e é a FK natural.
- **Celery já existe** (`app/workers/celery_app.py`), com filas nomeadas e um padrão
  estabelecido: rota cria registro + dispara `task.apply_async(..., queue=...)` retornando 202,
  task roda em `app/workers/*_tasks.py` (ver `nfe_tasks.py` / `job_service.py`).
- **Não existe lib de criptografia** no backend hoje (só `PyJWT`). Tokens OAuth2 do Conta Azul
  vão pra Postgres — decisão: cifrar com Fernet (nova dependência `cryptography`, nova env
  `CONTAAZUL_TOKEN_ENCRYPTION_KEY`).

Decisões do usuário: seção entra em `Configuracoes.tsx`; escopo inclui construir o backend
(não só mockar); tabelas em schema dedicado `conta_azul` (não `public.conta_azul_*`); tokens
cifrados com Fernet.

## Escopo

Feature única, implementada em duas fases sequenciais dentro do mesmo plano:

- **Fase A — Backend**: migration, rotas FastAPI, serviço OAuth2 (portado da CLI), Celery task
  de sync, criptografia de token.
- **Fase B — Frontend**: `ContaAzulSection` + hook + api client, plugado em `Configuracoes.tsx`.

O contrato JSON consumido pelo frontend é exatamente o do pedido original (ver seção
"Contrato da API").

## Modelo de dados (nova migration Alembic)

```sql
CREATE SCHEMA IF NOT EXISTS conta_azul;

CREATE TABLE conta_azul.integracoes (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES public.empresas(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE', -- PENDENTE|ATIVA|EXPIRADA|ERRO|DESCONECTADA
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expira_em TIMESTAMPTZ,
    oauth_state VARCHAR(255),          -- nonce CSRF durante handshake; limpo após callback
    oauth_state_expira_em TIMESTAMPTZ,
    erro_mensagem TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id)
);

CREATE TABLE conta_azul.sincronizacoes (
    id BIGSERIAL PRIMARY KEY,
    integracao_id BIGINT NOT NULL REFERENCES conta_azul.integracoes(id) ON DELETE CASCADE,
    run_id UUID NOT NULL,              -- agrupa as 5 linhas de uma mesma execução
    entidade VARCHAR(30) NOT NULL,     -- pessoas|produtos|categorias|vendas|financeiro
    status VARCHAR(20) NOT NULL,       -- EM_PROCESSAMENTO|SUCESSO|SUCESSO_PARCIAL|ERRO
    registros_processados INTEGER,
    erro_mensagem TEXT,
    iniciado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    fim_em TIMESTAMPTZ
);
CREATE INDEX ix_sincronizacoes_integracao_run ON conta_azul.sincronizacoes (integracao_id, run_id);
```

`GET .../sincronizacoes` monta a resposta a partir do `run_id` mais recente por `integracao_id`:
`ultima_sync_em` = `max(fim_em)` do run; `status` geral = pior status entre as linhas do run
(`ERRO` > `SUCESSO_PARCIAL` > `SUCESSO`); `entidades` = as 5 linhas do run. Não há tabela de
"job" separada — as próprias linhas com `status='EM_PROCESSAMENTO'` sinalizam o polling do
frontend.

## Arquitetura backend

Segue convenção do repo (raw psycopg, sem ORM, camadas routes/services/repositories):

```
API/app/api/conta_azul/routes.py
API/app/services/conta_azul/
    auth_service.py     # portado de contaazul-integracao/contaazul/auth.py
    sync_service.py     # orquestra fetch (reaproveita ContaAzulClient) + grava linhas
    crypto_service.py   # Fernet encrypt/decrypt de token
API/app/repositories/conta_azul/
    integracoes_repository.py
    sincronizacoes_repository.py
API/app/workers/conta_azul_tasks.py   # celery task sincronizar_conta_azul_task, fila "conta_azul"
API/app/alembic/versions/<timestamp>_000X_conta_azul_schema.py
```

`app/core/config.py` ganha getters `get_contaazul_client_id()` / `_client_secret()` /
`_redirect_uri()` / `get_contaazul_token_encryption_key()`, no mesmo estilo dos getters
existentes (`os.getenv` + validação em `validate_production_config()`).

O client HTTP (`ContaAzulClient`, paginação, retry, tratamento de erro) e os schemas Pydantic
por entidade (`Cliente`, `Produto`, `Categoria`, `Venda`, `ContaReceber`, `ContaPagar`) são
**reaproveitados diretamente** de `API/contaazul-integracao/contaazul/`, sem reescrever. A
função `_coletar_todas_paginas` (hoje só em `main.py` da CLI) é movida para um módulo
compartilhado (`contaazul/pagination.py`) importável tanto pela CLI quanto pela API.

### Rotas

Todas com `Depends(get_current_user)`, escopo por `current_user.empresa_id` — mesmo padrão de
`nfe`/`jobs`:

| Método | Rota | Ação |
|---|---|---|
| GET | `/api/empresas/{id}/integracoes/conta-azul` | status atual da integração |
| GET | `/api/empresas/{id}/integracoes/conta-azul/auth-url` | gera `auth_url` + grava `oauth_state` pendente |
| GET | `/api/conta-azul/callback` | recebido pelo Conta Azul (fora do prefixo `empresas`, ver fluxo OAuth2) |
| DELETE | `/api/empresas/{id}/integracoes/conta-azul` | desconecta, apaga tokens |
| POST | `/api/empresas/{id}/integracoes/conta-azul/sync` | dispara `sincronizar_conta_azul_task.apply_async`, retorna 202 |
| GET | `/api/empresas/{id}/integracoes/conta-azul/sincronizacoes` | status do último run |

### Fluxo OAuth2

1. `GET auth-url`: gera `state = secrets.token_urlsafe(24)`, upsert em
   `conta_azul.integracoes` (por `empresa_id`) com `status='PENDENTE'`, `oauth_state=state`,
   `oauth_state_expira_em = now() + 10min`. Retorna `{ auth_url }` via
   `ContaAzulAuth.build_authorization_url` (portado, inalterado).
2. Frontend abre `auth_url` em popup (`window.open`).
3. Usuário autoriza no Conta Azul → redirect pro `redirect_uri` fixo:
   `GET /api/conta-azul/callback?code=&state=`.
4. Callback protegido por `Depends(get_current_user)` — o cookie de sessão do browser ainda é
   válido porque o redirect volta pro nosso próprio domínio. Valida `state` contra a linha
   `PENDENTE` de `current_user.empresa_id`, checa expiração. Troca `code` por token
   (`exchange_code_for_token`, portado), cifra com Fernet, grava `status='ATIVA'`,
   `token_expira_em`, limpa `oauth_state`.
5. Callback responde com página HTML mínima:
   `window.opener.postMessage({type:'conta-azul-oauth', status:'success'|'error'}, window.location.origin)`
   seguido de `window.close()`.
6. Frontend escuta `message` no `window`, filtra por `type`, fecha popup se necessário, chama
   `refresh()`.

`refresh_access_token` (portado) roda sob demanda dentro do `sync_service` sempre que
`token_expira_em` já venceu antes de uma sincronização. Se o refresh falhar (refresh token
também expirado), marca integração como `EXPIRADA`.

### Fluxo de sincronização

`POST .../sync`: gera `run_id` novo (`uuid4`), insere 5 linhas `EM_PROCESSAMENTO` em
`sincronizacoes` (pessoas/produtos/categorias/vendas/financeiro), dispara
`sincronizar_conta_azul_task.apply_async(args=[integracao_id, run_id], queue="conta_azul")`,
retorna 202 `{ run_id }` — mesmo padrão de `JobService`/`nfe_tasks`.

Task (`conta_azul_tasks.py`):
- Garante token válido (refresh se preciso).
- Instancia `ContaAzulClient` reaproveitado, autenticado com o token da integração.
- Por entidade, pagina via `_coletar_todas_paginas` (agora compartilhado).
- `financeiro` = soma de `contas_receber` + `contas_pagar`.
- Erro tolerante por entidade (mesmo padrão de `_listar_vendedores_tolerante` na CLI): captura
  `ApiError`, marca a linha daquela entidade como `ERRO` com `erro_mensagem`, segue pras
  próximas entidades. `autoretry_for=(ConnectionError,)`, mesmo padrão de `nfe_tasks`.

Polling do frontend: a cada 3s em `GET sincronizacoes`, até nenhuma entidade estar
`EM_PROCESSAMENTO`, máx 60 tentativas (3 min) — igual ao pedido original.

## Contrato da API (consumido pelo frontend)

```
GET /api/empresas/:id/integracoes/conta-azul
```
Resposta: `{ status: null | "ATIVA" | "EXPIRADA" | "ERRO" | "DESCONECTADA", token_expira_em, erro_mensagem? }`

```
GET /api/empresas/:id/integracoes/conta-azul/sincronizacoes
```
```json
{
  "ultima_sync_em": "2026-07-27T14:32:00Z",
  "status": "ATIVA",
  "token_expira_em": "2026-07-27T15:32:00Z",
  "entidades": [
    { "entidade": "pessoas", "registros_processados": 248, "status": "SUCESSO", "fim_em": "..." },
    { "entidade": "produtos", "registros_processados": 1203, "status": "SUCESSO", "fim_em": "..." },
    { "entidade": "categorias", "registros_processados": 87, "status": "SUCESSO", "fim_em": "..." },
    { "entidade": "vendas", "registros_processados": 3412, "status": "SUCESSO", "fim_em": "..." },
    { "entidade": "financeiro", "registros_processados": 891, "status": "ERRO", "fim_em": "...", "erro": "Rate limit atingido" }
  ]
}
```

Demais rotas (`auth-url`, `sync`, `DELETE`) sem corpo relevante além do já descrito na tabela
de rotas.

## Frontend

Estrutura de arquivos, em TypeScript e usando o que já existe no repo (sem CSS próprio — só
Tailwind, sem lib nova):

```
Painel/src/features/configuracoes/components/ContaAzulSection/
    ContaAzulSection.tsx
    SyncStatusPanel.tsx
    SyncEntidadeRow.tsx
Painel/src/features/configuracoes/hooks/useContaAzulIntegracao.ts
Painel/src/services/contaAzul.api.ts
```

- `Card`/`CardHeader`/`CardTitle`/`CardContent` (mesmo shape de `CompanyDataCard.tsx`).
- `Badge` (variantes `default`/`warning`/`destructive`/`secondary`) para os status
  ATIVA/EXPIRADA/ERRO/DESCONECTADA.
- `Dialog` (shadcn) para o modal de confirmação de desconexão.
- `Loader2` animado (`lucide-react`) como spinner de sync/loading — sem componente `Spinner`
  dedicado no repo, segue o padrão já usado em `CadastroEmpresaPage.tsx`/`Login.tsx`.
- `useToast` para feedback de conectar/desconectar/sincronizar (sucesso e erro).
- `contaAzul.api.ts` usa `apiFetch` (wrapper existente em `services/api.ts`); comentário no
  topo do arquivo documenta os 6 endpoints (método, path, payload esperado).
- `useContaAzulIntegracao.ts` expõe `{ integracao, loading, error, sincronizando, conectar,
  desconectar, sincronizarAgora, refresh }`; cuida do polling (`setInterval`/`clearInterval` no
  cleanup do `useEffect`) e do listener de `postMessage` do popup OAuth2.
- `Configuracoes.tsx`: adiciona `<ContaAzulSection empresaId={empresa.id} />` no grid, ao lado
  de `CompanyDataCard`/`PasswordChangeCard`.
- Sem formulário próprio, sem botão "Salvar" — só ações de integração, conforme pedido
  original. Regras de UI/UX do pedido original (badges por cor, barra de progresso
  proporcional, `toLocaleString('pt-BR')`, datas em `dd/MM/yyyy 'às' HH:mm` fuso São Paulo,
  responsivo a partir de 768px, `aria-label`/`aria-live`/foco no modal) permanecem válidas e
  não mudam.

## Tratamento de erros

- Backend: `ApiError`/`AuthError` da CLI viram HTTP 502/401 com mensagem curta; token cifrado
  nunca aparece em log; erro por entidade fica isolado na linha de `sincronizacoes`
  correspondente, não derruba a task inteira.
- Frontend: hook captura erro de rede/HTTP e expõe mensagem amigável, sem stack trace na UI.
- Token expirando em até 30 min: aviso discreto, sem bloquear a UI (`token_expira_em` vem do
  endpoint de status).

## Testes

- Backend: `pytest` + `respx` (mesmo padrão de `contaazul-integracao/tests/test_client.py`)
  para `auth_service`/`sync_service`; teste de rota com token mockado; nova migration validada
  via `alembic upgrade head`.
- Frontend: testes unitários de `useContaAzulIntegracao.ts` mockando `contaAzul.api.ts` — os 4
  casos do pedido original: estado inicial sem integração, transição para `ATIVA` após
  conectar, comportamento de polling durante sincronização, limpeza do polling no unmount.

## Fora de escopo

- Sync incremental por data (a API do Conta Azul já limita isso em outros endpoints, ver spec
  irmã `2026-07-28-contaazul-produtos-vendedores-itens-design.md` — não assumir suporte sem
  checar o OpenAPI real de cada endpoint usado aqui também, especialmente `financeiro`).
- Qualquer dado fiscal (NCM/CEST/origem) de produto — confirmado inexistente na API do Conta
  Azul pela spec irmã acima.
- Refresh automático em background fora do fluxo de sync (ex: cron dedicado) — não pedido.
