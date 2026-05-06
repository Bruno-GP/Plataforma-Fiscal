# Jobs assíncronos

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

## Status

- `PENDING`
- `QUEUED`
- `RUNNING`
- `SUCCESS`
- `FAILED`
- `CANCELED`
