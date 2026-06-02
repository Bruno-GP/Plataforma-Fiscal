# Estrutura Alvo do Backend

Este documento descreve uma estrutura alvo para evoluir o backend sem reescrita completa. A ideia e orientar novos modulos e refatoracoes futuras, migrando gradualmente os arquivos grandes atuais.

## Principios

- Nao mover tudo de uma vez.
- Criar estrutura nova quando houver feature/refatoracao no dominio.
- Preservar contratos HTTP existentes.
- Manter commits pequenos e reversiveis.
- Preferir extrair helpers puros e repositories antes de quebrar services grandes.

## Estrutura Recomendada

```text
API/app/
  api/
    auth/
    nfe/
    sped/
    reforma_tributaria/
    empresas/
    usuarios/
    importacao/
    relatorios/
    dashboard/
    jobs/
    shared/

  domain/
    nfe/
    sped/
    reforma_tributaria/
    fiscal/
    importacao/
    shared/

  services/
    nfe/
    sped/
    reforma_tributaria/
    empresas/
    usuarios/
    importacao/
    relatorios/
    dashboard/
    jobs/
    shared/

  repositories/
    nfe/
    sped/
    reforma_tributaria/
    empresas/
    usuarios/
    importacao/
    jobs/
    shared/

  models/
    nfe/
    sped/
    reforma_tributaria/
    auth/
    jobs/
    shared/

  workers/
    nfe/
    sped/
    shared/

  tests/
```

## Responsabilidade Por Pasta

### `api/<dominio>/`

Rotas FastAPI do dominio.

Deve conter:

- definicao de endpoints;
- dependencies;
- conversao de excecoes esperadas;
- response models.

Nao deve conter:

- SQL;
- parsing de arquivo;
- regra fiscal extensa;
- chamadas diretas para OpenAI, Redis ou banco quando houver service/repository.

### `domain/<dominio>/`

Regras puras e objetos de dominio.

Exemplos:

- extracao de dados de XML;
- normalizadores puros;
- classificadores fiscais;
- calculos deterministico sem I/O.

### `services/<dominio>/`

Casos de uso e orquestracao.

Exemplos:

- processar importacao;
- montar dashboard;
- sincronizar Reforma Tributaria;
- gerar analise fiscal chamando repositories.

### `repositories/<dominio>/`

Acesso a banco e queries.

Exemplos:

- consultas de notas;
- backfill Reforma Tributaria;
- resumo por periodo;
- persistencia de jobs;
- staging de importacao.

### `models/<dominio>/`

Schemas Pydantic e contratos de API.

Evitar misturar com regras de service.

### `workers/<dominio>/`

Execucao assíncrona de jobs e processamento em segundo plano.

Workers devem chamar services; nao devem repetir regra de rota.

### `shared/`

Codigo transversal realmente compartilhado.

Aceitavel:

- validadores de empresa;
- helpers de relatorio IA;
- montagem compartilhada de dashboards;
- utilitarios de erro;
- contratos internos comuns.

Evitar:

- jogar regras especificas de dominio em `shared`;
- transformar `shared` em novo modulo gigante.

## Dominios Recomendados

### `nfe`

Responsabilidade:

- consultas NFe/XML;
- notas e itens;
- KPIs NFe;
- importacao XML;
- dashboards NFe.

Prioridade de evolucao:

- continuar reduzindo `NFeConsultaService`;
- separar consultas de vendas/compras/clientes em repositories;
- manter `NFeNotasRepository` como referencia para novas consultas.

### `sped`

Responsabilidade:

- importacao SPED;
- staging SPED;
- consultas analiticas SPED;
- dashboards SPED;
- apuracao ICMS SPED.

Prioridade de evolucao:

- quebrar `SpedConsultaService` por caso de uso;
- criar repositories para KPIs, clientes, compras, vendas e hierarquia;
- separar parsing/carga/persistencia em `SpedImportacaoService`.

### `reforma_tributaria`

Responsabilidade:

- catalogo de tributos;
- apuracao;
- memoria de calculo;
- backfill;
- sincronizacao NFe/SPED com tabelas da Reforma.

Prioridade de evolucao:

- continuar extraindo repositories do `ReformaTributariaSyncService`;
- manter helpers XML puros fora do sync service;
- separar sync NFe e sync SPED quando houver cobertura adicional.

### `empresas`

Responsabilidade:

- perfil operacional XML/SPED;
- validacoes de CNPJ por empresa;
- futuras regras de multiempresa.

Hoje parte disso esta em:

- `CompanyProfileService`;
- `api/shared/company_validation.py`.

### `usuarios`

Responsabilidade:

- autenticacao;
- login;
- sessao;
- lockout;
- senha.

Prioridade futura:

- reduzir `LoginService` separando repository de login, politica de senha e politica de lockout.

### `importacao`

Responsabilidade:

- fluxo generico de staging;
- pendencias;
- validacao de lote;
- resultado de importacao.

Pode ser compartilhado por XML e SPED quando houver padrao comum suficiente.

### `relatorios`

Responsabilidade:

- relatorios IA;
- formatacao de prompts;
- respostas textuais;
- regras de disponibilidade externa.

Hoje parte disso esta em:

- `services/shared/ia_report_service.py`;
- `services/shared/analise_relatorio_service.py`;
- `services/AI/openai_report_service.py`.

### `dashboard`

Responsabilidade:

- montagem de dashboards;
- series mensais;
- comparativos;
- KPIs agregados.

Pode ficar em `services/shared` enquanto os fluxos ainda forem poucos, mas deve virar dominio proprio se crescer.

### `jobs`

Responsabilidade:

- criacao de jobs;
- consulta de status;
- metricas;
- integracao com workers.

## Plano Incremental de Migracao

### Passo 1

Para qualquer nova feature, criar arquivos ja na estrutura alvo quando possivel.

### Passo 2

Ao tocar em rota grande, remover uma responsabilidade:

- helper puro;
- formatter;
- validator;
- repository.

### Passo 3

Ao tocar em service P0/P1, evitar adicionar metodo grande novo. Criar service/use case menor e chamar pelo service legado se necessario.

### Passo 4

Quando um dominio tiver 3 ou mais repositories/use cases, criar um README curto no diretorio explicando responsabilidades.

### Passo 5

Remover codigo legado apenas depois de:

- testes passarem;
- chamadas antigas terem sido substituidas;
- contrato publico estar preservado.

## Regra de Ouro

Se uma mudanca exige entender rota, SQL, schema, parsing e regra fiscal no mesmo arquivo, ela deve ser quebrada antes de crescer.
