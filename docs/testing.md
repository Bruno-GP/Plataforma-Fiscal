# Testes e Qualidade

Este guia registra como rodar e evoluir os testes automatizados do projeto, com foco especial no back-end. A suite atual foi pensada para ser rapida e deterministica, deixando os cenarios pesados de banco, fila e carga para suites separadas.

## Arquivos de referencia

Back-end:

- `API/app/tests/`
- `API/app/tests/conftest.py`
- `API/app/tests/fixtures/`
- `API/app/requirements.txt`
- `API/app/api/auth/routes.py`
- `API/app/api/jobs/routes.py`
- `API/app/api/nfe/routes.py`
- `API/app/api/sped/routes.py`
- `API/app/core/security.py`
- `API/app/core/upload_security.py`
- `API/app/workers/`

Front-end:

- `Painel/package.json`
- `Painel/vitest.config.ts`
- `Painel/src/test/`

Carga e performance:

- `k6-tests/README.md`
- `k6-tests/scenarios/heavy/`

## Estado atual

### Back-end

- A suite fica em `API/app/tests/` e usa `pytest`.
- `conftest.py` ajusta o `sys.path`, cria um `TestClient` do FastAPI e sobrescreve `require_company_scope` com um usuario autenticado anonimo.
- As fixtures anonimizadas ficam em `API/app/tests/fixtures/`.
- Testes HTTP validam contratos de rotas sem exigir PostgreSQL, Redis ou Celery reais.
- Dependencias externas e servicos de persistencia sao isolados com `monkeypatch`.
- `test_sped_reader.py` compara o parser atual de SPED com a versao otimizada em `polars`; o teste e pulado automaticamente se `polars` nao estiver instalado.
- `test_jobs.py` cobre contratos de `/api/jobs`, disparo de jobs de importados e simulacoes de sucesso/falha do worker de NFe.

### Front-end

- Existem `vitest.config.ts` e testes em `Painel/src/test/`.
- `package.json` pode nao expor todos os comandos de teste esperados em CI; confira o arquivo antes de assumir `npm test`.
- Scripts historicamente usados: `dev`, `build`, `lint`, `preview`.

## Comandos

### Back-end

Instale as dependencias:

```bash
pip install -r API/app/requirements.txt
```

Rodando a partir da raiz:

```bash
python -m pytest API/app/tests
```

Rodando a partir de `API/app`:

```bash
cd API/app
pytest
```

No Windows, usando a venv local do projeto quando existir:

```powershell
cd API
.\.venv-local\Scripts\python.exe -m pytest app/tests
```

Para investigar um arquivo especifico:

```bash
python -m pytest API/app/tests/test_jobs.py -q
```

### Front-end

```bash
cd Painel
npm run lint
npm run build
```

Para rodar Vitest diretamente:

```bash
cd Painel
npx vitest run
```

### Testes pesados

Os cenarios de carga ficam fora da suite rapida de `pytest` e devem seguir os guias de `k6-tests/`. Nao misture execucao de carga com a suite unitaria/contratual do back-end, porque elas tem objetivos, duracao e dependencias diferentes.

## Padrao da suite back-end

### Autenticacao nos testes HTTP

O fixture `client` injeta um usuario autenticado com:

- `cnpj="12345678000190"`
- `empresa_id=1`
- `tem_sped=False`

Quando o teste precisa simular uma empresa SPED, ajuste o comportamento do servico consultado pela rota com `monkeypatch`, como nos testes de upload e processamento de SPED.

### Isolamento de banco e fila

Por padrao, testes de rota nao devem tocar banco real nem fila real. Prefira substituir repositorios, services e tasks nos pontos de uso da rota:

```python
monkeypatch.setattr("app.api.jobs.routes.JobsRepository", FakeJobsRepository)
```

Para workers, substitua as classes usadas dentro do modulo do worker:

```python
monkeypatch.setattr("app.workers.nfe_tasks.JobsRepository", Repo)
monkeypatch.setattr("app.workers.nfe_tasks.XMLImportacaoService", Importacao)
```

### Fixtures fiscais

Use apenas massas anonimizadas em `API/app/tests/fixtures/`. As fixtures pequenas atuais cobrem:

- NFe XML valida
- NFe XML invalida
- SPED TXT valido
- SPED TXT invalido

Ao adicionar uma fixture, documente no nome do arquivo qual fluxo ela cobre e evite dados reais de clientes, fornecedores, chaves de acesso ou valores sensiveis.

### Uploads

Testes de upload devem cobrir pelo menos:

- extensao e tipo de arquivo aceitos
- arquivo invalido
- limite de tamanho por variavel de ambiente
- regra de perfil da empresa, XML versus SPED
- resumo retornado pela rota, como quantidade importada e mensagens

### Jobs

Testes de jobs devem separar tres niveis:

- contrato HTTP de `/api/jobs`
- contrato HTTP de `processar-importados`, esperando `202` e `job_id`
- comportamento do worker com repositorios e processadores falsos

Evite depender de Redis/Celery em testes unitarios. Quando for necessario validar fila real, crie uma suite de integracao separada e deixe claro no nome/comando que ela exige infraestrutura.

## Lacunas conhecidas

- Falta ampliar a suite back-end com banco PostgreSQL descartavel.
- Falta teste de migrations em banco limpo.
- Falta cobertura completa de regras fiscais NFe/SPED com massas maiores.
- Falta regressao mais ampla para Reforma Tributaria e memoria de calculo.
- Falta teste dedicado de autorizacao multiempresa para endpoints analiticos.
- Falta suite de integracao para Redis/Celery com workers reais.
- Falta cobertura automatizada de relatorios IA com cliente OpenAI fakeado.
- Falta padronizar comando de teste do front-end no `package.json`, se o CI for exigir `npm test`.

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

### Fase 4: front-end e integracao

- Guards de rota XML/SPED.
- Login, hidratacao e logout limpando sessao local.
- Importacao com sucesso parcial e mensagens por arquivo.
- Dashboards com estado carregando, vazio e erro.
- Reforma Tributaria com filtros e estado vazio.
- Relatorios IA com loading, erro por `OPENAI_API_KEY` ausente e renderizacao do HTML retornado.
- Inconsistencias lendo pendencias da API e historico em `localStorage`.

### Fase 5: CI

- Adicionar script `test` ao `Painel/package.json`, se ainda nao existir.
- Rodar `npm run lint`, `npm run build` e `npm test` no CI.
- Rodar `python -m pytest API/app/tests` no CI.
- Criar suite back-end com banco de teste descartavel.
- Rodar migrations em banco limpo no pipeline.
- Publicar artefatos de cobertura e logs de falhas.
- Bloquear merge quando testes de seguranca, importacao e Reforma Tributaria falharem.
