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

## Logs

Os logs estruturados incluem `request_id`, `job_id`, `tipo_job`, `status`, `etapa`, `duracao_ms`, `total_itens`, `itens_processados` e `erro`.

Nao registrar XML completo, SPED completo, tokens, senhas, secrets ou `.env`.

## Erros comuns

- `Redis indisponivel`: verificar `REDIS_URL` e container `redis`.
- `PostgreSQL indisponivel`: verificar `DATABASE_URL`, credenciais e migration.
- `Nenhum XML pendente`: importar XML antes de processar.
- `Nenhum arquivo SPED pendente`: importar SPED antes de processar.
- Job `FAILED`: consultar `erro` em `/api/jobs/{job_id}` e filtrar logs pelo `job_id`.

## Reprocessamento

Ainda nao ha endpoint dedicado de reprocessamento. Hoje o reprocessamento depende de haver arquivos importados com `processado_em IS NULL`.
