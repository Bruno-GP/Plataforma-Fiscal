# Banco de Dados

Este projeto usa PostgreSQL e agora possui Alembic em `API/app/alembic`. A estrutura ainda combina migrations versionadas, scripts SQL legados, DDL defensivo em services e um fallback opcional de schema no startup da API.

## Arquivos de referencia no codigo

- `API/app/file/sql/schema_tables.sql`
- `API/app/file/sql/ncm_catalogo.sql`
- `API/app/file/sql/ncm_tributacao.sql`
- `API/app/file/sql/municipios_catalogo.sql`
- `API/SQL/migrations/001_add_tem_sped.sql` ate `API/SQL/migrations/007_add_sped_processing_columns.sql`
- `API/app/services/db_schema_service.py`
- `API/app/services/nfe/xml_importacao_service.py`
- `API/app/services/sped/sped_importacao_service.py`
- `API/app/services/sped/sped_consulta_service.py`

## Bases usadas

- Banco principal NFe/XML: configurado por `POSTGRES_DB` ou `POSTGRES_DB_NFE`.
- Banco SPED: configurado por `POSTGRES_SPED_DB` ou `POSTGRES_DB_SPED`.
- O codigo trata NFe/XML e SPED como fluxos separados. Confirme em producao se as variaveis realmente apontam para os bancos esperados.

## Fontes de schema

| Local | Uso atual |
| --- | --- |
| `API/app/file/sql/schema_tables.sql` | Schema base do fluxo NFe/XML. |
| `API/app/file/sql/ncm_catalogo.sql` | Estrutura auxiliar de catalogo NCM. |
| `API/app/file/sql/ncm_tributacao.sql` | Estrutura auxiliar de aliquotas IBPT por NCM/UF. |
| `API/app/file/sql/municipios_catalogo.sql` | Catalogo de municipios usado por consultas geograficas e fiscais. |
| `API/app/models/nfe/Tables/FISCAL Schema Tables.sql` | Schema historico do modulo fiscal/NFe. Validar antes de reaplicar. |
| `API/SQL/migrations/*.sql` | Evolucoes manuais numeradas legadas. |
| `API/app/alembic/` | Caminho operacional recomendado para novas migrations versionadas. |
| `API/app/services/db_schema_service.py` | DDL opcional no startup da API para colunas, tabelas auxiliares, indices e Reforma Tributaria. |
| `API/app/services/nfe/xml_importacao_service.py` | Cria/ajusta `notas_xml_importados` sob demanda. |
| `API/app/services/sped/sped_importacao_service.py` | Cria/ajusta tabelas de staging e tabelas analiticas SPED sob demanda. |

## Estruturas criadas no startup

Quando `ENABLE_STARTUP_SCHEMA_ENSURE=true`, `API/app/main.py` chama:

- `ensure_empresas_tem_sped_column`: adiciona `public.empresas.tem_sped`.
- `ensure_ncm_ibpt_tables`: cria `public.ncm_catalogo` e `public.ncm_tributacao`.
- `ensure_municipios_catalogo_table`: cria `public.municipios_catalogo`.
- `ensure_fiscal_analysis_indexes`: cria indices funcionais para analise fiscal NFe/SPED.
- `ensure_reforma_tributaria_base_schema`: aplica `004_add_reforma_tributaria_base.sql`.
- `ensure_reforma_tributaria_documentos_itens_schema`: aplica `005_add_reforma_tributaria_documentos_itens.sql`.
- `ensure_reforma_tributaria_creditos_debitos_memoria_schema`: aplica `006_add_reforma_tributaria_creditos_debitos_memoria.sql`.

Essas chamadas ajudam em desenvolvimento e em bancos legados, mas nao substituem migrations versionadas em producao.

## Tabelas por origem de criacao

### Criadas por scripts SQL

`API/app/file/sql/schema_tables.sql`:

- `empresas`
- `sped_importacoes`
- `participantes`
- `produtos`
- `documentos_fiscais`
- `documento_itens`
- `tributos_itens`
- `resumo_cfop_cst`
- `apuracao_icms`
- `apuracao_ipi`
- `inventario`
- `ajustes_fiscais`
- `kpis_sped_fiscal`

Scripts auxiliares:

- `municipios_catalogo` em `API/app/file/sql/municipios_catalogo.sql`
- `ncm_catalogo` em `API/app/file/sql/ncm_catalogo.sql`
- `ncm_tributacao` em `API/app/file/sql/ncm_tributacao.sql`

### Criadas ou alteradas por migrations manuais

- `001_add_tem_sped.sql`: altera `public.empresas`.
- `002_add_ncm_tributacao.sql`: cria `public.ncm_tributacao`.
- `003_add_fiscal_analysis_indexes.sql`: cria indices em `notas`, `notas_itens`, `sped_documentos_fiscais`, `sped_documento_itens`, `sped_produtos`, `sped_participantes`.
- `004_add_reforma_tributaria_base.sql`: cria `tributos`, `regras_tributarias`, `regras_tributarias_vigencias`, `aliquotas_tributarias`, `apuracao_tributaria`, `ajustes_tributarios`.
- `005_add_reforma_tributaria_documentos_itens.sql`: cria `documentos_fiscais_tributos`, `itens_documentos_fiscais_tributos`.
- `006_add_reforma_tributaria_creditos_debitos_memoria.sql`: cria `creditos_tributarios`, `debitos_tributarios`, `memoria_calculo_tributaria`.
- `007_add_sped_processing_columns.sql`: altera `sped_documentos_fiscais`, `sped_documento_itens`, `sped_kpis_fiscal`.

### Criadas no startup

Com `ENABLE_STARTUP_SCHEMA_ENSURE=true`, o startup executa DDL idempotente em `db_schema_service.py`:

- altera `public.empresas` para garantir `tem_sped`;
- cria `public.ncm_catalogo`;
- cria `public.ncm_tributacao`;
- cria `public.municipios_catalogo`;
- cria indices funcionais de analise fiscal;
- reaplica as estruturas das migrations `004`, `005` e `006`.

Fragilidade: se habilitado em ambiente persistente, o startup pode alterar schema sem um registro formal de migration aplicada.

### Criadas sob demanda por service

- `notas_xml_importados`: criada por `XMLImportacaoService._garantir_tabela`.
- `sped_importados`: criada por `SpedImportacaoService._garantir_tabela`.
- `sped_empresas`, `sped_participantes`, `sped_produtos`, `sped_documentos_fiscais`, `sped_documento_itens`, `sped_kpis_fiscal`, `sped_apuracao_icms`: criadas por `SpedImportacaoService._garantir_tabelas_analiticas`.
- `public.sped_kpis_fiscal`: tambem pode ser criada/ajustada por `SpedConsultaService`.

Fragilidade: tabelas sob demanda podem nao existir em um banco recem-provisionado ate o primeiro uso do fluxo correspondente.

## Checklist de banco pronto

- PostgreSQL acessivel pela API.
- Banco principal criado e com tabelas base de NFe/XML.
- Banco SPED criado quando houver empresas `tem_sped=true`.
- `public.empresas` existe antes do startup tentar adicionar `tem_sped`.
- Migrations `001` a `007` avaliadas e aplicadas na ordem adequada.
- Tabelas de staging (`notas_xml_importados`, `sped_importados`) criadas apos primeiro uso ou validadas manualmente.
- Tabelas da Reforma Tributaria existentes: `tributos`, `apuracao_tributaria`, `documentos_fiscais_tributos`, `itens_documentos_fiscais_tributos`, `creditos_tributarios`, `debitos_tributarios`, `memoria_calculo_tributaria`.
- Catalogos NCM/IBPT e municipios carregados quando as telas dependentes forem usadas.
- Backups testados antes de qualquer DDL em producao.

## Riscos atuais

- Scripts SQL legados nao possuem tabela propria de controle de aplicacao; Alembic deve ser o caminho principal para novas mudancas.
- Parte do schema pode ser criada automaticamente no startup quando o fallback estiver habilitado, dificultando auditoria de quando uma mudanca entrou.
- Scripts SQL estao distribuídos em varios diretorios.
- Reaplicar scripts historicos sem revisao pode conflitar com estruturas ja ajustadas pelo codigo.
- Ambientes podem divergir silenciosamente se uma migration manual for esquecida.

## Recomendacao

Consolidar o uso do Alembic com:

- revisoes numeradas e rastreadas no banco;
- comando unico de upgrade/downgrade;
- separacao clara entre DDL de desenvolvimento e DDL de producao;
- migrations para estruturas hoje criadas em runtime;
- validacao de schema no CI antes de deploy.
