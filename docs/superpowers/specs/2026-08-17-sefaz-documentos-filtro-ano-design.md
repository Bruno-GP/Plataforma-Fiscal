# SEFAZ documentos — filtro por ano

## Contexto

`GET /api/sefaz/documentos` ja suporta `data_inicio`/`data_fim` (repositorio `DocumentosRepository.listar`). A sincronizacao (`SefazDistribuicaoService.sincronizar_empresa`) ja persiste documentos nas duas direcoes (`emitida` e `recebida`, via `calcular_direcao`), sem descartar nada por data. O pedido original ("pegar as notas emitidas e contra o cnpj dentro do ano de 2026 quando sincronizar") foi refinado em brainstorming: nao ha mudanca na sincronizacao/persistencia -- o ajuste e um atalho de consulta por ano na rota existente.

## Objetivo

Adicionar parametro `ano` em `GET /api/sefaz/documentos` como atalho para `data_inicio=01/01/ano` e `data_fim=31/12/ano`, cobrindo emitida+recebida automaticamente (parametro `direcao` continua opcional e independente).

## Fora de escopo

- Sincronizacao (`SefazDistribuicaoService`) nao muda -- continua gravando tudo, sem filtro de ano.
- Sem migration, sem mudanca de schema em `sefaz.documentos`.
- Sem mudanca no frontend (Painel) nesta iteracao.

## Design

### 1. Helper de dominio (novo arquivo)

`app/domain/sefaz/periodo.py`:

```python
from __future__ import annotations

from datetime import date


def intervalo_do_ano(ano: int) -> tuple[date, date]:
    return date(ano, 1, 1), date(ano, 12, 31)
```

Puro, sem I/O, testavel isoladamente.

### 2. Rota `app/api/sefaz/routes.py::listar_documentos`

- Novo param: `ano: int | None = Query(default=None, ge=2000, le=2100)`.
- Se `ano` vier junto com `data_inicio` ou `data_fim`: `HTTPException(400)` -- combinacao ambigua (`docs/backend-error-handling.md`: 400 = entrada/regra invalida).
- Se so `ano`: computa `data_inicio, data_fim = intervalo_do_ano(ano)` e repassa pro repository, sem alterar `DocumentosRepository.listar` (assinatura ja aceita esses dois params).

### 3. Testes

- `app/tests/test_sefaz_routes.py`: `GET /sefaz/documentos?ano=2026` -> repo recebe `data_inicio=date(2026,1,1)`, `data_fim=date(2026,12,31)`. `GET ...?ano=2026&data_inicio=2026-01-01` -> 400.
- Novo teste unitario para `intervalo_do_ano`.

## Erros e validacao

- `ano` fora de `[2000, 2100]`: `422` (validacao Pydantic/Query nativa do FastAPI, ja no padrao do projeto).
- `ano` + `data_inicio`/`data_fim` juntos: `400` explicito na rota.
