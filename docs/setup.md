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
- `ENABLE_STARTUP_SCHEMA_ENSURE` nao deve ser habilitado; use Alembic para schema.

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

No Windows, se a venv antiga estiver quebrada ou o comando `python` nao estiver no PATH, crie uma venv local com um Python instalado/funcional e use os executaveis pelo caminho completo. Exemplo usado no projeto:

```powershell
cd "C:\Users\supor\OneDrive\Área de Trabalho\Github\Plataforma-Fiscal\API"
.\.venv-local\Scripts\uvicorn.exe app.main:app --reload
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
celery -A app.workers.celery_app worker --loglevel=info -Q conta_azul
celery -A app.workers.celery_app beat --loglevel=info
```

No Windows, use `--pool=solo`:

```powershell
cd "C:\Users\supor\OneDrive\Área de Trabalho\Github\Plataforma-Fiscal\API"
.\.venv-local\Scripts\celery.exe -A app.workers.celery_app worker --loglevel=info -Q nfe --pool=solo
.\.venv-local\Scripts\celery.exe -A app.workers.celery_app worker --loglevel=info -Q sped --pool=solo
.\.venv-local\Scripts\celery.exe -A app.workers.celery_app worker --loglevel=info -Q conta_azul --pool=solo
```

## Redis local no Windows com Garnet

Para rodar sem Docker e sem WSL/Linux, use o Garnet como servidor compativel com Redis. O Celery usa scripts Lua internamente, entao o Garnet precisa subir com `--lua`.

Na pasta do Garnet:

```powershell
cd "C:\Users\supor\OneDrive\Área de Trabalho\Garnet\garnet-main"
dotnet run -c Release --project .\main\GarnetServer\GarnetServer.csproj -- --port 6379 --lua
```

Teste a conexao a partir da API:

```powershell
cd "C:\Users\supor\OneDrive\Área de Trabalho\Github\Plataforma-Fiscal\API"
.\.venv-local\Scripts\python.exe -c "import redis; c=redis.Redis.from_url('redis://localhost:6379/0'); print(c.ping())"
```

Resultado esperado:

```text
True
```

Ordem recomendada para desenvolvimento local no Windows:

1. Garnet com `--lua`
2. Worker Celery da fila usada, por exemplo `nfe`
3. API FastAPI
4. Painel React/Vite

## Migrations

```bash
alembic -c API/app/alembic.ini upgrade head
alembic -c API/app/alembic.ini downgrade -1
alembic -c API/app/alembic.ini revision -m "descricao"
```

O startup da API nao executa DDL. `ENABLE_STARTUP_SCHEMA_ENSURE=true` foi descontinuado e faz a API falhar cedo. Aplique Alembic antes de subir API, workers ou jobs.
