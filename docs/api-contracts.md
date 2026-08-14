# Contratos de API

Base local: `http://localhost:8000`. Prefixo: `/api`. Endpoints fiscais exigem autenticacao por cookie HttpOnly ou `Authorization: Bearer <token>`.

## Arquivos de referencia no codigo

- `API/app/api/auth/routes.py`
- `API/app/api/nfe/routes.py`
- `API/app/api/sped/routes.py`
- `API/app/api/ncm/routes.py`
- `API/app/api/jobs/routes.py`
- `API/app/api/reforma_tributaria/routes.py`
- `API/app/models/nfe/auth/schemas.py`
- `API/app/models/nfe/schemas.py`
- `API/app/models/sped/schemas.py`
- `API/app/models/reforma_tributaria/schemas.py`
- `API/app/core/security.py`

## Autenticacao

### `POST /api/auth/registrar`

- Autenticacao: nao exige sessao previa.
- Body obrigatorio: `empresa_nome`, `email`, `senha`, `cnpj`, `estado`, `cidade`, `municipio_id`, `codigo_ibge`.
- Body opcional: `tem_sped` (padrao `false`).
- Request:

```json
{ "empresa_nome": "Empresa Exemplo", "email": "user@example.com", "senha": "Senha@123456", "cnpj": "12345678000199", "tem_sped": false, "estado": "SP", "cidade": "Sao Paulo", "municipio_id": "3550308", "codigo_ibge": "3550308" }
```

- Response:

```json
{ "status": "ok", "login_id": 1, "empresa_id": 1, "cnpj": "12345678000199", "email": "user@example.com", "empresa_nome": "Empresa Exemplo", "tem_sped": false, "tem_xml_importado_valido": false, "expires_in": 28800, "access_token": "eyJ..." }
```

- Erros comuns: `400` dados invalidos/duplicados, `422` schema invalido.
- Observacao: define o perfil operacional XML ou SPED da empresa. Os campos de localidade sao obrigatorios na validacao da rota mesmo sendo opcionais no schema Pydantic.

### `POST /api/auth/entrar`

- Autenticacao: nao exige sessao previa.
- Body obrigatorio: `email`, `senha`.
- Response semelhante ao cadastro, com `status="ok"`.
- Erros comuns: `401` credenciais invalidas ou bloqueio temporario por tentativas excedidas, `503` servico de autenticacao indisponivel.

### `GET /api/auth/sessao`

- Autenticacao: obrigatoria.
- Retorna dados da sessao atual e `expires_in`.
- Erros comuns: `401` token ausente, invalido ou expirado.

### `GET /api/auth/perfil`

- Autenticacao: obrigatoria.
- Retorna os dados cadastrais da empresa da sessao atual, usados pela tela de configuracoes.
- Campos retornados: `status`, `login_id`, `empresa_id`, `cnpj`, `empresa_nome`, `estado`, `cidade`, `municipio_id`, `codigo_ibge`.
- Erros comuns: `401` sem autenticacao, `404` quando o perfil da empresa nao e localizado.

### `PATCH /api/auth/senha`

- Autenticacao: obrigatoria.
- Body obrigatorio: `nova_senha`.
- Atualiza somente a senha do usuario logado.
- Response: `status`, `message`.
- Erros comuns: `400` senha vazia ou invalida, `503` indisponibilidade do servico de autenticacao.

### `POST /api/auth/sair`

- Autenticacao: nao depende de body.
- Response: `204 No Content`.
- Observacao: remove cookie de sessao; o painel tambem limpa `localStorage`.

Schema real de auth (`LoginCadastroResponse`, `LoginResponse`, `SessaoResponse`, `CompanyProfileResponse`, `UpdatePasswordResponse`):

Exemplo de resposta de `POST /api/auth/entrar`:

```json
{
  "status": "ok",
  "login_id": 1,
  "empresa_id": 1,
  "cnpj": "12345678000199",
  "email": "user@example.com",
  "empresa_nome": "Empresa Exemplo",
  "tem_sped": false,
  "tem_xml_importado_valido": false,
  "expires_in": 28800,
  "access_token": "eyJ..."
}
```

Exemplo de resposta de `GET /api/auth/sessao` (sem `access_token`, que nao e renovado nesta rota):

```json
{
  "status": "ok",
  "login_id": 1,
  "empresa_id": 1,
  "cnpj": "12345678000199",
  "email": "user@example.com",
  "empresa_nome": "Empresa Exemplo",
  "tem_sped": false,
  "tem_xml_importado_valido": false,
  "expires_in": 28800
}
```

Exemplo de resposta de `GET /api/auth/perfil`:

```json
{
  "status": "ok",
  "login_id": 1,
  "empresa_id": 1,
  "cnpj": "12345678000199",
  "empresa_nome": "Empresa Exemplo",
  "estado": "SP",
  "cidade": "Sao Paulo",
  "municipio_id": "3550308",
  "codigo_ibge": "3550308"
}
```

Exemplo de resposta de `PATCH /api/auth/senha`:

```json
{
  "status": "ok",
  "message": "Senha atualizada com sucesso."
}
```

## Importacao XML/NFe

### `POST /api/nfe/processar`

- Autenticacao: obrigatoria.
- Query obrigatoria: `cnpj_empresa_origem` (validado contra o CNPJ da sessao por `require_company_scope` e contra o perfil da empresa por `validar_empresa_xml`).
- Body obrigatorio: `origem`, `pasta_xml`.
- Body opcional: `empresa_id`, `periodo`.
- Request:

```http
POST /api/nfe/processar?cnpj_empresa_origem=12345678000199
```

```json
{ "origem": "upload-local", "pasta_xml": "empresa-x/lote-01", "periodo": "2026-01" }
```

- Response (`ProcessarNFeResponse`): `status`, `cnpj_emitente`, `periodo_ano`, `periodo_mes`, `periodos_encontrados`, `notas_processadas`, `itens_processados`, `kpis`, `erros`, `data_processamento`.
- Item de `kpis`: `ano`, `mes`, `kpis`; dentro de `kpis`: `total_vendas`, `quantidade_notas`, `ticket_medio`, `maior_nota`, `menor_nota`, `total_icms`, `total_ipi`, `total_pis`, `total_cofins`, `top_clientes`, `top_produtos`, `top_cidades`.
- Observacao: rota batch/legada, nao usada pelo Painel (fluxo principal e importar para staging e chamar `xml/processar-importados`). `pasta_xml` e relativa e resolvida dentro de `PROCESSAMENTO_BATCH_ROOT_DIR` (400 se nao configurado ou se o caminho escapar da raiz). O CNPJ extraido dos XMLs deve bater com `cnpj_empresa_origem`, senao a resposta volta com `status="erro"`.
- Erros comuns: `400` empresa fora do perfil XML, path fora da raiz permitida ou raiz nao configurada; `403` `cnpj_empresa_origem` fora do escopo da sessao.

### `POST /api/nfe/xml/importar`

- Autenticacao: obrigatoria e empresa `tem_sped=false`.
- Query obrigatoria: `cnpj_empresa_origem`.
- Body: `multipart/form-data` com `arquivos`.
- Limites: ate 10.000 arquivos; `.xml`; tamanho por arquivo e total conforme env.
- Exemplo:

```bash
curl -X POST "http://localhost:8000/api/nfe/xml/importar?cnpj_empresa_origem=12345678000199" -F "arquivos=@nota.xml"
```

- Response:

```json
{ "status": "ok", "total_arquivos": 1, "importados": 1, "duplicados": 0, "erros": 0, "resultados": [{ "arquivo": "nota.xml", "cnpj_emitente": "12345678000199", "status": "importado", "mensagem": "XML importado com sucesso." }] }
```

- Erros comuns: `400` extensao/conteudo/CNPJ/fluxo invalidos, `403` CNPJ fora do escopo.
- Observacao: duplicidade e controlada por hash do arquivo por CNPJ.

### `GET /api/nfe/xml/pendencias`

- Query obrigatoria: `cnpj_emitente`.
- Response (`ImportacaoXMLPendenciasResponse`): `status`, `cnpj_emitente`, `total_pendentes`, `possui_pendentes`.

### `POST /api/nfe/xml/processar-importados`

- Query obrigatoria: `cnpj_emitente`.
- Enfileira o processamento do staging nao processado.
- Status HTTP: `202 Accepted`.
- Response (`JobCreateResponse`):

```json
{
  "job_id": "00000000-0000-0000-0000-000000000000",
  "status": "QUEUED",
  "message": "Processamento enviado para fila"
}
```

- O resultado operacional deve ser acompanhado em `/api/jobs/{job_id}`. Em sucesso, o worker marca os XMLs importados como processados e atualiza `processing_jobs`.
- Erros comuns: `404` sem XML pendente, `400` fluxo errado.

## Importacao SPED

### `POST /api/sped/processar`

- Autenticacao: obrigatoria.
- Query obrigatoria: `cnpj_empresa_origem` (validado contra o CNPJ da sessao por `require_company_scope` e contra o perfil da empresa por `validar_empresa_sped`).
- Body obrigatorio: `arquivo_sped`.
- Request:

```http
POST /api/sped/processar?cnpj_empresa_origem=12345678000199
```

```json
{ "arquivo_sped": "empresa-x/EFD_FISCAL_012026.txt" }
```

- Response (`ProcessarSpedFiscalResponse`): `status`, `arquivo_sped`, `total_linhas`, `total_registros_identificados`, `resumo_registros`, `banco_sped`.
- Item de `resumo_registros`: `registro`, `quantidade`.
- Observacao: rota batch/legada, nao usada pelo Painel (fluxo principal e importar para staging e chamar `processar-importados`). `arquivo_sped` e relativo e resolvido dentro de `PROCESSAMENTO_BATCH_ROOT_DIR` (400 se nao configurado ou se o caminho escapar da raiz). Nao ha extracao de CNPJ do conteudo do arquivo para conferencia adicional — o escopo depende do `cnpj_empresa_origem` informado.
- Erros comuns: `400` empresa fora do perfil SPED, path fora da raiz permitida ou raiz nao configurada; `403` `cnpj_empresa_origem` fora do escopo da sessao.

### `POST /api/sped/importar`

- Autenticacao: obrigatoria e empresa `tem_sped=true`.
- Query obrigatoria: `cnpj_empresa_origem`.
- Body: `multipart/form-data` com `arquivos`.
- Limites: ate 500 arquivos; `.txt`; tamanho por arquivo e total conforme env.
- Response (`ImportacaoSpedResponse`): `status`, `total_arquivos`, `importados`, `duplicados`, `erros`, `resultados`.
- Item de `resultados`: `arquivo`, `cnpj_emitente`, `status`, `mensagem`.
- Observacao: CNPJ e extraido do registro `0000`.

### `GET /api/sped/pendencias`

- Query obrigatoria: `cnpj_emitente`.
- Response (`ImportacaoSpedPendenciasResponse`): `status`, `cnpj_emitente`, `total_pendentes`, `possui_pendentes`.

### `POST /api/sped/processar-importados`

- Query obrigatoria: `cnpj_emitente`.
- Enfileira o processamento do staging SPED nao processado.
- Status HTTP: `202 Accepted`.
- Response (`JobCreateResponse`):

```json
{
  "job_id": "00000000-0000-0000-0000-000000000000",
  "status": "QUEUED",
  "message": "Processamento enviado para fila"
}
```

- O worker carrega participantes, produtos, documentos, itens, KPIs e apuracao ICMS quando disponiveis. O resultado operacional deve ser acompanhado em `/api/jobs/{job_id}`.

## Jobs de processamento

Os endpoints de processamento de importados nao executam trabalho pesado no request. Eles criam registro em `processing_jobs`, enviam a tarefa ao Celery e retornam `job_id`.

Os endpoints `GET /api/jobs`, `GET /api/jobs/{job_id}` e `GET /api/jobs/metrics` exigem autenticacao. A listagem e as metricas retornam apenas jobs vinculados ao CNPJ da sessao autenticada. A consulta de um `job_id` de outra empresa retorna `404`, para nao expor a existencia do job.

Tipos atuais:

- `NFE_PROCESSAMENTO_IMPORTADOS`
- `SPED_PROCESSAMENTO_IMPORTADOS`

Status possiveis:

- `PENDING`
- `QUEUED`
- `RUNNING`
- `SUCCESS`
- `FAILED`
- `CANCELED`

### `GET /api/jobs/{job_id}`

- Retorna `id`, `tipo`, `status`, `mensagem`, `total_itens`, `itens_processados`, `erro`, `criado_em`, `iniciado_em`, `finalizado_em`.
- Erros comuns: `401` sem autenticacao; `404` job inexistente ou fora do escopo da empresa autenticada.

### `GET /api/jobs`

- Query opcional: `status`, `tipo`, `data_inicio`, `data_fim`, `limit` (1-500), `offset`.
- Response: `total`, `limit`, `offset`, `resultados`.

### `GET /api/jobs/metrics`

- Query opcional: `status`, `tipo`, `data_inicio`, `data_fim`.
- Response: `total_jobs`, `por_status`, `por_tipo`, `duracao_media_ms`.

Observacao operacional: Redis e workers Celery devem estar ativos para que jobs avancem de `QUEUED` para `RUNNING`/`SUCCESS`/`FAILED`.

## Analises fiscais, dashboards e clientes

Rotas NFe e SPED possuem contratos semelhantes:

- NFe usa `emitente_cnpj` opcional em algumas rotas porque tambem resolve por sessao/email.
- SPED exige `emitente_cnpj`.
- Filtros comuns: `periodo_ano`, `periodo_mes`, `limite`, `offset`.
- IA opcional: `gerar_relatorio_ia`, `formato_relatorio`, `layout` em compras/vendas.

Rotas criticas:

- `GET /api/nfe/analise/compras`
- `GET /api/nfe/analise/vendas`
- `GET /api/nfe/analise/clientes`
- `GET /api/nfe/analise/fiscal/cfop`
- `GET /api/nfe/analise/fiscal/ncm`
- `GET /api/nfe/analise/fiscal/hierarquia`
- equivalentes em `/api/sped/...`

Exemplo:

```http
GET /api/sped/analise/fiscal/hierarquia?emitente_cnpj=12345678000199&periodo_ano=2026&periodo_mes=1&nivel_atual=estado&limite=100&offset=0
```

Responses principais:

- Compras (`AnaliseComprasResponse`): `status`, `emitente_cnpj`, `periodo_ano`, `periodo_mes`, `total_comprado`, `total_impostos_complementares`, `total_tributos_reforma`, `top_fornecedores_valor`, `top_fornecedores_quantidade`, `top_produtos_valor`, `top_produtos_quantidade`, `relatorio_ia`.
- Vendas (`AnaliseVendasResponse`): `status`, `emitente_cnpj`, `periodo_ano`, `periodo_mes`, `total_vendido`, `total_impostos_complementares`, `total_tributos_reforma`, `top_regioes_valor`, `top_cidades_valor`, `top_clientes_valor`, `top_clientes_quantidade`, `top_produtos_valor`, `top_produtos_quantidade`, `top_cfops_valor`, `relatorio_ia`.
- Clientes (`AnaliseClientesResponse`): `status`, `emitente_cnpj`, `periodo_ano`, `periodo_mes`, `total_vendido`, `total_clientes`, `top_clientes_valor`, `top_clientes_quantidade`, `relatorio_ia`.
- Fiscal CFOP (`AnaliseFiscalCfopResponse`): `status`, `emitente_cnpj`, `periodo_ano`, `periodo_mes`, `total_movimentado`, `total_impostos_complementares`, `total_tributos_reforma`, `quantidade_documentos`, `quantidade_cfops`, `top_categorias`, `top_cfops`.
- Fiscal NCM (`AnaliseFiscalNcmResponse`): `status`, `emitente_cnpj`, `periodo_ano`, `periodo_mes`, `total_movimentado`, `total_impostos_complementares`, `total_tributos_reforma`, `quantidade_documentos`, `quantidade_ncms`, `top_ncms`.
- Hierarquia (`AnaliseFiscalHierarquicaResponse`): `status`, `emitente_cnpj`, `periodo_ano`, `periodo_mes`, `nivel_atual`, `offset`, `limite`, `total_registros_nivel`, `possui_mais_registros`, `total_faturamento`, `total_impostos`, `total_tributos_reforma`, `percentual_impostos_sobre_faturamento`, `quantidade_documentos`, `total_estados`, `total_cidades`, `total_ncms`, `total_produtos`, `hierarquia`, `itens_nivel_atual`, `por_estado`, `por_cidade`, `por_ncm`, `por_produto`.

Erros comuns: `400` parametros invalidos/fluxo errado, `403` CNPJ fora do escopo, `404` sem dados.

## NCM / IBPT

### `POST /api/ncm/ibpt/sincronizar`

- Autenticacao: obrigatoria.
- Body opcional: `uf`, `todas_ufs`, `ncm`.
- Request:

```json
{ "uf": "SC", "todas_ufs": false, "ncm": "01012100" }
```

- Erros comuns: `429` chamada repetida antes do cooldown, `502` falha externa/sincronizacao.
- Response (`IBPTSyncResponse`): `status`, `executado_por`, `total_ufs`, `resultados`; cada resultado possui `uf`, `registros_recebidos`, `catalogo_sincronizado`, `tributacao_sincronizada`.
- Observacao: sincroniza catalogo e tributacao IBPT usados por consultas. Rota nao tem escopo de empresa (catalogo e global) nem role/admin — qualquer usuario autenticado pode disparar. Protegida por cooldown global (`IBPT_SYNC_MIN_INTERVAL_SECONDS`, padrao 300s) para conter abuso/DoS contra a API externa do IBPT; nao substitui um controle de role, que ainda nao existe no sistema.

### `GET /api/ncm/tributacao`

- Query obrigatoria: `codigo`, `uf`.
- Response (`NCMTributacaoResponse`): `status`, `ncm_codigo`, `descricao`, `uf`, `nacional_federal`, `importados_federal`, `estadual`, `municipal`, `vigencia_inicio`, `vigencia_fim`, `versao`, `fonte`, `atualizado_em`.

## Reforma Tributaria

### `GET /api/reforma-tributaria/tributos`

- Query opcional: `incluir_inativos`.
- Response (`ConsultaTributosResponse`): `status`, `total`, `resultados`.
- Item de `resultados`: `id`, `codigo`, `nome`, `esfera`, `tipo`, `descricao`, `ativo`.

### `GET /api/reforma-tributaria/apuracao`

- Query obrigatoria: `emitente_cnpj`.
- Query opcional: `periodo_ano`, `periodo_mes`, `tributo_codigo`.
- Response (`ConsultaApuracaoTributariaResponse`): `status`, `emitente_cnpj`, `periodo_ano`, `periodo_mes`, `total`, `resultados`.
- Item de `resultados`: `id`, `empresa_cnpj`, `periodo_ano`, `periodo_mes`, `tributo_codigo`, `tributo_nome`, `total_debitos`, `total_creditos`, `ajustes_debito`, `ajustes_credito`, `estornos_debito`, `estornos_credito`, `compensacoes`, `saldo_apurado`, `saldo_periodo_anterior`, `saldo_a_recolher`, `status`, `data_fechamento`.

### `GET /api/reforma-tributaria/documentos/{origem_documento}/{documento_id}/tributos`

- Path: `origem_documento` (`nfe` ou `sped`), `documento_id`.
- Query obrigatoria: `emitente_cnpj`.
- Response (`ConsultaDocumentoFiscalTributosResponse`): `status`, `origem_documento`, `documento_id`, `total`, `resultados`.
- Item de `resultados`: `id`, `nota_id`, `sped_documento_id`, `tributo_codigo`, `tributo_nome`, `empresa_cnpj`, `periodo_ano`, `periodo_mes`, `modelo_documento`, `chave_acesso`, `tipo_operacao`, `data_emissao`, `base_calculo`, `valor_debito`, `valor_credito`, `valor_tributo`, `valor_isento`, `valor_outros`, `valor_reducao_base`, `valor_diferido`, `natureza`, `origem`, `status`.

### `GET /api/reforma-tributaria/itens/{origem_item}/{item_id}/tributos`

- Path: `origem_item` (`nfe` ou `sped`), `item_id`.
- Query obrigatoria: `emitente_cnpj`.
- Response (`ConsultaItemDocumentoFiscalTributosResponse`): `status`, `origem_item`, `item_id`, `total`, `resultados`.
- Item de `resultados`: `id`, `documento_tributo_id`, `nota_item_id`, `sped_item_id`, `tributo_codigo`, `tributo_nome`, `empresa_cnpj`, `periodo_ano`, `periodo_mes`, `numero_item`, `produto_codigo`, `ncm_codigo`, `cfop`, `cst_codigo`, `classificacao_tributaria`, `base_calculo`, `aliquota`, `aliquota_federal`, `aliquota_estadual`, `aliquota_municipal`, `percentual_reducao_base`, `percentual_diferimento`, `valor_debito`, `valor_credito`, `valor_tributo`, `valor_isento`, `valor_outros`, `valor_reducao_base`, `valor_diferido`, `valor_credito_presumido`, `natureza`, `origem`, `status`.

### `GET /api/reforma-tributaria/memoria-calculo`

- Query obrigatoria: `emitente_cnpj`.
- Query opcional: `periodo_ano`, `periodo_mes`, `tributo_codigo`, `documento_tributo_id`, `item_tributo_id`, `limite` (1-1000), `offset`.
- Response (`ConsultaMemoriaCalculoTributariaResponse`): `status`, `emitente_cnpj`, `periodo_ano`, `periodo_mes`, `total`, `limite`, `offset`, `resultados`.
- Item de `resultados`: `id`, `documento_tributo_id`, `item_tributo_id`, `credito_tributario_id`, `debito_tributario_id`, `tributo_codigo`, `tributo_nome`, `empresa_cnpj`, `periodo_ano`, `periodo_mes`, `etapa_calculo`, `base_origem`, `base_calculo`, `aliquota_aplicada`, `percentual_reducao_base`, `percentual_diferimento`, `valor_calculado`, `formula_calculo`, `parametros_calculo`, `resultado_calculo`, `fonte_dados`, `hash_calculo`, `criado_em`.
- Observacao: use esta rota para rastrear valores ate documento/item de origem.

## Metas

### `POST /api/metas`

- Autenticacao: sessao ativa. Escopo por `current_user.empresa_id` (sem `empresa_id` de query).
- Body obrigatorio: `indicador_id`, `titulo`, `valor_alvo`, `tipo_meta`, `periodo_tipo`, `periodo_inicio`, `periodo_fim`.
- Body opcional: `descricao`.
- Erros: `400` indicador inexistente/inativo, `422` `periodo_fim < periodo_inicio` ou `valor_alvo <= 0`.

### `GET /api/metas?status=&indicador_id=`

- Lista metas da empresa da sessao, mais recentes primeiro.

### `GET /api/metas/{id}`

- `404` se a meta nao existe ou pertence a outra empresa.

### `GET /api/metas/{id}/analise`

- Retorna `AnaliseMetaResponse`: `percentual_atingido`, `tempo_decorrido_pct`, `status_ritmo` (`no_caminho`/`em_risco`/`fora_da_rota`), `tendencia` (5 faixas), `diagnostico`, `serie_historica`, `projecao_fim_periodo`, `comparativo_ano_anterior_pct` (`null` se historico < 12 meses).

### `PATCH /api/metas/{id}`

- Body opcional: `titulo`, `descricao`, `valor_alvo`, `status`.

### `DELETE /api/metas/{id}`

- Soft delete (`status = 'cancelada'`). Responde `204`.

### `GET /api/indicadores?perfil=xml`

- Catalogo fixo (seed via migration). Nesta fase so `perfil=xml` tem dado.

### `GET /api/indicadores/{id}/historico?meses=12`

- Serie mensal de `indicador_historico`, ordenada por periodo ascendente. Materializada pela task Celery `materializar_indicadores_historico_task` (diaria, 4h) a partir de `notas_kpis`.
