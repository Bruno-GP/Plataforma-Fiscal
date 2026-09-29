# Checklist de PR Backend

Use este checklist antes de abrir ou aprovar qualquer PR que altere backend. O objetivo e impedir que novas funcionalidades aumentem acoplamento, SQL espalhado, rotas gordas e services com responsabilidades misturadas.

## Escopo

- O PR tem objetivo unico e claro?
- A descricao informa quais fluxos foram alterados?
- O PR segue as convencoes de `docs/backend-implementation-conventions.md`?
- Refatoracoes P0/P1 seguem `docs/backend-refactoring-roadmap.md`?
- Mudancas de regra fiscal estao separadas de refatoracoes estruturais?
- Mudancas de schema/migration estao separadas de mudancas de comportamento sempre que possivel?
- Arquivos fora do escopo ficaram intactos?

## Rotas

- A rota apenas recebe parametros, valida contexto e chama service/use case?
- A rota esta sem SQL ou acesso direto a `psycopg.connect`?
- A rota esta sem parsing de XML/SPED?
- A rota nao monta dashboard ou response complexo manualmente quando isso pode ficar em service/formatter?
- A rota converte erros esperados conforme `docs/backend-error-handling.md`?
- A rota usa `response_model` adequado?
- A rota fiscal usa `require_company_scope` ou mecanismo equivalente?
- Se a rota e de catalogo global, isso esta explicitado e nao depende de CNPJ na URL?
- A rota valida perfil operacional XML/SPED quando aplicavel?

## Services

- O service alterado continua com responsabilidade principal clara?
- O metodo novo tem tamanho razoavel e e testavel?
- O service nao mistura regra fiscal, SQL, parsing e schema HTTP no mesmo metodo?
- O service chama repositories para consultas novas?
- O service preserva assinaturas publicas usadas por rotas, jobs e workers?
- Fluxos transacionais continuam explicitos?
- Nao houve criacao de dependencia circular entre services?

## Repositories

- Toda nova consulta SQL ficou em repository ou modulo de infraestrutura equivalente?
- O repository nao importa FastAPI nem levanta `HTTPException`?
- O repository nao retorna schema HTTP/Pydantic de resposta?
- Queries reutilizaveis nao foram duplicadas em outro service?
- Operacoes que precisam da mesma transacao recebem `conn` ou `cur` do chamador?
- Operacoes independentes abrem conexao de forma controlada e testavel?

## Dominio, Helpers e Formatadores

- Regras puras foram extraidas para funcoes testaveis?
- Transformacoes de dados ficaram fora de repositories?
- Formatacao de resposta ficou fora de queries SQL?
- Validadores compartilhados foram reaproveitados antes de criar validacao local?
- Duplicacao entre NFe, SPED e Reforma Tributaria foi verificada?

## Banco e Migrations

- Alteracao de schema tem migration versionada?
- A migration e idempotente ou segura para o fluxo operacional previsto?
- O codigo nao cria/ajusta schema em runtime sem necessidade?
- Consultas novas usam tabelas/colunas existentes em Alembic?
- Indices necessarios foram avaliados para filtros por CNPJ, periodo e origem?
- Nao ha SQL com interpolacao insegura de parametros externos?

## Testes

- Existe teste do fluxo principal?
- Existe teste do erro esperado mais importante?
- Erros novos ou alterados tem teste de status HTTP e mensagem relevante?
- Contratos HTTP foram protegidos quando rota mudou?
- Helpers puros novos tem teste direto?
- Repositories novos tem teste de parametros/resultado ou teste de integracao com banco descartavel?
- Jobs/workers afetados tem teste de sucesso e falha?
- A suite rapida passou?

Comando minimo:

```powershell
.\API\.venv-local\Scripts\python.exe -m pytest API/app/tests -q
```

## Seguranca

- CNPJ/empresa continuam respeitando escopo do usuario?
- Rotas globais foram revisadas quanto a permissao necessaria?
- Uploads continuam usando validadores de seguranca?
- Dados enviados para IA continuam agregados e intencionais?
- Erros nao expõem credenciais, SQL sensivel ou dados fiscais desnecessarios?
- Mensagens de erro seguem o padrao seguro de `docs/backend-error-handling.md`?

## Compatibilidade

- O contrato da API usado pelo Painel foi preservado?
- Campos existentes nao mudaram de nome/tipo sem plano de migracao?
- Jobs pendentes ou dados em staging continuam processaveis?
- Backfills e importacoes antigas continuam funcionando?
- Mudancas em resposta foram refletidas em `docs/api-contracts.md` quando necessario?

## Sinais de Bloqueio

Nao aprove o PR sem ajuste ou decisao explicita se houver:

- SQL novo dentro de rota.
- `HTTPException` novo dentro de repository ou service novo.
- Rota com regra fiscal extensa.
- Service crescendo com mais uma responsabilidade independente.
- Duplicacao de fluxo entre NFe e SPED.
- Refatoracao estrutural junto com mudanca fiscal sem teste de caracterizacao.
- Refatoracao P0/P1 sem criterio de entrada, saida e rollback claro.
- Migration sem estrategia de rollback/backup.
- Falha na suite rapida.
- Mudanca de contrato sem atualizacao de testes.

## Resumo Para Descricao de PR

Copie e preencha:

```md
## Backend Checklist

- [ ] Escopo do PR esta claro e pequeno.
- [ ] Convencoes backend foram verificadas.
- [ ] Rotas continuam sem SQL/regra fiscal extensa.
- [ ] Acesso a banco ficou em repository/service apropriado.
- [ ] Erros seguem `docs/backend-error-handling.md`.
- [ ] Contratos HTTP afetados tem teste.
- [ ] Helpers/regras puras tem teste direto.
- [ ] Perfil XML/SPED e escopo de empresa foram preservados.
- [ ] Rotas globais de catalogo ficaram explicitamente classificadas.
- [ ] Migrations/docs foram atualizadas quando necessario.
- [ ] Suite backend rapida passou.

Comando executado:

Resultado:
```
