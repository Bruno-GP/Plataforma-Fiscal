# Migrations

O projeto agora possui Alembic em `API/app/alembic`.

Os SQLs legados em `API/SQL/migrations/` continuam como referencia historica, mas o caminho operacional recomendado e Alembic.

## Comandos

Da raiz do repositorio, no Windows com a venv local do projeto:

```powershell
.\API\.venv-local\Scripts\python.exe -m alembic -c .\alembic.ini upgrade head
```

Comandos genericos:

```bash
alembic -c API/app/alembic.ini upgrade head
alembic -c API/app/alembic.ini downgrade -1
alembic -c API/app/alembic.ini revision -m "descricao"
```

Em Docker Compose, o servico `migration` roda `upgrade head` antes da API e dos workers.

## Arquivos de referencia no codigo

- `API/SQL/migrations/001_add_tem_sped.sql`
- `API/SQL/migrations/002_add_ncm_tributacao.sql`
- `API/SQL/migrations/003_add_fiscal_analysis_indexes.sql`
- `API/SQL/migrations/004_add_reforma_tributaria_base.sql`
- `API/SQL/migrations/005_add_reforma_tributaria_documentos_itens.sql`
- `API/SQL/migrations/006_add_reforma_tributaria_creditos_debitos_memoria.sql`
- `API/SQL/migrations/007_add_sped_processing_columns.sql`
- `API/SQL/migrations/008_add_dashboard_performance_indexes.sql`
- `API/app/services/db_schema_service.py`
- `API/app/services/company_profile_service.py`
- `API/app/services/NCM/ibpt_sync_service.py`
- `API/app/services/nfe/auth/login_service.py`
- `API/app/services/nfe/xml_importacao_service.py`
- `API/app/services/sped/sped_consulta_service.py`
- `API/app/services/sped/sped_importacao_service.py`

## Ordem recomendada

| Ordem | Arquivo | Finalidade |
| --- | --- | --- |
| 1 | `001_add_tem_sped.sql` | Adiciona o perfil operacional XML/SPED da empresa. |
| 2 | `002_add_ncm_tributacao.sql` | Adiciona estruturas de tributacao NCM/IBPT. |
| 3 | `003_add_fiscal_analysis_indexes.sql` | Indices para consultas analiticas fiscais. |
| 4 | `004_add_reforma_tributaria_base.sql` | Tributos, regras, vigencias, aliquotas, apuracao e ajustes. |
| 5 | `005_add_reforma_tributaria_documentos_itens.sql` | Tributos vinculados a documentos e itens fiscais. |
| 6 | `006_add_reforma_tributaria_creditos_debitos_memoria.sql` | Creditos, debitos e memoria de calculo. |
| 7 | `007_add_sped_processing_columns.sql` | Colunas auxiliares do processamento SPED. |
| 8 | `008_add_dashboard_performance_indexes.sql` | Indices de dashboard para `documentos_fiscais_tributos`. |

## Como aplicar hoje

1. Fazer backup do banco.
2. Confirmar qual banco recebera a migration: principal NFe/XML ou SPED.
3. Ler o SQL inteiro antes de executar.
4. Executar em transacao sempre que possivel.
5. Registrar manualmente data, responsavel, banco e hash do arquivo aplicado.
6. Reiniciar a API e verificar `/health`.
7. Validar endpoints criticos e telas dependentes.

## Pontos de atencao

- O startup nao executa DDL. `ENABLE_STARTUP_SCHEMA_ENSURE=true` foi descontinuado e falha cedo com orientacao para aplicar Alembic.
- `notas_xml_importados`, `sped_importados` e `processing_jobs` estao na migration inicial.
- As colunas de seguranca de `public.login` (`tentativas_falhas`, `bloqueado_ate`, `ultimo_login_em`) estao na revision Alembic `20260515_0004`.
- `008_add_dashboard_performance_indexes.sql` foi aplicada pela revision Alembic `20260511_0003`.
- Services de importacao XML/SPED validam as tabelas de staging antes do uso, mas nao criam/alteram essas tabelas em runtime.
- `CompanyProfileService` valida `public.empresas.tem_sped` antes do uso, mas nao cria/altera `public.empresas` em runtime.
- `IBPTSyncService` valida `ncm_catalogo` e `ncm_tributacao` antes da sincronizacao, mas nao cria/altera essas tabelas em runtime.
- `JobsRepository` valida `processing_jobs` antes do uso, mas nao cria/altera essa tabela em runtime.
- `LoginService` valida as colunas de autenticacao antes do uso, mas nao cria/altera `public.login` em runtime.
- `SpedConsultaService` valida `sped_kpis_fiscal` antes de listar KPIs, mas nao cria/altera essa tabela em runtime.
- `SpedImportacaoService` valida staging e tabelas analiticas SPED antes do uso, mas nao cria/altera essas tabelas em runtime.
- Os helpers legados em `db_schema_service.py` nao sao chamados no startup e devem ser removidos em uma limpeza futura.
- Downgrade destrutivo amplo nao foi automatizado por seguranca; rollback de producao deve usar backup/restore planejado.

## Inventario por tipo de criacao

| Tipo | Tabelas/estruturas |
| --- | --- |
| Script SQL base | `empresas`, `sped_importacoes`, `participantes`, `produtos`, `documentos_fiscais`, `documento_itens`, `tributos_itens`, `resumo_cfop_cst`, `apuracao_icms`, `apuracao_ipi`, `inventario`, `ajustes_fiscais`, `kpis_sped_fiscal`. |
| Script SQL auxiliar | `municipios_catalogo`, `ncm_catalogo`, `ncm_tributacao`. |
| Migration manual/Alembic | `tem_sped` em `empresas`, `ncm_tributacao`, indices fiscais, `documentos_fiscais_tributos` de dashboard, `tributos`, `regras_tributarias`, `regras_tributarias_vigencias`, `aliquotas_tributarias`, `apuracao_tributaria`, `ajustes_tributarios`, `documentos_fiscais_tributos`, `itens_documentos_fiscais_tributos`, `creditos_tributarios`, `debitos_tributarios`, `memoria_calculo_tributaria`, colunas SPED de processamento, colunas de seguranca de `login`. |
| Startup | Nenhuma estrutura. A API exige schema aplicado previamente por Alembic. |
| Service sob demanda | Nenhuma estrutura operacional recomendada. Services validam schema e falham cedo quando Alembic nao foi aplicado. |

## Fragilidades

- Ainda ha helpers legados de DDL em `db_schema_service.py`, mantidos temporariamente como referencia historica.
- O mesmo objeto ainda aparece em scripts SQL legados e em Alembic; o caminho operacional recomendado e Alembic.
- Um ambiente pode parecer saudavel no `/health` e ainda assim nao ter todas as tabelas necessarias para um fluxo fiscal especifico.

## Validacao minima pos-migration

```sql
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'empresas' AND column_name = 'tem_sped';

SELECT codigo, nome FROM public.tributos ORDER BY codigo;

SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'apuracao_tributaria',
    'documentos_fiscais_tributos',
    'itens_documentos_fiscais_tributos',
    'creditos_tributarios',
    'debitos_tributarios',
    'memoria_calculo_tributaria'
  );
```
