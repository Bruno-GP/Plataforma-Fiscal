# Resultados k6 - baseline local de performance

Data do registro: 2026-05-13
Ambiente: local
Ferramenta: Grafana k6

Este documento consolida os resultados apresentados da bateria local de performance da Plataforma Fiscal.

## Resumo executivo

A bateria local foi aprovada nos cenarios `stress`, `spike`, `soak` e `heavy/progressive-stress`.

Nao houve falhas HTTP em nenhum dos cenarios registrados. As poucas falhas de check ocorreram apenas por estouros pontuais de tempo em validacoes internas, sem falha de contrato, autenticacao ou resposta HTTP.

## Cenarios executados

| Cenario | Script | Duracao | Pico de VUs | Requests | Resultado |
| --- | --- | ---: | ---: | ---: | --- |
| Stress | `k6-tests/scenarios/stress.test.js` | 13m | 100 | 94.176 | Aprovado |
| Spike | `k6-tests/scenarios/spike.test.js` | 3m10s | 100 | 39.186 | Aprovado |
| Soak | `k6-tests/scenarios/soak.test.js` | 1h10m | 30 | 359.343 | Aprovado |
| Progressive stress | `k6-tests/scenarios/heavy/progressive-stress.test.js` | 28m | 100 | 246.879 | Aprovado |

## Resultados por cenario

### Stress

Comando:

```powershell
k6 run -e ENVIRONMENT=local k6-tests/scenarios/stress.test.js
```

Thresholds:

| Metrica | Resultado | Limite |
| --- | ---: | ---: |
| `checks` | 99,99% | > 90% |
| `critical_validation_failure_rate` | 0,00% | < 5% |
| `http_req_duration p95` | 139,33ms | < 3000ms |
| `http_req_failed` | 0,00% | < 5% |
| `login_failure_rate` | 0,00% | < 5% |

Resumo:

| Metrica | Valor |
| --- | ---: |
| Checks totais | 418.560 |
| Checks com sucesso | 418.533 |
| Checks com falha | 27 |
| Requests HTTP | 94.176 |
| Iteracoes completas | 10.464 |
| `http_req_duration avg` | 34,33ms |
| `http_req_duration max` | 2,74s |
| `iteration_duration p95` | 4,25s |

Falhas pontuais de tempo:

| Check | Falhas |
| --- | ---: |
| `auth_login: resposta abaixo de 2000ms` | 3 |
| `auth_session: resposta abaixo de 1000ms` | 5 |
| `jobs_metrics: resposta abaixo de 1500ms` | 10 |
| `reforma_tributos: resposta abaixo de 1500ms` | 9 |

### Spike

Comando:

```powershell
k6 run -e ENVIRONMENT=local k6-tests/scenarios/spike.test.js
```

Thresholds:

| Metrica | Resultado | Limite |
| --- | ---: | ---: |
| `checks` | 99,96% | > 90% |
| `http_req_failed` | 0,00% | < 5% |
| `login_failure_rate` | 0,00% | < 5% |

Resumo:

| Metrica | Valor |
| --- | ---: |
| Checks totais | 174.160 |
| Checks com sucesso | 174.101 |
| Checks com falha | 59 |
| Requests HTTP | 39.186 |
| Iteracoes completas | 4.354 |
| `http_req_duration avg` | 55,30ms |
| `http_req_duration p95` | 210,42ms |
| `http_req_duration max` | 3s |
| Throughput medio | 204,38 req/s |

Falhas pontuais de tempo:

| Check | Falhas |
| --- | ---: |
| `auth_login: resposta abaixo de 2000ms` | 21 |
| `auth_session: resposta abaixo de 1000ms` | 1 |
| `jobs_metrics: resposta abaixo de 1500ms` | 18 |
| `reforma_tributos: resposta abaixo de 1500ms` | 17 |
| `ncm_tributacao: resposta abaixo de 1500ms` | 1 |
| `nfe_analise_fiscal_cfop: resposta abaixo de 3000ms` | 1 |

### Soak

Comando:

```powershell
k6 run -e ENVIRONMENT=local k6-tests/scenarios/soak.test.js
```

Thresholds:

| Metrica | Resultado | Limite |
| --- | ---: | ---: |
| `checks` | 100,00% | > 95% |
| `critical_validation_failure_rate` | 0,00% | < 1% |
| `http_req_duration p95` | 31,89ms | < 3000ms |
| `http_req_failed` | 0,00% | < 1% |
| `login_failure_rate` | 0,00% | < 1% |

Resumo:

| Metrica | Valor |
| --- | ---: |
| Checks totais | 1.597.080 |
| Checks com sucesso | 1.597.080 |
| Checks com falha | 0 |
| Requests HTTP | 359.343 |
| Iteracoes completas | 39.927 |
| `http_req_duration avg` | 13,84ms |
| `http_req_duration max` | 1,03s |
| `iteration_duration p95` | 3,70s |
| Throughput medio | 85,52 req/s |

### Progressive stress

Comando:

```powershell
k6 run -e ENVIRONMENT=local k6-tests/scenarios/heavy/progressive-stress.test.js
```

Thresholds:

| Metrica | Resultado | Limite |
| --- | ---: | ---: |
| `checks` | 99,99% | > 90% |
| `http_req_duration p95` | 162,23ms | < 5000ms |
| `http_req_failed` | 0,00% | < 8% |

Resumo:

| Metrica | Valor |
| --- | ---: |
| Checks totais | 1.097.240 |
| Checks com sucesso | 1.097.199 |
| Checks com falha | 41 |
| Requests HTTP | 246.879 |
| Iteracoes completas | 27.431 |
| `http_req_duration avg` | 37,26ms |
| `http_req_duration max` | 2,12s |
| `iteration_duration p95` | 4,24s |
| Throughput medio | 146,88 req/s |

Falhas pontuais de tempo:

| Check | Falhas |
| --- | ---: |
| `auth_session: resposta abaixo de 1000ms` | 20 |
| `jobs_metrics: resposta abaixo de 1500ms` | 7 |
| `reforma_tributos: resposta abaixo de 1500ms` | 14 |

## Conclusao

O baseline local de performance foi aprovado.

A aplicacao sustentou carga progressiva e picos de ate 100 VUs sem falhas HTTP, sem falhas de autenticacao e sem falhas de validacao critica. O teste de soak tambem passou sem nenhum check com falha durante 1h10m, indicando estabilidade local sob carga constante.

Os endpoints com maior incidencia de latencia pontual foram:

- `auth_login`
- `auth_session`
- `jobs_metrics`
- `reforma_tributos`

Esses pontos nao bloquearam os thresholds da bateria, mas podem ser usados como foco de observabilidade em uma futura execucao em staging.
