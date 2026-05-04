# Testes e Qualidade

## Arquivos de referencia no codigo

- `Painel/package.json`
- `Painel/vitest.config.ts`
- `Painel/src/test/`
- `API/app/api/auth/routes.py`
- `API/app/api/nfe/routes.py`
- `API/app/api/sped/routes.py`
- `API/app/api/reforma_tributaria/routes.py`
- `API/app/core/security.py`
- `API/app/core/upload_security.py`

## Estado atual

Frontend:

- Existem `vitest.config.ts` e testes em `Painel/src/test/`.
- `package.json` nao possui script `test`.
- Scripts existentes: `dev`, `build`, `lint`, `preview`.

Backend:

- Nao ha suite de testes automatizados identificada no modulo `API/`.
- A validacao atual depende de execucao manual, Swagger, health check e verificacao das telas.

## Comandos disponiveis hoje

```bash
cd Painel
npm run lint
npm run build
```

Para rodar Vitest sem alterar `package.json`, use:

```bash
cd Painel
npx vitest run
```

## Lacunas

- Falta script `test` no frontend.
- Falta suite de testes backend para rotas, services e banco.
- Falta base de fixtures fiscais versionada para XML, NFC-e, NFSe e SPED.
- Falta teste de regressao para Reforma Tributaria e memoria de calculo.
- Falta teste de autorizacao multiempresa.

## Plano de implementacao por fases

### Fase 1: seguranca e importacao minima

- Backend auth: cadastro, login, sessao, logout, senha fraca, senha invalida, lockout.
- Escopo multiempresa: `emitente_cnpj`, `cnpj_emitente` e `cnpj_empresa_origem` divergentes devem retornar `403`.
- Upload XML: extensao invalida, arquivo vazio, tamanho acima do limite, conteudo nao XML, CNPJ divergente, duplicidade, NFC-e cancelada/inutilizada.
- Upload SPED: extensao invalida, arquivo vazio, tamanho acima do limite, conteudo nao textual, registro `0000` ausente, CNPJ divergente, duplicidade.
- Rotas batch frageis: testes devem registrar o comportamento atual de `/api/nfe/processar` e `/api/sped/processar`, que nao recebem CNPJ em query.

### Fase 2: banco e processamento

- Criacao sob demanda de `notas_xml_importados` e `sped_importados`.
- Marcacao de `processado_em` apos processamento.
- Pendencias antes/depois do processamento.
- Fixtures anonimizadas de XML e SPED com totais esperados.
- Processamento SPED criando participantes, produtos, documentos, itens, KPIs e apuracao ICMS.
- Validacao de migrations `004` a `006` em banco limpo.
- Testes de falha de banco e transacao parcial.

### Fase 3: Reforma Tributaria

- Catalogo de tributos carregado por migration.
- Sync NFe para ICMS, IPI, PIS e COFINS.
- Sync SPED para ICMS.
- Apuracao por periodo e tributo.
- Documento e item retornando apenas dados da empresa autenticada.
- Memoria de calculo: primeiro testar estado vazio, porque nao foi encontrado service que popula `memoria_calculo_tributaria`; depois criar testes quando a populacao for implementada.
- Testes negativos deixando claro que CBS, IBS e IS ainda nao possuem motor fiscal implementado.

### Fase 4: frontend e integracao

- Guards de rota XML/SPED.
- Login, hidratacao e logout limpando sessao local.
- Importacao com sucesso parcial e mensagens por arquivo.
- Dashboards com estado carregando, vazio e erro.
- Reforma Tributaria com filtros e estado vazio.
- Relatorios IA com loading, erro por `OPENAI_API_KEY` ausente e renderizacao do HTML retornado.
- Inconsistencias lendo pendencias da API e historico em `localStorage`.

### Fase 5: CI

- Adicionar script `test` ao `Painel/package.json`.
- Rodar `npm run lint`, `npm run build` e `npm test` no CI.
- Criar suite backend com banco de teste descartavel.
- Rodar migrations em banco limpo no pipeline.
- Publicar artefatos de cobertura e logs de falhas.
- Bloquear merge quando testes de seguranca, importacao e Reforma Tributaria falharem.
