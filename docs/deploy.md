# Deploy

## Arquivos de referencia no codigo

- `API/app/main.py`
- `API/app/core/config.py`
- `API/app/requirements.txt`
- `API/app/workers/celery_app.py`
- `API/app/workers/nfe_tasks.py`
- `API/app/workers/sped_tasks.py`
- `docker-compose.yml`
- `Painel/package.json`
- `Painel/vercel.json`
- `Painel/src/services/api.ts`
- `docs/migrations.md`
- `docs/production-checklist.md`

## Ambiente local completo

Com Docker Compose:

```bash
docker compose up --build
```

Servicos principais:

- API: `http://localhost:8000`
- Painel: `http://localhost:5173`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- Workers: `celery-worker-default`, `celery-worker-nfe`, `celery-worker-sped`

## Ambiente local manual

API:

```bash
pip install -r API/app/requirements.txt
cd API
python -m uvicorn app.main:app --reload
```

Painel:

```bash
cd Painel
npm install
npm run dev
```

## Variaveis principais

API (`API/app/.env` ou ambiente da plataforma):

- `APP_ENV`;
- `AUTH_SECRET_KEY`;
- `AUTH_TOKEN_EXPIRE_MINUTES`;
- `AUTH_COOKIE_NAME`, `AUTH_COOKIE_DOMAIN`, `AUTH_COOKIE_SAMESITE`, `AUTH_COOKIE_SECURE`;
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`;
- `DATABASE_URL`, `POSTGRES_DSN`, `POSTGRES_NFE_DSN`, `POSTGRES_SPED_DSN`;
- `REDIS_URL`, `CELERY_RESULT_BACKEND`;
- `ENABLE_STARTUP_SCHEMA_ENSURE`;
- `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, `CORS_ALLOW_ORIGIN_REGEX`;
- `OPENAI_API_KEY`, `OPENAI_REPORT_MODEL`;
- `UPLOAD_MAX_XML_BYTES`, `UPLOAD_MAX_TXT_BYTES`, `UPLOAD_MAX_TOTAL_BYTES`.

Painel:

- `VITE_API_URL`.

## Build do frontend

```bash
cd Painel
npm run build
```

O build gera `Painel/dist`.

## Execucao da API em producao

Use servidor ASGI com processo gerenciado pela plataforma. Exemplo conceitual:

```bash
cd API
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Antes de expor, aplique migrations, configure CORS restrito e confirme que `/health` responde.

## Workers em producao

Os processamentos de importados XML/NFe e SPED dependem de Redis e Celery. Rode workers separados por fila para isolar carga:

```bash
cd API
celery -A app.workers.celery_app worker --loglevel=info -Q default
celery -A app.workers.celery_app worker --loglevel=info -Q nfe
celery -A app.workers.celery_app worker --loglevel=info -Q sped
```

Em plataformas gerenciadas, configure API e workers como processos separados usando o mesmo pacote, o mesmo `.env`, o mesmo `DATABASE_URL`/`POSTGRES_DSN` e o mesmo `REDIS_URL`.

## Ordem operacional recomendada

1. Backup: fazer snapshot dos bancos NFe/XML e SPED, e testar acesso ao arquivo de backup.
2. Congelamento: pausar importacoes/processamentos durante a janela de deploy.
3. Migrations: aplicar scripts revisados na ordem definida em `docs/migrations.md`.
4. Validacao de schema: confirmar tabelas/colunas criticas e registrar evidencias.
5. Deploy API: publicar nova versao do backend com variaveis de ambiente revisadas.
6. Deploy workers: publicar workers Celery nas filas `default`, `nfe` e `sped`.
7. Health check API: validar `GET /health`, `GET /health/db`, `GET /health/redis` e uma chamada autenticada simples (`/api/auth/sessao`).
8. Deploy Painel: publicar build do frontend apontando `VITE_API_URL` para a API correta.
9. Smoke tests: login, importacao controlada XML ou SPED, pendencias, criacao de job, consulta em `/api/jobs/{job_id}`, dashboard, Reforma Tributaria.
10. Logs: verificar erros de startup, CORS, banco, Redis, workers, upload rejeitado e `403` multiempresa.
11. Liberacao: reabrir operacao normal.
12. Rollback: se smoke tests falharem, voltar codigo e avaliar restore de banco conforme tipo da falha.

## Health check

- API: `GET /health` retorna `{ "status": "ok" }`.
- Banco: `GET /health/db` retorna `{ "status": "ok" }`.
- Redis: `GET /health/redis` retorna `{ "status": "ok" }`.
- Painel: validar carregamento da tela de login e chamada a `/api/auth/sessao`.

## Rollback

Codigo:

- reimplantar versao anterior da API/Painel;
- manter variaveis compativeis.

Banco:

- nao ha rollback automatico de migrations;
- usar backup/restore ou script de reversao revisado;
- nunca executar rollback destrutivo sem snapshot validado.
- se a migration ja alterou dados fiscais, nao tratar rollback como simples redeploy de codigo.

## Backup e restore

- Backup antes de DDL e deploy de processamento fiscal.
- Teste periodico de restore.
- Separar backup do banco NFe/XML e SPED se forem bancos distintos.
- Proteger backups como dados fiscais sensiveis.
