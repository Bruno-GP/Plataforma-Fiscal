# Checklist de Producao

## Arquivos de referencia no codigo

- `API/app/main.py`
- `API/app/core/config.py`
- `API/app/core/security.py`
- `API/app/core/upload_security.py`
- `Painel/package.json`
- `Painel/src/services/api.ts`
- `docs/deploy.md`
- `docs/migrations.md`

## Ordem operacional

1. Backup dos bancos NFe/XML e SPED.
2. Revisao final de variaveis sensiveis.
3. Aplicacao de migrations manuais.
4. Deploy da API.
5. Health check da API.
6. Deploy do Painel.
7. Smoke tests funcionais.
8. Validacao de logs.
9. Decisao de manter deploy ou executar rollback.

## Antes do deploy

- `APP_ENV=production`.
- `AUTH_SECRET_KEY` forte e diferente do padrao.
- HTTPS ativo.
- Cookies seguros configurados.
- CORS restrito ao dominio exato do painel, por exemplo `CORS_ALLOW_ORIGINS=https://plataforma-fiscal.vercel.app`.
- `CORS_ALLOW_CREDENTIALS=true`, sem wildcard em `CORS_ALLOW_ORIGINS`.
- `VITE_API_URL` do Painel apontando para a API publica, nunca para `localhost`.
- Se API e Painel estiverem em sites diferentes, `AUTH_COOKIE_SAMESITE=none` e `AUTH_COOKIE_SECURE=true`.
- Bancos NFe/XML e SPED criados e acessiveis.
- `DATABASE_URL`/`POSTGRES_DSN` apontando para o banco principal de producao.
- `POSTGRES_NFE_DSN` e `POSTGRES_SPED_DSN` definidos quando houver bancos separados.
- `sslmode=require` no DSN ou `POSTGRES_SSLMODE=require` quando o provedor exigir SSL.
- Migrations revisadas e aplicadas.
- Backup feito e restore testado.
- `npm run build` do Painel executado com sucesso.
- Health check da API validado.
- `OPENAI_API_KEY` configurada somente se relatorios IA forem habilitados.

## Depois do deploy

- Login com usuario real de teste.
- Cadastro ou consulta de empresa com `tem_sped=false`.
- Cadastro ou consulta de empresa com `tem_sped=true`.
- Teste controlado de importacao XML.
- Teste controlado de importacao SPED.
- Consulta de pendencias antes/depois do processamento.
- Dashboards principais carregando.
- Analise fiscal carregando.
- Reforma Tributaria com estado vazio ou dados esperados.
- Relatorio IA testado ou explicitamente desabilitado.
- Logs sem erros recorrentes.

## Criterios de rollback

- API nao inicia ou `/health` falha.
- Login ou sessao falha para usuario valido.
- CORS impede o Painel de chamar a API.
- Migration quebrou consulta fiscal critica.
- Importacao XML/SPED falha para fixture validada.
- Logs mostram erro recorrente de banco, autenticacao ou escopo.

Rollback de codigo deve ser rapido. Rollback de banco e mais sensivel e deve usar backup/restore ou script revisado; nao ha mecanismo automatizado no projeto.

## Auditoria operacional

- Registrar versao implantada.
- Registrar migrations aplicadas.
- Registrar responsavel e horario.
- Guardar evidencias de health check e smoke tests.
- Monitorar falhas de login, upload rejeitado e `403` multiempresa.
