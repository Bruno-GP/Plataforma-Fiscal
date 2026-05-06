# Setup local

## Variaveis de ambiente

Use `API/app/.env.example` como referencia. Nao versione `.env` real.

Variaveis principais:

- `DATABASE_URL` ou `POSTGRES_DSN`
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `REDIS_URL`
- `OPENAI_API_KEY`
- `APP_ENV` ou `ENVIRONMENT`
- `LOG_LEVEL`
- `ENABLE_STARTUP_SCHEMA_ENSURE=false`

## Subir ambiente completo

```bash
docker compose up --build
```

Servicos expostos:

- API: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## Rodar API local sem Docker

```bash
cd API
python -m venv .venv
.venv/Scripts/activate
pip install -r app/requirements.txt
uvicorn app.main:app --reload
```

## Rodar frontend local

```bash
cd Painel
npm install
npm run dev
```

## Workers Celery

```bash
cd API
celery -A app.workers.celery_app worker --loglevel=info -Q default
celery -A app.workers.celery_app worker --loglevel=info -Q nfe
celery -A app.workers.celery_app worker --loglevel=info -Q sped
```

## Migrations

```bash
alembic -c API/app/alembic.ini upgrade head
alembic -c API/app/alembic.ini downgrade -1
alembic -c API/app/alembic.ini revision -m "descricao"
```

O startup da API nao deve ser o mecanismo principal de DDL. `ENABLE_STARTUP_SCHEMA_ENSURE=true` existe apenas como fallback transitorio para bancos legados.
