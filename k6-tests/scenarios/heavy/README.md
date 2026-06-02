# Testes k6 pesados

Esta pasta adiciona uma camada complementar aos cenarios k6 existentes. Ela nao substitui `smoke.test.js`, `load.test.js`, `stress.test.js`, `spike.test.js` ou `soak.test.js`.

Os testes usam os mesmos helpers e flows existentes:

- autenticacao: `flows/login.flow.js`
- dashboard: `flows/dashboard.flow.js`
- consultas/listagens: `flows/consulta.flow.js`
- operacao critica read-only: `flows/operacaoCritica.flow.js`
- jornada completa: `flows/jornadaCompleta.flow.js`
- metricas customizadas: `helpers/metrics.js`

## Antes de rodar

Confirme:

- API local ou staging online.
- Usuario de teste valido em `K6_EMAIL` e `K6_PASSWORD`. O `high-load.test.js` tenta criar o usuario no `setup()` quando ele ainda nao existe.
- CNPJs e periodo com massa representativa.
- Banco, Redis e workers observados durante testes mais longos.
- Nao executar contra producao sem autorizacao explicita.

Exemplo local:

```powershell
$env:K6_EMAIL="usuario-local@teste.com"
$env:K6_PASSWORD="SenhaTeste@123"
$env:K6_AUTH_CNPJ="28942600000198"
$env:K6_XML_CNPJ="28942600000198"
$env:K6_SPED_CNPJ="35317121000146"
$env:K6_PERIODO_ANO="2026"
$env:K6_PERIODO_MES="2"
```

## Ordem recomendada

```bash
k6 run -e ENVIRONMENT=local k6-tests/scenarios/smoke.test.js

k6 run -e ENVIRONMENT=local k6-tests/scenarios/heavy/moderate-load.test.js

k6 run -e ENVIRONMENT=local k6-tests/scenarios/heavy/high-load.test.js

k6 run -e ENVIRONMENT=local k6-tests/scenarios/heavy/mixed-users.test.js

k6 run -e ENVIRONMENT=local k6-tests/scenarios/heavy/throughput.test.js

k6 run -e ENVIRONMENT=local k6-tests/scenarios/heavy/progressive-stress.test.js

k6 run -e ENVIRONMENT=local k6-tests/scenarios/heavy/sudden-spike.test.js

k6 run -e ENVIRONMENT=local k6-tests/scenarios/heavy/endurance.test.js
```

## Cenarios

### Moderate load

Arquivo: `moderate-load.test.js`

Uso:

```bash
k6 run -e ENVIRONMENT=local k6-tests/scenarios/heavy/moderate-load.test.js
```

Objetivo: primeiro passo apos o smoke. Sobe ate 5 VUs, sustenta por 5 minutos e reduz.

Thresholds:

- `http_req_failed < 1%`
- `http_req_duration p95 < 2000ms`
- `checks > 95%`
- `login_failure_rate < 1%`
- `auth_validation_failure_rate < 1%`

### High load

Arquivo: `high-load.test.js`

Uso:

```bash
k6 run -e ENVIRONMENT=local k6-tests/scenarios/heavy/high-load.test.js
```

Com alvo customizado:

```bash
k6 run -e ENVIRONMENT=local -e TARGET_VUS=20 -e TEST_DURATION=3m k6-tests/scenarios/heavy/high-load.test.js
```

Objetivo: simular uma carga maior, com rampa progressiva ate `TARGET_VUS` ou 30 VUs por padrao.

Thresholds:

- `http_req_failed < 3%`
- `http_req_duration p95 < 3000ms`
- `checks > 93%`
- `login_failure_rate < 3%`

### Progressive stress

Arquivo: `progressive-stress.test.js`

Uso:

```bash
k6 run -e ENVIRONMENT=local k6-tests/scenarios/heavy/progressive-stress.test.js
```

Com teto customizado:

```bash
k6 run -e ENVIRONMENT=local -e MAX_VUS=60 k6-tests/scenarios/heavy/progressive-stress.test.js
```

Objetivo: aumentar carga gradualmente para descobrir onde latencia, erros ou checks comecam a degradar.

Thresholds:

- `http_req_failed < 8%`
- `http_req_duration p95 < 5000ms`
- `checks > 90%`

### Sudden spike

Arquivo: `sudden-spike.test.js`

Uso:

```bash
k6 run -e ENVIRONMENT=local k6-tests/scenarios/heavy/sudden-spike.test.js
```

Com pico customizado:

```bash
k6 run -e ENVIRONMENT=local -e TARGET_VUS=50 k6-tests/scenarios/heavy/sudden-spike.test.js
```

Objetivo: simular entrada repentina de usuarios e observar recuperacao apos o pico.

Thresholds:

- `http_req_failed < 10%`
- `http_req_duration p95 < 6000ms`
- `checks > 85%`

### Endurance

Arquivo: `endurance.test.js`

Uso:

```bash
k6 run -e ENVIRONMENT=local k6-tests/scenarios/heavy/endurance.test.js
```

Com duracao customizada:

```bash
k6 run -e ENVIRONMENT=local -e TARGET_VUS=10 -e TEST_DURATION=45m k6-tests/scenarios/heavy/endurance.test.js
```

Objetivo: validar estabilidade por periodo prolongado. Nao rode automaticamente em CI comum.

Thresholds:

- `http_req_failed < 2%`
- `http_req_duration p95 < 3000ms`
- `checks > 95%`

### Mixed users

Arquivo: `mixed-users.test.js`

Uso:

```bash
k6 run -e ENVIRONMENT=local k6-tests/scenarios/heavy/mixed-users.test.js
```

Objetivo: simular perfis simultaneos:

- `dashboard_users`: login + dashboard.
- `consulta_users`: login + consultas/listagens.
- `critical_users`: login + operacao critica read-only.
- `slow_users`: usuarios com pausas maiores.
- `intense_users`: usuarios com menor tempo de espera.

Thresholds:

- `http_req_failed < 3%`
- `http_req_duration p95 < 3000ms`
- `checks > 93%`
- `login_failure_rate < 3%`
- `auth_validation_failure_rate < 3%`
- `critical_validation_failure_rate < 3%`

### Throughput

Arquivo: `throughput.test.js`

Uso:

```bash
k6 run -e ENVIRONMENT=local k6-tests/scenarios/heavy/throughput.test.js
```

Com taxa customizada:

```bash
k6 run -e ENVIRONMENT=local -e THROUGHPUT_RATE=3 -e TARGET_VUS=15 -e MAX_VUS=60 -e TEST_DURATION=5m k6-tests/scenarios/heavy/throughput.test.js
```

Objetivo: controlar volume de iteracoes por segundo usando `constant-arrival-rate`. O padrao e prudente: 2 iteracoes por segundo por 5 minutos.

Thresholds:

- `http_req_failed < 3%`
- `http_req_duration p95 < 3000ms`
- `checks > 93%`
- `login_failure_rate < 3%`
- `auth_validation_failure_rate < 3%`

## Variaveis de ambiente

- `ENVIRONMENT`: `local`, `staging` ou `production`. Padrao: `local`.
- `K6_ALLOW_PRODUCTION`: deve ser `true` para liberar production.
- `K6_EMAIL` e `K6_PASSWORD`: credenciais do usuario de teste.
- `K6_RUN_MODE`: `nfe`, `sped` ou automatico pela sessao.
- `K6_XML_CNPJ` e `K6_SPED_CNPJ`: CNPJs usados quando a sessao nao resolver um CNPJ valido.
- `K6_PERIODO_ANO` e `K6_PERIODO_MES`: periodo consultado.
- `TARGET_VUS`: alvo de VUs em cenarios parametrizados.
- `MAX_VUS`: teto de VUs em stress e throughput.
- `TEST_DURATION`: duracao dos blocos sustentados em high, endurance e throughput.
- `THROUGHPUT_RATE`: iteracoes por segundo no throughput.

## Como interpretar

- `checks`: validacoes funcionais. Queda aqui indica contrato, auth ou payload inesperado.
- `http_req_failed`: falhas HTTP na visao do k6.
- `http_req_duration p95`: 95% das requisicoes responderam abaixo desse tempo.
- `iteration_duration`: tempo de uma jornada completa.
- `login_duration`: tempo especifico de login.
- `dashboard_duration`: tempo especifico do dashboard de vendas.
- `consulta_duration`: tempo de consulta/listagem fiscal.
- `operacao_critica_duration`: tempo da consulta fiscal hierarquica.

## Quando parar

Pare o teste se:

- `http_req_failed` subir continuamente.
- `checks` cair abaixo do threshold.
- p95 crescer em degraus e nao recuperar.
- CPU, memoria, conexoes do banco ou Redis ficarem saturados.
- logs indicarem erro de autenticacao, pool de conexoes esgotado ou timeout.

## Gargalos provaveis

Observe:

- tempo de `POST /api/auth/entrar` para custo de login e banco;
- dashboards NFe/SPED para consultas agregadas;
- analise fiscal hierarquica para consultas pesadas;
- pool de conexoes PostgreSQL;
- Redis e workers apenas se testes com efeito colateral forem habilitados em outro fluxo.

Estes cenarios nao executam escrita destrutiva por padrao. A operacao critica permanece read-only.
