# Processamento de dados

## Decisao tecnica

O parsing fiscal principal continua em Python puro, porque XML/NFe e SPED carregam regras fiscais especificas, validacoes contextuais e tratamento de layout.

Polars foi introduzido apenas como alvo controlado para resumo tabular de registros SPED em `app.domain.sped.reader.resumir_registros_sped_bytes_polars`. O pipeline principal ainda usa a implementacao atual ate benchmarks maiores validarem ganho real.

DuckDB foi adicionado como dependencia preparada para consultas analiticas sobre CSV/Parquet e data lake local, mas nao substitui PostgreSQL operacional.

PostgreSQL permanece como banco transacional: empresas, notas, itens, KPIs, importacoes, jobs e status.

## Quando usar cada tecnologia

- Python puro: XML, regras fiscais, validacoes complexas, compatibilidade com services existentes.
- Polars: filtros, joins, agregacoes e parsing tabular em lote, principalmente SPED.
- DuckDB: consultas SQL sobre arquivos, Parquet, CSV e exploracao analitica intermediaria.
- PostgreSQL: persistencia operacional, integridade, status de jobs e consultas transacionais.
- Parquet: saidas analiticas reproduziveis quando o volume justificar.

## Gargalos mapeados

- `SpedImportacaoService._carregar_sped_em_tabelas`: usa `splitlines()`, loop linha a linha e inserts durante parsing.
- `resumir_registros_sped_bytes`: loop Python simples sobre todas as linhas.
- Endpoints fiscais NFe/SPED tinham `limite=100000`; foram reduzidos para default `1000` e teto `5000`.
- Processamento de importados NFe/SPED rodava dentro do request HTTP; agora retorna job assíncrono.

## Benchmark

```bash
cd API/app
python -m app.benchmarks.sped_summary_benchmark file/EFD_FISCAL_35317121000146_022026.txt
```

O benchmark imprime tempo, pico aproximado de memoria, total de linhas e registros distintos para a implementacao atual e a opcional com Polars.
