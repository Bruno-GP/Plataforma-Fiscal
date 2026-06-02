# Carga de dados de referencia

Os arquivos em `API/SQL/Insert` sao seeds operacionais para tabelas de referencia.
Eles devem ser aplicados depois das migrations Alembic e antes da API/workers
processarem arquivos fiscais.

## Comando

Na raiz do repositorio:

```bash
python API/scripts/bootstrap_referencias.py
```

Dentro da pasta `API`:

```bash
python scripts/bootstrap_referencias.py
```

O comando carrega, nesta ordem:

- `cfops_insert.sql`
- `municipios_catalogo_insert.sql`
- `ncm_catalogo_insert.sql`

As cargas sao idempotentes: podem ser executadas mais de uma vez sem duplicar
registros.

## Carga parcial

```bash
python API/scripts/bootstrap_referencias.py --arquivo ncm_catalogo_insert.sql
```

O parametro `--arquivo` pode ser repetido para escolher mais de um seed.

## Docker

O `docker-compose.yml` executa o servico `reference-seed` automaticamente apos
`migration` e antes de `api` e workers Celery.

## IBPT

O seed do `ncm_catalogo` carrega a base local inicial. A sincronizacao IBPT
continua separada:

```bash
python API/scripts/sync_ibpt.py --todas-ufs
```

Durante o processamento de XML, quando um NCM da Reforma Tributaria nao existir
no catalogo, a API tenta sincronizar esse NCM pelo IBPT antes de gravar o item.
