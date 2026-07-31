# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repositorio

Duas aplicacoes que operam em conjunto:

- `API/`: backend FastAPI (autenticacao, importacao fiscal XML/SPED, processamento assincrono, consultas analiticas, Reforma Tributaria, integracao Conta Azul).
- `Painel/`: frontend React + Vite (operacao diaria, importacoes, dashboards, relatorios, configuracoes).

Fluxo principal: empresa cadastrada com perfil `tem_sped` (false = fluxo XML/NFe, true = fluxo SPED) -> upload de arquivos para staging -> job assincrono Celery processa e consolida KPIs -> Painel exibe dashboards/analises -> relatorios narrativos opcionais via OpenAI.

**Empresas XML e SPED nunca compartilham fluxo.** Toda rota/service novo que trata dado fiscal deve respeitar esse perfil.

Documentacao operacional completa vive em `docs/` (leia antes de mudancas estruturais): `docs/backend-architecture.md`, `docs/backend-target-structure.md`, `docs/backend-implementation-conventions.md`, `docs/backend-error-handling.md`, `docs/backend-pr-checklist.md`, `docs/database.md`, `docs/migrations.md`, `docs/security.md`, `docs/jobs.md`, `docs/api-contracts.md`, `docs/frontend.md`, `docs/testing.md`.

## Comandos

### Backend (API)

Rodar API local (Windows, venv local do projeto):

```powershell
cd "C:\Users\supor\OneDrive\Área de Trabalho\Github\Plataforma-Fiscal\API"
.\.venv-local\Scripts\uvicorn.exe app.main:app --reload
```

Rodar API local (generico):

```bash
cd API
pip install -r app/requirements.txt
uvicorn app.main:app --reload
```

Migrations (Alembic e o caminho operacional; nunca `ENABLE_STARTUP_SCHEMA_ENSURE=true`, foi descontinuado e falha cedo):

```bash
alembic -c API/app/alembic.ini upgrade head
alembic -c API/app/alembic.ini downgrade -1
alembic -c API/app/alembic.ini revision -m "descricao"
```

Testes backend (suite rapida, sem PostgreSQL/Redis/Celery reais):

```bash
python -m pytest API/app/tests -q
# ou de dentro de API/app
cd API/app && pytest
# Windows com venv local
cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests -q
```

Um unico arquivo:

```bash
python -m pytest API/app/tests/test_jobs.py -q
```

Testes de banco (opcionais, exigem PostgreSQL descartavel com `test`/`teste` no nome do DB — a fixture recusa qualquer outro nome):

```powershell
$env:PLATAFORMA_FISCAL_TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/plataforma_fiscal_test"
cd API
.\.venv-local\Scripts\python.exe -m pytest app/tests -q
```

Workers Celery (filas: `default`, `nfe`, `sped`, `conta_azul`; Windows exige `--pool=solo`):

```bash
cd API
celery -A app.workers.celery_app worker --loglevel=info -Q nfe
celery -A app.workers.celery_app worker --loglevel=info -Q sped
celery -A app.workers.celery_app worker --loglevel=info -Q conta_azul
celery -A app.workers.celery_app beat --loglevel=info
```

Redis local no Windows sem Docker/WSL, via Garnet (precisa `--lua` porque Celery usa Lua):

```powershell
cd "C:\Users\supor\OneDrive\Área de Trabalho\Garnet\garnet-main"
dotnet run -c Release --project .\main\GarnetServer\GarnetServer.csproj -- --port 6379 --lua
```

Ordem local recomendada no Windows: Garnet com `--lua` -> worker Celery da fila usada -> API -> Painel.

Ambiente completo via Docker Compose (sobe Postgres, Redis, migration, reference-seed, API, workers, beat e frontend):

```bash
docker compose up --build
```

### Frontend (Painel)

```bash
cd Painel
npm install
npm run dev          # http://localhost:5173
npm run build         # tsc -b && vite build
npm run lint
npm run preview
npm run test          # vitest (watch)
npm run test:run      # vitest run (CI)
npm run test:coverage
npm run e2e           # playwright
```

Criar `Painel/.env` com `VITE_API_URL=http://localhost:8000` (normalizado automaticamente para `/api`).

### Testes de carga (k6)

Ficam fora da suite rapida, em `k6-tests/`. Nao misturar com pytest/vitest. Scripts npm dedicados: `npm run test:k6:smoke`, `test:k6:load`, `test:k6:stress`, etc (rodar a partir de `Painel/`).

## Arquitetura backend

Camadas em `API/app/` (ver `docs/backend-architecture.md` e `docs/backend-target-structure.md` para o detalhamento completo):

- `api/<dominio>/` — rotas FastAPI finas: le params, valida auth/escopo/perfil, chama service, converte excecao esperada em `HTTPException`, retorna schema. **Nunca** SQL, parsing de XML/SPED ou regra fiscal aqui.
- `services/<dominio>/` — orquestra casos de uso, coordena repositories, controla transacao quando precisa de atomicidade. Nao deve levantar `HTTPException` em codigo novo (legado ainda faz isso e deve ser preservado ate ter teste de caracterizacao).
- `repositories/<dominio>/` — unico lugar com SQL. Recebe `conn`/`cur` quando a transacao e externa. Nunca importa FastAPI nem conhece schema HTTP.
- `domain/<dominio>/` — regras puras e deterministicas (parsing, normalizacao, classificacao fiscal), sem I/O.
- `models/` — schemas Pydantic de contrato HTTP.
- `workers/` — tasks Celery, chamam services (nao repetem regra de rota).

Dominios existentes: `nfe`, `sped`, `reforma_tributaria`, `ncm`, `jobs`, `geo`/`municipios`, `auth`, `conta_azul`, `fiscal` (compartilhado), `shared`.

Regra pratica para PR: se uma rota passa de 30-40 linhas ou um service de ~300 linhas/metodo de ~60 linhas, quebrar em helper/repository/formatter antes de crescer mais. Use `docs/backend-pr-checklist.md` antes de abrir PR de backend.

### Erros HTTP

Mapa de status (`docs/backend-error-handling.md`): `400` entrada/regra invalida, `401` falha de auth, `403` fora de escopo de empresa, `404` recurso ausente, `409` conflito/duplicidade, `422` validacao Pydantic, `502` dependencia externa (OpenAI etc.) falhou, `503` infra indisponivel (banco, fila). Mensagens de erro nunca expoem SQL, connection string, token, stack trace ou dado de outra empresa.

### Escopo multiempresa

Rotas fiscais usam `require_company_scope`, que compara `emitente_cnpj`/`cnpj_emitente`/`cnpj_empresa_origem` da query com o CNPJ do usuario autenticado (divergencia = `403`). Varias rotas de analise NFe ainda resolvem por sessao sem comparar via query (`docs/security.md` lista o risco rota a rota) — ao criar rota nova, sempre exigir e comparar o parametro de empresa.

### Jobs assincronos

`POST /api/nfe/xml/processar-importados` e `POST /api/sped/processar-importados` nao processam no request: retornam `202` com `job_id` (tabela `processing_jobs`). Cliente acompanha via `GET /api/jobs/{job_id}`, `GET /api/jobs`, `GET /api/jobs/metrics`, filtrados pelo CNPJ da sessao. Status possiveis: `PENDING`, `QUEUED`, `RUNNING`, `SUCCESS`, `FAILED`, `CANCELED`.

### Banco de dados

PostgreSQL, dois bancos logicos separados: NFe/XML (`POSTGRES_DB`/`POSTGRES_DB_NFE`) e SPED (`POSTGRES_SPED_DB`/`POSTGRES_DB_SPED`). Schema operacional e criado exclusivamente por Alembic (`API/app/alembic/`) — os SQLs legados em `API/SQL/` sao apenas referencia historica, nao reaplicar sem revisao. O startup da API **nao** executa DDL; rode `alembic upgrade head` antes de subir API/workers. Varios services (`CompanyProfileService`, `XMLImportacaoService`, `SpedImportacaoService`, `JobsRepository`, `IBPTSyncService`, `LoginService`, `SpedConsultaService`) apenas *validam* que tabelas/colunas esperadas existem antes do uso — nao criam nada em runtime.

## Arquitetura frontend (Painel)

Ver `docs/frontend.md` para o guia completo com exemplos. Pontos essenciais:

- Camadas: `pages/` (entry point fino, so distribui props) -> `features/<nome>/hooks/use<Nome>PageData.ts` (unico lugar com logica/estado) -> `services/*.ts` -> `services/api.ts` (`apiFetch`, unico ponto de saida HTTP: injeta `Authorization: Bearer`, `credentials: 'include'`, limpa sessao em `401`). Nunca chamar `fetch` direto nas features.
- Cada feature em `src/features/<nome>/` segue `components/`, `helpers/`, `hooks/`, `types.ts`.
- `services/fiscalSource.ts` (`createFiscalSourceApi(user?.tem_sped)`) unifica chamadas NFe/SPED — usar sempre que uma tela servir os dois perfis, nunca duplicar chamada por perfil.
- `AuthContext` e o unico ponto de acesso a sessao (`user`, `isAuthenticated`, `isReady`, `login`, `register`, `logout`, `refreshSession`). `MainLayout` renderiza `null` enquanto `isReady=false`.
- `utils/workspaceAccess.ts` centraliza `isXmlOnboardingLocked` (trava empresa XML sem import valido) e `getDefaultWorkspaceRoute`.
- Hooks reutilizaveis: `useProcessingJobFlow` (cria/acompanha/cancela job, poll 2.5s, timeout 15min), `usePeriodFilter`, `useFiscalYears`, `useImportFileQueue`.
- Token sensivel fica em cookie HttpOnly; dados em `localStorage` (`auth_session`, `fiscal_operations`, `dashboard_fiscal_years`) sao conveniencia de UI, nao fronteira de seguranca — nunca confiar neles para autorizacao.
- Nova pagina: criar feature completa, registrar rota em `App.tsx` dentro de `MainLayout`, adicionar item em `AppSidebar.tsx`. Checklist completo em `docs/frontend.md`.
- Componentes em `components/ui/` sao Radix/shadcn — nao editar diretamente.

Features com codigo pronto mas desligado (nao assumir que estao ativas): Chat (`ChatWidget` comentado em `MainLayout.tsx`), pagina Atualizacoes (rota comentada em `App.tsx`), item de menu Reforma Tributaria (rota ativa, apenas o link do menu esta comentado).

## Testes — padroes da suite backend

- `conftest.py` cria `TestClient` e sobrescreve `require_company_scope` com usuario anonimo (`cnpj="12345678000190"`, `empresa_id=1`, `tem_sped=False`); para simular SPED, `monkeypatch` o service da rota.
- Testes de rota nao tocam banco/fila reais por padrao — substituir repository/service/task no ponto de uso: `monkeypatch.setattr("app.api.jobs.routes.JobsRepository", FakeJobsRepository)`; em workers, `monkeypatch.setattr("app.workers.nfe_tasks.JobsRepository", Repo)`.
- Fixtures fiscais anonimizadas em `API/app/tests/fixtures/` — nunca usar dado real de cliente/fornecedor/CNPJ real.
- `test_database_schema.py` so roda a parte de integracao com PostgreSQL quando `PLATAFORMA_FISCAL_TEST_DATABASE_URL` aponta para banco com `test`/`teste` no nome (seguranca contra apontar para producao).
- `test_sped_reader.py` compara parser SPED atual com versao `polars`; pulado se `polars` nao instalado.

## Convencoes gerais ao alterar codigo

- Regra de ouro do backend: se uma mudanca exige entender rota + SQL + schema + parsing + regra fiscal no mesmo arquivo, quebrar antes de crescer (`docs/backend-target-structure.md`).
- Preservar contratos HTTP existentes; mudar contrato exige atualizar `docs/api-contracts.md` e testes.
- Commits pequenos e reversiveis; nao mover arquivos so por organizacao sem teste de protecao.
- CNPJ alfanumerico (formato RFB vigente desde 2026-07-31) impacta validacoes de CNPJ espalhadas pelo codigo — ver memoria de projeto `project_cnpj_alfanumerico` antes de mexer em validacao/normalizacao de CNPJ.
