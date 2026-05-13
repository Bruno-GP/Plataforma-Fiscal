# Jobs assincronos

Jobs assincronos dependem de PostgreSQL para persistir `processing_jobs`, Redis como broker/result backend e workers Celery para executar o processamento fora do request HTTP.

## Contrato alterado

Os endpoints abaixo deixam de executar processamento pesado no request:

- `POST /api/nfe/xml/processar-importados`
- `POST /api/sped/processar-importados`

Resposta atual:

```json
{
  "job_id": "00000000-0000-0000-0000-000000000000",
  "status": "QUEUED",
  "message": "Processamento enviado para fila"
}
```

O cliente deve consultar:

- `GET /api/jobs/{job_id}`
- `GET /api/jobs`
- `GET /api/jobs/metrics`

Essas consultas exigem autenticacao. Listagens e metricas sao filtradas pelo CNPJ da sessao autenticada, usando o CNPJ gravado no payload do job. A consulta direta de um job de outra empresa retorna `404`.

Enquanto o job estiver em fila ou execucao, a UI deve mostrar progresso por `total_itens`, `itens_processados`, `mensagem` e `status`.

## Tipos de job

- `NFE_PROCESSAMENTO_IMPORTADOS`: processa XMLs importados em staging para um `cnpj_emitente`.
- `SPED_PROCESSAMENTO_IMPORTADOS`: processa arquivos SPED importados em staging para um `cnpj_emitente`.

## Status

- `PENDING`
- `QUEUED`
- `RUNNING`
- `SUCCESS`
- `FAILED`
- `CANCELED`

## Infraestrutura

Filas configuradas:

- `default`
- `nfe`
- `sped`

Workers locais:

```bash
cd API
celery -A app.workers.celery_app worker --loglevel=info -Q default
celery -A app.workers.celery_app worker --loglevel=info -Q nfe
celery -A app.workers.celery_app worker --loglevel=info -Q sped
```

Com Docker Compose, os servicos `celery-worker-default`, `celery-worker-nfe` e `celery-worker-sped` sobem junto com API, Redis e PostgreSQL.

## Tabela de controle

A tabela `processing_jobs` e criada automaticamente pelo `JobsRepository` se ainda nao existir. Campos principais:

- `id`
- `tipo`
- `status`
- `mensagem`
- `total_itens`
- `itens_processados`
- `erro`
- `criado_em`
- `iniciado_em`
- `finalizado_em`
- `payload`

O schema tambem cria indices por `status`, `tipo` e `criado_em`.
