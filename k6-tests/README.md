# Testes k6

Base incremental de testes de carga, acesso de usuarios e performance da Plataforma Fiscal.

## Projeto analisado

- Backend: FastAPI em `API/app`, exposto localmente em `http://localhost:8000`.
- Frontend: React + Vite em `Painel`, exposto localmente em `http://localhost:5173`.
- Prefixo da API: `/api`.
- Autenticacao: `POST /api/auth/entrar`, com cookie HttpOnly definido pela API.
- Sessao autenticada: `GET /api/auth/sessao`.
- Variaveis de ambiente: `.env.example`, `API/app/.env.example` e `Painel/.env`.
- Docker: `docker-compose.yml` sobe PostgreSQL, Redis, API, workers Celery e frontend.
- Testes existentes: testes Python em `API/app/tests`, testes Vitest em `Painel/src/test` e scripts k6 legados mantidos na raiz de `k6-tests`.

## Estrutura

```text
k6-tests/
|-- config/
|   `-- environments.js
|-- data/
|   `-- users.example.json
|-- helpers/
|   |-- auth.js
|   |-- httpClient.js
|   `-- metrics.js
|-- flows/
|   |-- login.flow.js
|   |-- dashboard.flow.js
|   |-- consulta.flow.js
|   |-- operacaoCritica.flow.js
|   `-- jornadaCompleta.flow.js
|-- scenarios/
|   |-- smoke.test.js
|   |-- load.test.js
|   |-- stress.test.js
|   |-- spike.test.js
|   |-- soak.test.js
|   `-- heavy/
|       |-- moderate-load.test.js
|       |-- high-load.test.js
|       |-- progressive-stress.test.js
|       |-- sudden-spike.test.js
|       |-- endurance.test.js
|       |-- mixed-users.test.js
|       |-- throughput.test.js
|       `-- README.md
`-- README.md
```

## Instalacao do k6

Windows com Chocolatey:

```powershell
choco install k6
```

Windows com winget:

```powershell
winget install k6.k6
```

macOS:

```bash
brew install k6
```

Linux: consulte https://grafana.com/docs/k6/latest/set-up/install-k6/.

## Credenciais e massa de teste

Nao versione credenciais reais. O arquivo `data/users.example.json` e apenas um exemplo.

Para rodar localmente, informe credenciais por variaveis de ambiente:

```powershell
$env:K6_EMAIL="usuario-local@teste.com"
$env:K6_PASSWORD="SenhaTeste@123"
$env:K6_AUTH_CNPJ="28942600000198"
```

Opcionalmente crie `k6-tests/data/users.local.json` para documentar usuarios locais. Esse arquivo esta no `.gitignore` e nao e lido automaticamente pelos scripts para evitar falha quando ele nao existir.

## Ambientes

O ambiente padrao e `local`.

```bash
k6 run -e ENVIRONMENT=local k6-tests/scenarios/smoke.test.js
k6 run -e ENVIRONMENT=staging k6-tests/scenarios/load.test.js
```

URLs podem ser sobrescritas:

```powershell
$env:K6_BASE_URL="http://localhost:8000"
$env:K6_FRONTEND_URL="http://localhost:5173"
```

Execucao contra `production` e bloqueada por padrao. Para liberar conscientemente:

```bash
k6 run -e ENVIRONMENT=production -e K6_ALLOW_PRODUCTION=true k6-tests/scenarios/smoke.test.js
```

Nao rode load, stress, spike ou soak em producao sem janela aprovada e limites definidos.

## Dados de filtro

Os fluxos usam CNPJ e periodo da sessao autenticada quando possivel. Para bases locais sem dados suficientes, ajuste:

```powershell
$env:K6_XML_CNPJ="28942600000198"
$env:K6_SPED_CNPJ="35317121000146"
$env:K6_PERIODO_ANO="2026"
$env:K6_PERIODO_MES="2"
$env:K6_UF="SP"
$env:K6_NCM="01012100"
```

Para forcar o tipo de jornada:

```powershell
$env:K6_RUN_MODE="nfe"
# ou
$env:K6_RUN_MODE="sped"
```

Sem `K6_RUN_MODE`, o script usa `tem_sped` retornado pela sessao.

## Como rodar

Na raiz do repositorio:

```bash
k6 run -e ENVIRONMENT=local -e K6_DEBUG_HTTP=true k6-tests/scenarios/debug-status.test.js
k6 run -e ENVIRONMENT=local k6-tests/scenarios/smoke.test.js
k6 run -e ENVIRONMENT=local k6-tests/scenarios/load.test.js
k6 run -e ENVIRONMENT=local k6-tests/scenarios/stress.test.js
k6 run -e ENVIRONMENT=local k6-tests/scenarios/spike.test.js
k6 run -e ENVIRONMENT=local k6-tests/scenarios/soak.test.js
```

Ou pelo `package.json` do frontend:

```bash
cd Painel
npm run test:k6:smoke
npm run test:k6:load
npm run test:k6:stress
npm run test:k6:spike
npm run test:k6:soak
```

Testes pesados complementares:

```bash
cd Painel
npm run test:k6:heavy:moderate
npm run test:k6:heavy:high
npm run test:k6:heavy:mixed
npm run test:k6:heavy:throughput
npm run test:k6:heavy:stress
npm run test:k6:heavy:spike
npm run test:k6:heavy:endurance
```

Veja os detalhes em `k6-tests/scenarios/heavy/README.md`.

## Cenarios

- Smoke: 1 VU por 1 minuto. Valida API online, login, sessao, dashboard, consulta/listagem e operacao critica read-only.
- Debug status: 1 iteracao autenticada. Imprime status e trecho do corpo de `/reforma-tributaria/tributos` e da analise fiscal hierarquica para diagnosticar falhas sem rodar carga.
- Load: rampa ate 10 VUs, mantem 5 minutos e reduz. Simula carga esperada inicial.
- Stress: rampa ate 100 VUs. Ajuda a encontrar limite do sistema.
- Spike: salto rapido de 10 para 100 VUs. Simula pico repentino.
- Soak: 30 VUs por 60 minutos. Valida estabilidade e degradacao ao longo do tempo.

## Fluxos cobertos

- `POST /api/auth/entrar`
- `GET /api/auth/sessao`
- `GET /api/jobs/metrics`
- `GET /api/jobs?limit=10&offset=0`
- `GET /api/reforma-tributaria/tributos`
- `GET /api/ncm/tributacao`
- NFe, quando `tem_sped=false` ou `K6_RUN_MODE=nfe`:
  - `GET /api/nfe/analise/vendas/dashboard`
  - `GET /api/nfe/analise/fiscal/cfop`
  - `GET /api/nfe/analise/fiscal/hierarquia`
- SPED, quando `tem_sped=true` ou `K6_RUN_MODE=sped`:
  - `GET /api/sped/analise/vendas/dashboard`
  - `GET /api/sped/analise/fiscal/cfop`
  - `GET /api/sped/analise/fiscal/hierarquia`

## Metricas e thresholds

Metricas k6 padrao:

- `http_req_failed`
- `http_req_duration`
- `checks`

Metricas customizadas:

- `login_duration`
- `login_failure_rate`
- `dashboard_duration`
- `consulta_duration`
- `operacao_critica_duration`
- `auth_validation_failure_rate`
- `critical_validation_failure_rate`

Thresholds principais:

- Smoke/load: `http_req_failed < 1%`, `p95 < 2000ms`, `checks > 95%`.
- Stress/spike: tolerancia maior de erro controlado para descobrir limite.
- Soak: `http_req_failed < 1%`, `p95 < 3000ms`, `checks > 95%`.

## Operacoes com efeito colateral

Por padrao, `operacaoCritica.flow.js` executa apenas consulta pesada read-only em analise fiscal hierarquica.

Chamadas que podem enfileirar processamento, como:

- `POST /api/nfe/xml/processar-importados`
- `POST /api/sped/processar-importados`

so sao executadas quando `K6_ENABLE_SIDE_EFFECTS=true`. Mesmo assim, os scripts aceitam `202`, `400`, `403` e `404`, porque dependem de pendencias reais e perfil da empresa.

Uploads/importacoes nao fazem parte da jornada principal de carga para evitar criacao destrutiva de massa. Os scripts k6 legados continuam disponiveis para testes controlados de importacao.

## Interpretacao rapida

- `checks`: taxa de validacoes funcionais que passaram.
- `http_req_failed`: percentual de requests com falha HTTP segundo o k6.
- `http_req_duration p(95)`: 95% das requisicoes responderam abaixo desse tempo.
- `login_failure_rate`: falha especifica do fluxo de autenticacao.
- `critical_validation_failure_rate`: falha da consulta/operacao critica.

Se o smoke falhar no login, valide `K6_EMAIL`, `K6_PASSWORD`, API ligada e usuario cadastrado no banco local/staging. A senha precisa obedecer a politica da API: minimo de 12 caracteres, maiuscula, minuscula, numero e simbolo.

## Pontos para preencher/validar

- Trocar placeholders de `staging` e `production` em `config/environments.js`.
- Definir usuarios de teste por ambiente.
- Validar CNPJs e periodos com dados representativos.
- Ajustar thresholds apos medir baseline real do staging.
- Definir janela e limites antes de qualquer teste fora do ambiente local/staging.
