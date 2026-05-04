# Reforma Tributaria

Esta documentacao descreve o que existe no codigo. Ela nao representa validacao legal completa da Reforma Tributaria e nao deve ser usada como parecer fiscal.

## Arquivos de referencia no codigo

- `API/migrations/004_add_reforma_tributaria_base.sql`
- `API/migrations/005_add_reforma_tributaria_documentos_itens.sql`
- `API/migrations/006_add_reforma_tributaria_creditos_debitos_memoria.sql`
- `API/app/api/reforma_tributaria/routes.py`
- `API/app/models/reforma_tributaria/schemas.py`
- `API/app/services/reforma_tributaria/reforma_tributaria_consulta_service.py`
- `API/app/services/reforma_tributaria/reforma_tributaria_sync_service.py`
- `API/app/services/nfe/process_nfe.py`
- `API/app/services/sped/sped_importacao_service.py`

## Separacao do que existe

### Apenas estrutura de banco

As migrations criam estrutura para um motor tributario mais amplo:

- regras: `regras_tributarias`, `regras_tributarias_vigencias`;
- aliquotas: `aliquotas_tributarias`;
- ajustes: `ajustes_tributarios`;
- creditos/debitos: `creditos_tributarios`, `debitos_tributarios`;
- memoria: `memoria_calculo_tributaria`.

Fragilidade: existir tabela nao significa existir regra legal carregada, validada ou aplicada.
Na revisao do codigo, nao foi encontrado `INSERT` em `memoria_calculo_tributaria`; a API consulta a tabela, mas a populacao automatica da memoria ainda deve ser tratada como pendente ou dependente de carga externa.

### Cadastro de tributos

A migration `004_add_reforma_tributaria_base.sql` cadastra tributos atuais e de reforma:

- Atuais: `ICMS`, `ICMS_ST`, `IPI`, `PIS`, `COFINS`, `ISS`.
- Reforma: `CBS`, `IBS`, `IBS_UF`, `IBS_MUN`, `IS`.

Esse cadastro alimenta consultas e relacionamentos. Ele nao prova que CBS, IBS ou IS estejam calculados.

### Sincronizado a partir de NFe/XML

`ProcessarNFeService` chama `ReformaTributariaSyncService().sincronizar_nfe_periodo(...)` apos registrar notas por periodo.

O sync NFe trabalha com tributos legados definidos em `TRIBUTOS_LEGADOS_NFE = ("ICMS", "IPI", "PIS", "COFINS")`:

- insere tributos por documento em `documentos_fiscais_tributos`;
- insere tributos por item em `itens_documentos_fiscais_tributos`;
- insere creditos/debitos conforme natureza da operacao;
- atualiza `apuracao_tributaria` por periodo.

Quando o valor por item nao vem diretamente do XML, parte da distribuicao e proporcional ao valor do item no documento. Isso e uma regra operacional do codigo, nao uma validacao fiscal legal.

### Sincronizado a partir de SPED

`SpedImportacaoService.processar_importados` chama:

- `sincronizar_sped_apuracao_icms`;
- `sincronizar_sped_documentos_itens_icms`.

O sync SPED trabalha com `TRIBUTOS_LEGADOS_SPED = ("ICMS",)`:

- copia totais de `sped_apuracao_icms` para `apuracao_tributaria`;
- distribui ICMS para documentos SPED proporcionalmente a partir da apuracao;
- distribui ICMS para itens proporcionalmente ao valor do item no documento;
- gera creditos/debitos ICMS para entradas/saidas.

Isso nao calcula CBS, IBS ou IS.

### Calculado pelo sistema

O sistema calcula ou distribui valores operacionais para tributos legados:

- NFe/XML: ICMS, IPI, PIS e COFINS, usando valores dos documentos/itens e rateios proporcionais quando necessario.
- SPED: ICMS, usando apuracao SPED e distribuicao proporcional em documentos/itens.

Nao foi encontrado no codigo um motor de regra fiscal que leia `regras_tributarias`, vigencias e aliquotas para calcular CBS/IBS/IS.

### Sem motor fiscal implementado

Nao ha evidencia no codigo de calculo legal completo para:

- CBS;
- IBS;
- IBS_UF;
- IBS_MUN;
- Imposto Seletivo (`IS`);
- transicao entre tributos atuais e novos tributos;
- aplicacao automatica de `regras_tributarias_vigencias` e `aliquotas_tributarias`.

Documente qualquer evolucao nessa area como nova funcionalidade, com testes fiscais e fixtures.

### Depende de dados previamente persistidos

As rotas de Reforma Tributaria sao consultas. Elas dependem de:

- tabelas criadas;
- tributos cadastrados;
- documentos NFe/SPED processados;
- sync de Reforma executado durante o processamento;
- dados de memoria ja gravados, quando houver. Hoje nao foi localizado service que grave automaticamente `memoria_calculo_tributaria`.

Se nao houver processamento previo, a tela pode estar correta ao retornar vazio.

## Finalidade da apuracao

A apuracao consolida valores por empresa, periodo e tributo em `apuracao_tributaria`. A tela e a API exibem:

- debitos;
- creditos;
- ajustes;
- estornos;
- compensacoes;
- saldo apurado;
- saldo anterior;
- saldo a recolher;
- status.

No fluxo SPED, o service sincroniza informacoes de ICMS a partir dos registros processados, especialmente dados de apuracao SPED. Isso nao equivale a apurar automaticamente todos os novos tributos da Reforma.

## Memoria de calculo

A memoria de calculo em `memoria_calculo_tributaria` registra etapas de calculo com base, aliquota, valor, formula, parametros, resultado, fonte e hash. Sua finalidade e rastreabilidade: permitir que um valor exibido na apuracao ou em documento/item seja auditado.

## Relacao entre entidades

- Documento fiscal: NFe/XML (`notas`) ou SPED (`sped_documentos_fiscais`).
- Item fiscal: item da NFe (`notas_itens`) ou item SPED (`sped_documento_itens`).
- Tributo do documento: `documentos_fiscais_tributos`.
- Tributo do item: `itens_documentos_fiscais_tributos`.
- Apuracao: totaliza por empresa, periodo e tributo.
- Memoria: aponta para documento, item, credito ou debito tributario.

## Filtros disponiveis

`GET /api/reforma-tributaria/tributos`

- `incluir_inativos`: inclui tributos inativos.

`GET /api/reforma-tributaria/apuracao`

- obrigatorio: `emitente_cnpj`;
- opcionais: `periodo_ano`, `periodo_mes`, `tributo_codigo`.

`GET /api/reforma-tributaria/memoria-calculo`

- obrigatorio: `emitente_cnpj`;
- opcionais: `periodo_ano`, `periodo_mes`, `tributo_codigo`, `documento_tributo_id`, `item_tributo_id`, `limite`, `offset`.

## Significado operacional dos campos

- Debito: valor a favor do fisco ou devido na operacao, conforme origem registrada.
- Credito: valor aproveitavel ou informativo registrado como credito.
- Ajuste: lancamento que altera debito ou credito fora da composicao direta do documento.
- Saldo: resultado consolidado de debitos, creditos, ajustes, estornos, compensacoes e saldos anteriores conforme dados gravados.
- Status: estado operacional do registro (`aberta`, `fechada`, `retificada`, `cancelada` na apuracao; outros status existem em documentos, itens, creditos e debitos).

## Como auditar um valor

1. Localize a linha em `GET /api/reforma-tributaria/apuracao`.
2. Anote `emitente_cnpj`, `periodo_ano`, `periodo_mes` e `tributo_codigo`.
3. Consulte `GET /api/reforma-tributaria/memoria-calculo` com os mesmos filtros.
4. Para uma memoria com `documento_tributo_id`, consulte o documento correspondente em `documentos_fiscais_tributos`.
5. Para uma memoria com `item_tributo_id`, consulte o item correspondente em `itens_documentos_fiscais_tributos`.
6. Use `nota_id`, `sped_documento_id`, `nota_item_id` ou `sped_item_id` para chegar ao documento/item fiscal original.
7. Compare base, aliquota, formula, fonte e hash com os dados importados.

## Limitacoes atuais

- Nao ha garantia documentada de conformidade legal para CBS, IBS ou IS.
- Regras tributarias, vigencias e aliquotas possuem estrutura de banco, mas a cobertura efetiva depende de dados carregados e services existentes.
- A tela consulta dados ja persistidos; ela nao substitui conferencia fiscal.
- O fluxo XML e SPED tem origens diferentes e podem produzir niveis diferentes de detalhe.
- Valores de memoria e apuracao exigem validacao humana antes de uso fiscal oficial.
