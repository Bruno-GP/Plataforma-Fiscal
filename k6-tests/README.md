# k6 tests

Scripts de carga e contrato leve para a Plataforma Fiscal.

## Variaveis principais

```powershell
$env:BASE_URL="http://localhost:8000"
$env:K6_EMAIL="seu-email@empresa.com"
$env:K6_PASSWORD="sua-senha"
$env:K6_XML_CNPJ="28942600000198"
$env:K6_SPED_CNPJ="35317121000146"
$env:K6_PERIODO_ANO="2026"
$env:K6_PERIODO_MES="2"
```

## Scripts

Smoke publico:

```powershell
k6 run k6-tests/smoke.js
```

Fluxo real da tela de login: sessao sem cookie retorna `401`, login retorna `200`,
sessao autenticada retorna `200`, logout retorna `204` e sessao apos logout retorna `401`.

```powershell
k6 run k6-tests/auth-flow.js
```

Consultas autenticadas de jobs, Reforma Tributaria, NFe e SPED:

```powershell
k6 run k6-tests/readonly-dashboard.js
```

Para limitar a leitura a um tipo de empresa:

```powershell
$env:K6_RUN_MODE="nfe"
k6 run k6-tests/readonly-dashboard.js

$env:K6_RUN_MODE="sped"
k6 run k6-tests/readonly-dashboard.js
```

Importacao e criacao de jobs. Por padrao, este script consulta pendencias e jobs sem subir arquivos. Para importar as fixtures anonimizadas:

```powershell
$env:K6_RUN_UPLOADS="true"
k6 run k6-tests/imports-and-jobs.js
```

## Observacoes

- `BASE_URL` deve apontar para a raiz da API FastAPI, nao para `/api`.
- Os scripts autenticados dependem do cookie criado por `POST /api/auth/entrar`.
- Os endpoints de importacao usam fixtures existentes em `API/app/tests/fixtures`.
- Os status `400`, `403` e `404` aparecem como esperados em alguns cenarios porque dependem do tipo da empresa autenticada, existencia de dados e pendencias no banco.
- Ajuste os thresholds conforme o ambiente. Os valores atuais sao conservadores para desenvolvimento local.
