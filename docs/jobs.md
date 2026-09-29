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

## Sincronizacao SEFAZ (fora do framework `processing_jobs`)

As tasks `sefaz_sync_diario_task` (Celery beat, 02:00) e `sefaz_sync_empresa_task`
(disparada por `POST /api/sefaz/sync`) **nao** usam `processing_jobs`/`JobsRepository` —
sao `celery_app.send_task` direto na fila `sefaz`, sem `job_id` e sem status
`PENDING/QUEUED/RUNNING/...`. O acompanhamento e via `GET /api/sefaz/sync-log`
(tabela `sefaz.sync_log`, status `sucesso`/`bloqueado`/`erro`). Ver `docs/api-contracts.md`
(secao "Sincronizacao SEFAZ") e `docs/mapeamento-busca-xml-sefaz.md`.

`sefaz_evento_documento_novo_task` (por documento novo) e `sefaz_backfill_fiscal_task`
(ao fim de cada `sefaz_sync_empresa_task`, por empresa) transportam documentos
`direcao='emitida'` para as tabelas Fiscal via `SefazFiscalTransportService` —
tambem best-effort, sem `job_id`/`processing_jobs`. Falha nao derruba o sync;
o documento fica pendente (`sefaz.documentos.processado_fiscal_em IS NULL`) ate
a proxima tentativa. Ver `docs/superpowers/specs/2026-08-18-sefaz-fiscal-transport-design.md`.

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
- `conta_azul`
- `sefaz`

Workers locais:

```bash
cd API
celery -A app.workers.celery_app worker --loglevel=info -Q default
celery -A app.workers.celery_app worker --loglevel=info -Q nfe
celery -A app.workers.celery_app worker --loglevel=info -Q sped
celery -A app.workers.celery_app worker --loglevel=info -Q conta_azul
celery -A app.workers.celery_app worker --loglevel=info -Q sefaz
celery -A app.workers.celery_app beat --loglevel=info
```

Com Docker Compose, os servicos `celery-worker-default`, `celery-worker-nfe`, `celery-worker-sped`, `celery-worker-conta-azul` e `celery-beat` sobem junto com API, Redis e PostgreSQL. **Gap conhecido:** nao ha `celery-worker-sefaz` no `docker-compose.yml` — a fila `sefaz` (tasks `sefaz_sync_diario_task`/`sefaz_sync_empresa_task`) so roda hoje via worker local (`-Q sefaz` acima); em ambiente Docker Compose essas tasks ficam enfileiradas sem consumidor ate isso ser adicionado.

## Tabela de controle

A tabela `processing_jobs` e criada pela migration inicial Alembic. O `JobsRepository` apenas valida a existencia da tabela, das colunas esperadas e da constraint de status antes do uso. Campos principais:

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
