# Troubleshooting de jobs

## Consultar job

```bash
curl http://localhost:8000/api/jobs/{job_id}
```

## Listar jobs

```bash
curl "http://localhost:8000/api/jobs?status=FAILED&limit=20"
curl "http://localhost:8000/api/jobs?tipo=NFE_PROCESSAMENTO_IMPORTADOS"
```

## Metricas

```bash
curl http://localhost:8000/api/jobs/metrics
```

## Healthchecks

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/db
curl http://localhost:8000/health/redis
```

## Reiniciar workers

Com Docker Compose:

```bash
docker compose restart celery-worker-default celery-worker-nfe celery-worker-sped
```

Local:

```bash
cd API
celery -A app.workers.celery_app worker --loglevel=info -Q nfe
celery -A app.workers.celery_app worker --loglevel=info -Q sped
```

Windows com venv local:

```powershell
cd "C:\Users\supor\OneDrive\Área de Trabalho\Github\Plataforma-Fiscal\API"
.\.venv-local\Scripts\celery.exe -A app.workers.celery_app worker --loglevel=info -Q nfe --pool=solo
.\.venv-local\Scripts\celery.exe -A app.workers.celery_app worker --loglevel=info -Q sped --pool=solo
```

O worker esta pronto quando aparecer:

```text
celery@servidor ready.
```

## Redis/Garnet no Windows

Se estiver rodando sem Docker e sem WSL, o Redis pode ser substituido pelo Garnet. Suba o Garnet com Lua habilitado:

```powershell
cd "C:\Users\supor\OneDrive\Área de Trabalho\Garnet\garnet-main"
dotnet run -c Release --project .\main\GarnetServer\GarnetServer.csproj -- --port 6379 --lua
```

Valide a conexao:

```powershell
cd "C:\Users\supor\OneDrive\Área de Trabalho\Github\Plataforma-Fiscal\API"
.\.venv-local\Scripts\python.exe -c "import redis; c=redis.Redis.from_url('redis://localhost:6379/0'); print(c.ping())"
```

O resultado esperado e `True`.

## Logs

Os logs estruturados incluem `request_id`, `job_id`, `tipo_job`, `status`, `etapa`, `duracao_ms`, `total_itens`, `itens_processados` e `erro`.

Nao registrar XML completo, SPED completo, tokens, senhas, secrets ou `.env`.

## Erros comuns

- `Redis indisponivel`: verificar `REDIS_URL` e container `redis`.
- `celery : O termo 'celery' nao e reconhecido`: ativar a venv ou chamar `.\.venv-local\Scripts\celery.exe`.
- `No Python at ... WindowsApps`: a venv esta quebrada; recriar a venv e reinstalar `API/app/requirements.txt`.
- `This instance has Lua scripting support disabled`: o Garnet foi iniciado sem `--lua`; reiniciar com `--port 6379 --lua`.
- `PostgreSQL indisponivel`: verificar `DATABASE_URL`, credenciais e migration.
- `Nenhum XML pendente`: importar XML antes de processar.
- `Nenhum arquivo SPED pendente`: importar SPED antes de processar.
- Job `FAILED`: consultar `erro` em `/api/jobs/{job_id}` e filtrar logs pelo `job_id`.

## Reprocessamento

Ainda nao ha endpoint dedicado de reprocessamento. Hoje o reprocessamento depende de haver arquivos importados com `processado_em IS NULL`.
