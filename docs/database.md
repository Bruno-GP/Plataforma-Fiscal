# Banco de Dados

Este projeto usa PostgreSQL e agora possui Alembic em `API/app/alembic`. A estrutura operacional deve ser criada por migrations versionadas; scripts SQL legados ficam como referencia historica.

## Arquivos de referencia no codigo

- `API/SQL/Tables/FISCAL Schema Tables.sql`
- `API/SQL/Insert/ncm_catalogo.sql`
- `API/SQL/Insert/ncm_tributacao.sql`
- `API/SQL/Insert/municipios_catalogo.sql`
- `API/SQL/migrations/001_add_tem_sped.sql` ate `API/SQL/migrations/008_add_dashboard_performance_indexes.sql`
- `API/app/alembic/versions/20260511_0003_dashboard_performance_indexes.py`
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
| `API/SQL/Tables/FISCAL Schema Tables.sql` | Schema historico do fluxo NFe/XML. Validar antes de reaplicar. |
| `API/SQL/Insert/ncm_catalogo.sql` | Estrutura auxiliar de catalogo NCM. |
| `API/SQL/Insert/ncm_tributacao.sql` | Estrutura auxiliar de aliquotas IBPT por NCM/UF. |
| `API/SQL/Insert/municipios_catalogo.sql` | Catalogo de municipios usado por consultas geograficas e fiscais. |
| `API/app/alembic/versions/20260511_0003_dashboard_performance_indexes.py` | Wrapper Alembic para a migration de indices de dashboard. |
| `API/SQL/migrations/*.sql` | Evolucoes manuais numeradas legadas. |
| `API/app/alembic/` | Caminho operacional recomendado para novas migrations versionadas. |
| `API/app/services/db_schema_service.py` | Helpers legados de DDL. Nao sao chamados no startup da API; manter apenas como referencia ate remocao planejada. |
| `API/app/services/company_profile_service.py` | Valida `public.empresas.tem_sped` antes de consultar o perfil operacional da empresa. |
| `API/app/services/NCM/ibpt_sync_service.py` | Valida `ncm_catalogo` e `ncm_tributacao` antes de sincronizar dados IBPT. |
| `API/app/services/nfe/auth/login_service.py` | Valida as colunas usadas por autenticacao e lockout antes do uso; a evolucao do schema fica em Alembic. |
| `API/app/services/nfe/xml_importacao_service.py` | Valida `notas_xml_importados` antes do uso; a tabela e criada por Alembic. |
| `API/app/services/sped/sped_importacao_service.py` | Valida `sped_importados` e o schema analitico SPED antes do uso; as tabelas sao criadas por Alembic. |
| `API/app/services/sped/sped_consulta_service.py` | Valida `sped_kpis_fiscal` antes de listar KPIs SPED. |

## Startup da API

O startup da API nao executa DDL. `ENABLE_STARTUP_SCHEMA_ENSURE=true` foi descontinuado e faz a API falhar cedo com orientacao para aplicar Alembic.

Use `alembic -c API/app/alembic.ini upgrade head` antes de iniciar API, workers ou jobs.

## Tabelas por origem de criacao

### Criadas por scripts SQL

`API/SQL/Tables/FISCAL Schema Tables.sql`:

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

- `municipios_catalogo` em `API/SQL/Insert/municipios_catalogo.sql`
- `ncm_catalogo` em `API/SQL/Insert/ncm_catalogo.sql`
- `ncm_tributacao` em `API/SQL/Insert/ncm_tributacao.sql`

### Criadas ou alteradas por migrations manuais

- `001_add_tem_sped.sql`: altera `public.empresas`.
- `002_add_ncm_tributacao.sql`: cria `public.ncm_tributacao`.
- `003_add_fiscal_analysis_indexes.sql`: cria indices em `notas`, `notas_itens`, `sped_documentos_fiscais`, `sped_documento_itens`, `sped_produtos`, `sped_participantes`.
- `004_add_reforma_tributaria_base.sql`: cria `tributos`, `regras_tributarias`, `regras_tributarias_vigencias`, `aliquotas_tributarias`, `apuracao_tributaria`, `ajustes_tributarios`.
- `005_add_reforma_tributaria_documentos_itens.sql`: cria `documentos_fiscais_tributos`, `itens_documentos_fiscais_tributos`.
- `006_add_reforma_tributaria_creditos_debitos_memoria.sql`: cria `creditos_tributarios`, `debitos_tributarios`, `memoria_calculo_tributaria`.
- `007_add_sped_processing_columns.sql`: altera `sped_documentos_fiscais`, `sped_documento_itens`, `sped_kpis_fiscal`.
- `008_add_dashboard_performance_indexes.sql`: cria indices de dashboard em `documentos_fiscais_tributos`.
- Alembic `20260515_0004`: adiciona `tentativas_falhas`, `bloqueado_ate` e `ultimo_login_em` em `public.login`.
- Alembic `20260511_0003`: aplica a migration `008_add_dashboard_performance_indexes.sql`.

### Criadas no startup

Nenhuma. O caminho operacional e Alembic.

### Validadas por service

- `notas_xml_importados`: criada pela migration inicial Alembic; `XMLImportacaoService` apenas valida se a tabela e as colunas esperadas existem antes do uso.
- `sped_importados`: criada pela migration inicial Alembic; `SpedImportacaoService` apenas valida se a tabela e as colunas esperadas existem antes do uso.
- `processing_jobs`: criada pela migration inicial Alembic; `JobsRepository` apenas valida se a tabela, colunas e constraint de status existem antes do uso.
- `empresas.tem_sped`: criada pela migration inicial Alembic; `CompanyProfileService` apenas valida se a coluna existe antes do uso.
- `ncm_catalogo` e `ncm_tributacao`: carregadas pelos scripts SQL de referencia e validadas pelo `IBPTSyncService` antes de sincronizar dados.
- `login`: criada pela migration inicial Alembic e complementada pela migration `20260515_0004`; `LoginService` apenas valida as colunas de autenticacao antes do uso.
- `sped_empresas`, `sped_participantes`, `sped_produtos`, `sped_documentos_fiscais`, `sped_documento_itens`, `sped_kpis_fiscal`, `sped_apuracao_icms`: criadas pela migration inicial Alembic; `SpedImportacaoService` valida tabelas, colunas e constraints antes de processar importacoes.
- `public.sped_kpis_fiscal`: `SpedConsultaService` apenas valida se a tabela e as colunas esperadas existem antes de listar KPIs.

As tabelas de staging, jobs, autenticacao, IBPT e analiticas SPED dependem de Alembic e falham cedo se as migrations nao tiverem sido aplicadas.

## Checklist de banco pronto

- PostgreSQL acessivel pela API.
- Banco principal criado e com tabelas base de NFe/XML.
- Banco SPED criado quando houver empresas `tem_sped=true`.
- `public.empresas` existe com `tem_sped`.
- Migrations `001` a `008` avaliadas e aplicadas na ordem adequada.
- Tabelas de staging (`notas_xml_importados`, `sped_importados`), controle de jobs (`processing_jobs`) e colunas de seguranca de login criadas por Alembic.
- Tabelas da Reforma Tributaria existentes: `tributos`, `apuracao_tributaria`, `documentos_fiscais_tributos`, `itens_documentos_fiscais_tributos`, `creditos_tributarios`, `debitos_tributarios`, `memoria_calculo_tributaria`.
- Catalogos NCM/IBPT e municipios criados por Alembic e carregados quando as telas dependentes forem usadas.
- Backups testados antes de qualquer DDL em producao.

## Riscos atuais

- Scripts SQL legados nao possuem tabela propria de controle de aplicacao; Alembic deve ser o caminho principal para novas mudancas.
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
