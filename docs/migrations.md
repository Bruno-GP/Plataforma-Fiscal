# Migrations

Nao existe runner automatizado de migrations no repositorio. Os arquivos em `API/migrations/` devem ser tratados como migrations manuais e revisados antes de execucao.

## Arquivos de referencia no codigo

- `API/migrations/001_add_tem_sped.sql`
- `API/migrations/002_add_ncm_tributacao.sql`
- `API/migrations/003_add_fiscal_analysis_indexes.sql`
- `API/migrations/004_add_reforma_tributaria_base.sql`
- `API/migrations/005_add_reforma_tributaria_documentos_itens.sql`
- `API/migrations/006_add_reforma_tributaria_creditos_debitos_memoria.sql`
- `API/migrations/007_add_sped_processing_columns.sql`
- `API/app/services/db_schema_service.py`
- `API/app/services/nfe/xml_importacao_service.py`
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

## Como aplicar hoje

1. Fazer backup do banco.
2. Confirmar qual banco recebera a migration: principal NFe/XML ou SPED.
3. Ler o SQL inteiro antes de executar.
4. Executar em transacao sempre que possivel.
5. Registrar manualmente data, responsavel, banco e hash do arquivo aplicado.
6. Reiniciar a API e verificar `/health`.
7. Validar endpoints criticos e telas dependentes.

## Pontos de atencao

- As migrations `004`, `005` e `006` tambem sao executadas no startup por `db_schema_service.py`.
- As tabelas `notas_xml_importados` e `sped_importados` nao estao em migrations formais; sao criadas pelos services de importacao.
- As tabelas analiticas SPED tambem sao garantidas no processamento SPED.
- Nao ha rollback documentado. Em producao, rollback deve ser feito por backup/restore ou script especifico revisado.

## Inventario por tipo de criacao

| Tipo | Tabelas/estruturas |
| --- | --- |
| Script SQL base | `empresas`, `sped_importacoes`, `participantes`, `produtos`, `documentos_fiscais`, `documento_itens`, `tributos_itens`, `resumo_cfop_cst`, `apuracao_icms`, `apuracao_ipi`, `inventario`, `ajustes_fiscais`, `kpis_sped_fiscal`. |
| Script SQL auxiliar | `municipios_catalogo`, `ncm_catalogo`, `ncm_tributacao`. |
| Migration manual | `tem_sped` em `empresas`, `ncm_tributacao`, indices fiscais, `tributos`, `regras_tributarias`, `regras_tributarias_vigencias`, `aliquotas_tributarias`, `apuracao_tributaria`, `ajustes_tributarios`, `documentos_fiscais_tributos`, `itens_documentos_fiscais_tributos`, `creditos_tributarios`, `debitos_tributarios`, `memoria_calculo_tributaria`, colunas SPED de processamento. |
| Startup | `tem_sped`, `ncm_catalogo`, `ncm_tributacao`, `municipios_catalogo`, indices fiscais, estruturas das migrations `004` a `006`. |
| Service sob demanda | `notas_xml_importados`, `sped_importados`, `sped_empresas`, `sped_participantes`, `sped_produtos`, `sped_documentos_fiscais`, `sped_documento_itens`, `sped_kpis_fiscal`, `sped_apuracao_icms`. |

## Fragilidades

- Nao existe tabela como `alembic_version`.
- Nao ha comando unico de upgrade.
- Nao ha rollback versionado.
- O mesmo objeto pode ser criado por mais de um caminho (`ncm_tributacao`, estruturas da Reforma, `sped_kpis_fiscal`).
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
