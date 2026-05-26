# Fase 0 - Preparacao para Reducao de Debito Tecnico do Backend

Este documento define a base de seguranca para iniciar a reducao de debito tecnico do backend sem mudar comportamento funcional, contratos de API ou fluxo operacional da plataforma.

## Objetivo

Preparar a refatoracao gradual dos modulos fiscais mais criticos, garantindo que as proximas fases sejam feitas com baixo risco de regressao.

A Fase 0 nao altera regra de negocio, SQL, estrutura de banco, endpoints, schemas de resposta nem comportamento dos workers. Ela apenas registra escopo, limites, criterios de aceite e rollback.

## Branch de Trabalho

- Branch: `codex/fase-0-backend-debito-tecnico`
- Base atual: `dev`
- Observacao: existem alteracoes nao relacionadas no frontend antes do inicio desta fase. Elas nao fazem parte deste trabalho e nao devem ser revertidas ou misturadas com a refatoracao do backend.

## Arquivos Criticos Mapeados

| Prioridade | Arquivo | Risco | Motivo principal |
|---|---|---|---|
| P0 | `API/app/services/reforma_tributaria/reforma_tributaria_sync_service.py` | Critico | Sincronizacao fiscal, SQL, XML, apuracao, creditos, debitos e memoria no mesmo service. |
| P0 | `API/app/services/nfe/nfe_consulta_service.py` | Critico | Consulta, dashboards, filtros, SQL, resposta de API e regras analiticas concentradas. |
| P0 | `API/app/services/sped/sped_consulta_service.py` | Critico | Consultas analiticas grandes, SQL temporario, hierarquia fiscal e duplicacao com NFe. |
| P0 | `API/app/services/sped/sped_importacao_service.py` | Critico | Upload, staging, parsing, carga analitica, KPIs e pos-processamento misturados. |
| P1 | `API/app/api/nfe/routes.py` | Alto | Rotas com regra de dashboard, paginacao, conexao direta e montagem de resposta. |
| P1 | `API/app/api/sped/routes.py` | Alto | Duplicacao com NFe e regra de negocio em camada HTTP. |
| P1 | `API/app/services/nfe/nfe_notas_service.py` | Alto | Persistencia, filtro fiscal, consulta e montagem de modelos no mesmo service. |
| P1 | `API/app/services/nfe/nfe_itens_service.py` | Alto | Itens NFe acoplados a NCM e Reforma Tributaria. |
| P1 | `API/app/services/nfe/auth/login_service.py` | Alto | Auth, empresa, senha, cache, SQL e validacao de schema misturados. |
| P1 | `API/app/services/db_schema_service.py` | Alto | DDL e garantia de schema em runtime, paralela ao Alembic. |

## Endpoints Protegidos

Estes endpoints devem preservar contrato, status HTTP, filtros, campos de resposta e comportamento de erro durante as proximas fases.

### Autenticacao

- `POST /api/auth/registrar`
- `POST /api/auth/entrar`
- `GET /api/auth/sessao`
- `POST /api/auth/sair`

### Importacao e processamento NFe/XML

- `POST /api/nfe/processar`
- `POST /api/nfe/xml/importar`
- `GET /api/nfe/xml/pendencias`
- `POST /api/nfe/xml/processar-importados`

### Consultas NFe

- `GET /api/nfe/kpis`
- `GET /api/nfe/analise/compras`
- `GET /api/nfe/analise/vendas`
- `GET /api/nfe/analise/fiscal/cfop`
- `GET /api/nfe/analise/fiscal/ncm`
- `GET /api/nfe/analise/fiscal/hierarquia`
- `GET /api/nfe/analise/compras/dashboard`
- `GET /api/nfe/analise/vendas/dashboard`
- `GET /api/nfe/analise/clientes`
- `GET /api/nfe/kpis/comparativo`
- `GET /api/nfe/kpis/comparativo/atual`
- `GET /api/nfe/notas`
- `GET /api/nfe/notas/detalhado`

### Importacao e processamento SPED

- `POST /api/sped/processar`
- `POST /api/sped/importar`
- `GET /api/sped/pendencias`
- `POST /api/sped/processar-importados`

### Consultas SPED

- `GET /api/sped/clientes`
- `GET /api/sped/analise/compras`
- `GET /api/sped/analise/vendas`
- `GET /api/sped/analise/fiscal/cfop`
- `GET /api/sped/analise/fiscal/ncm`
- `GET /api/sped/analise/fiscal/hierarquia`
- `GET /api/sped/analise/compras/dashboard`
- `GET /api/sped/analise/vendas/dashboard`
- `GET /api/sped/analise/clientes`
- `GET /api/sped/kpis`

### Reforma Tributaria

- `GET /api/reforma-tributaria/tributos`
- `POST /api/reforma-tributaria/backfill`
- `GET /api/reforma-tributaria/apuracao`
- `GET /api/reforma-tributaria/documentos/{origem_documento}/{documento_id}/tributos`
- `GET /api/reforma-tributaria/itens/{origem_item}/{item_id}/tributos`
- `GET /api/reforma-tributaria/memoria-calculo`

### Jobs

- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/metrics`

## Fluxos Criticos

| Fluxo | Deve permanecer igual |
|---|---|
| Login e sessao | Contratos de auth, cookie/token, erros 401/403/503 e escopo de empresa. |
| Upload XML | Validacao de extensao, tamanho, CNPJ, duplicidade, staging e mensagens por arquivo. |
| Processamento XML importado | Criacao de job, retorno 202, atualizacao de notas, itens, KPIs e Reforma Tributaria. |
| Upload SPED | Validacao de TXT, registro `0000`, CNPJ, duplicidade e staging. |
| Processamento SPED importado | Criacao de job, carga de participantes, produtos, documentos, itens, KPIs, apuracao ICMS e sync fiscal. |
| Dashboards NFe/SPED | Periodo padrao, periodo anterior, serie mensal, rankings e tributos complementares. |
| Analise fiscal CFOP/NCM | Filtros, totais, rankings, descricao de referencia e fallback para codigo desconhecido. |
| Hierarquia fiscal | Filtros por estado, cidade, NCM, produto, paginacao e calculo de imposto/faturamento. |
| Reforma Tributaria | Backfill, apuracao, documentos, itens, memoria e filtros por periodo/tributo. |
| Jobs | Escopo por CNPJ, status, metricas, listagem, consulta individual e ocultacao de job de outra empresa. |

## Regras de Seguranca para as Proximas Fases

- Nao alterar contrato publico de API durante refatoracao.
- Nao alterar schema de banco junto com mudanca estrutural de codigo, salvo em tarefa isolada.
- Nao trocar tecnologia de persistencia ou framework nesta frente.
- Nao mover regra fiscal sem teste de caracterizacao do comportamento atual.
- Nao remover metodo publico antigo ate os consumidores estarem migrados.
- Manter fachadas temporarias quando quebrar services grandes.
- Preservar mensagens de erro relevantes para o frontend.
- Manter acesso multiempresa e `require_company_scope` como requisito inegociavel.
- Evitar mudar performance de queries criticas sem medicao antes/depois.
- Separar refatoracao pura de nova funcionalidade.

## Criterios de Aceite da Fase 0

- Branch de trabalho criada.
- Arquivos P0/P1 documentados.
- Endpoints protegidos listados.
- Fluxos criticos definidos.
- Criterios de seguranca registrados.
- Plano de rollback definido.
- Nenhum arquivo de codigo alterado.
- Nenhuma regra de negocio alterada.

## Estrategia de Rollback

Como a Fase 0 altera apenas documentacao, o rollback e simples:

1. Reverter apenas este documento, se necessario.
2. Manter intactas as alteracoes nao relacionadas ja existentes no frontend.
3. Nao usar `git reset --hard`.
4. Em fases futuras, cada extracao deve ser pequena o suficiente para ser revertida por commit sem afetar outras frentes.

## Proxima Fase

A Fase 1 deve criar testes de caracterizacao antes de mover qualquer responsabilidade dos arquivos criticos. A ordem recomendada e:

1. Contratos HTTP de NFe/SPED e jobs.
2. Dashboards e KPIs.
3. Analises fiscais CFOP/NCM.
4. Hierarquia fiscal.
5. Importacao XML/SPED.
6. Reforma Tributaria e backfill.

## Progresso da Fase 1

Protecoes ja adicionadas:

- Contratos HTTP de dashboards NFe/SPED.
- Contratos HTTP de hierarquia fiscal NFe/SPED.
- Contratos HTTP de consultas da Reforma Tributaria.
- Contrato de backfill da Reforma Tributaria.
- Contratos de upload XML/SPED para sucesso, perfil fiscal incorreto, extensao invalida, limite e resumo parcial.
- Contratos de pendencias XML/SPED.
- Contratos de processamento de importados sem pendencias.
- Contratos de autenticacao: cadastro, login, sessao, logout, erros de validacao e indisponibilidade de banco.
- Contratos de erro em rotas analiticas NFe/SPED: `ValueError` como 400 e falhas inesperadas como 502 nos fluxos com relatorio/analise.
- Helpers sem banco dos services criticos: normalizacao/parsing SPED, filtros de vendas NFe, filtro de CFOP de venda e truncamento de texto de itens NFe.
- Comportamento atual registrado: `_normalizar_cnpj_filtro` em `NFeConsultaService` rejeita CNPJ zerado, mas nao valida tamanho quando chamado diretamente.
- Helpers da Reforma Tributaria: parsing XML, busca por nome local, normalizacao de numero NF e coleta de resumo por periodo com cursor fake.
- Builders fiscais compartilhados: limite SQL, regiao por UF e construcao do `CASE` de categoria fiscal.
- Contratos de comparativo de KPIs NFe: periodo anterior padrao, virada janeiro/dezembro, modo automatico e retorno 404 sem KPIs.
- Contratos de consulta detalhada NFe: rota ainda nao implementada, periodo default, paginacao, tributos por item, descricao NCM, filtro de tipo de operacao e erro de banco como 503.
- Workers NFe/SPED: falha quando NFe nao consolida, falha quando SPED nao retorna IDs processados, sem marcar staging como processado em cenarios de erro.

Comando de verificacao usado:

```powershell
.\API\.venv-local\Scripts\python.exe -m pytest API/app/tests -q
```

Resultado atual:

- 160 testes passaram.
- 5 testes foram pulados por condicoes opcionais ja previstas na suite.
- 3 warnings conhecidos de dependencias/deprecacoes.

Status da Fase 1: concluida para a suite rapida e deterministica.

Lacunas intencionais deixadas para suites de integracao:

- Validacao fim a fim com PostgreSQL real usando `PLATAFORMA_FISCAL_TEST_DATABASE_URL`.
- Execucao real com Redis/Celery.
- Carga/performance com k6.
- Validacao legal/fiscal completa de CBS, IBS, IBS_UF, IBS_MUN e IS.

Criterio para iniciar a Fase 2:

- Manter os 160 testes rapidos passando antes e depois de cada extracao.
- Fazer extracoes pequenas, preferencialmente uma responsabilidade por commit.
- Preservar os contratos HTTP protegidos nesta fase.
- Nao alterar schema ou regra fiscal junto com a criacao de repositories/use cases.

## Referencias Existentes

- `docs/api-contracts.md`
- `docs/testing.md`
- `docs/importacao-processamento.md`
- `docs/reforma-tributaria.md`
- `docs/database.md`
- `docs/jobs.md`
