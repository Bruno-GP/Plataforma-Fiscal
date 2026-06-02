# Impacto Da Reforma Tributaria Na Plataforma

## Resumo executivo

A plataforma atual foi desenhada para o modelo tributario legado e esta fortemente acoplada a:

- tributos atuais de documento e KPI (`ICMS`, `IPI`, `PIS`, `COFINS`);
- classificacao operacional por `CFOP`;
- classificacao de produto por `NCM`;
- enriquecimento tributario por `IBPT` e por UF;
- separacao de fonte entre `XML/NFe` e `SPED`.

Hoje nao existe modelagem explicita para `IBS`, `CBS`, `Imposto Seletivo`, creditos da nova sistematica, split payment ou regras de convivencia entre regime atual e regime novo.

Conclusao: a reforma nao pede apenas novos campos. Ela pede desacoplamento da camada fiscal para que a plataforma suporte mais de um regime ao mesmo tempo, com versionamento por vigencia, origem do dado e granularidade diferente por empresa, documento e item.

## Onde a plataforma esta mais acoplada ao modelo atual

### Backend

- Rotas fiscais e analiticas estao separadas entre `NFe` e `SPED`:
  - `API/app/api/nfe/routes.py`
  - `API/app/api/sped/routes.py`
- Os schemas e KPIs expostos pela API usam tributos legados como contrato:
  - `API/app/models/nfe/schemas.py`
  - `API/app/models/sped/schemas.py`
- As consultas analiticas montam totais e dashboards em cima de `ICMS`, `IPI`, `PIS` e `COFINS`:
  - `API/app/services/nfe/nfe_consulta_service.py`
  - `API/app/services/sped/sped_consulta_service.py`
- O processamento de NFe registra KPIs agregados por periodo antes de qualquer camada de regras versionadas:
  - `API/app/services/nfe/process_nfe.py`
- O SPED possui estrutura explicita para apuracao de `ICMS`, o que mostra acoplamento ainda maior ao regime atual:
  - `API/app/services/sped/sped_importacao_service.py`
- O enriquecimento de NCM hoje usa tabela IBPT com foco em carga tributaria estimada por federacao:
  - `API/app/api/ncm/routes.py`
  - `API/app/services/NCM/ibpt_sync_service.py`
  - `API/migrations/002_add_ncm_tributacao.sql`

### Frontend

- O painel consome contratos separados para `NFe` e `SPED` e replica o mesmo shape fiscal em ambos:
  - `Painel/src/services/nfe.ts`
  - `Painel/src/services/sped.ts`
- A pagina de analise fiscal foi desenhada como drill-down por `Estado > Cidade > NCM > Produto`, usando `faturamento`, `imposto_valor` e `imposto_percentual`:
  - `Painel/src/pages/AnaliseFiscalCfop.tsx`
- O produto atual trata o fiscal principalmente como:
  - importacao;
  - processamento;
  - KPI historico;
  - ranking por `CFOP` e `NCM`;
  - percentual de imposto sobre faturamento.

## O que a reforma muda para a plataforma

### 1. O conceito de imposto muda

Hoje o sistema expõe tributos separados e fixos no contrato. Com a reforma, a plataforma precisa suportar:

- novos tributos principais (`IBS` e `CBS`);
- convivencia temporal com tributos antigos;
- possivel imposto seletivo por mercadoria;
- creditos e debitos em logica diferente da atual;
- composicao tributaria por item, operacao, regime e vigencia.

Impacto: campos fixos como `total_icms`, `total_ipi`, `total_pis` e `total_cofins` deixam de ser suficientes como modelo principal.

### 2. CFOP e NCM continuam importantes, mas deixam de bastar

`CFOP` e `NCM` seguem relevantes para classificacao, compliance e analise. Mas a plataforma nao pode depender deles como eixo unico de interpretacao tributaria.

Impacto:

- regras fiscais passam a depender mais de vigencia, natureza da operacao, regime e configuracao da empresa;
- `NCM + UF` enriquecido por `IBPT` ajuda em inteligencia, mas nao substitui motor de regras;
- dashboards por `CFOP` continuam uteis, mas deixam de representar a camada principal de calculo.

### 3. KPI fiscal vira estrutura extensivel

Hoje o KPI fiscal e um contrato fechado. A reforma exige um contrato aberto, por exemplo:

- totais por tributo;
- totais por familia de tributo;
- creditos, debitos, saldo e recolhimento;
- vigencia e fonte do calculo;
- comparacao entre regime legado e novo.

Impacto: API, banco e frontend precisam migrar de colunas nomeadas por tributo para colecoes tipadas e versionadas.

### 4. A plataforma precisara rodar dois mundos em paralelo

Nao basta trocar o modelo de uma vez. O produto precisa operar:

- empresas ainda presas ao modelo atual;
- empresas em transicao;
- historico antigo sem recalcule destrutivo;
- relatorios comparativos entre periodos de regimes distintos.

Impacto: versao fiscal passa a ser uma dimensao central da arquitetura.

## Riscos de escalar sem refatorar isso agora

Se adicionarmos `IBS` e `CBS` apenas como novas colunas e novos cards:

- a duplicacao entre `NFe` e `SPED` vai crescer muito;
- cada dashboard vai precisar conhecer tributos individualmente;
- a convivencia entre vigencias vai virar regra espalhada pelo sistema;
- relatorios historicos vao ficar inconsistentes;
- qualquer mudanca legal futura vai exigir refazer API, banco e UI ao mesmo tempo.

## Direcao de arquitetura recomendada

### 1. Criar uma camada fiscal canonica

Introduzir um modelo unico para eventos e resultados fiscais, independente da origem (`NFe` ou `SPED`).

Sugestao minima:

- `fiscal_regime`
- `vigencia_inicio`
- `vigencia_fim`
- `fonte_dado`
- `tributos[]`
- `creditos[]`
- `debitos[]`
- `indicadores[]`

Cada item de `tributos[]` pode conter:

- `codigo`: `ICMS`, `IPI`, `PIS`, `COFINS`, `IBS`, `CBS`, `IS`;
- `grupo`: `consumo`, `federal`, `estadual`, `municipal`, `seletivo`;
- `base_calculo`;
- `aliquota`;
- `valor`;
- `origem_calculo`;
- `vigencia`;

### 2. Separar ingestao de analise

Hoje processamento e KPI estao muito proximos. A recomendacao e dividir em camadas:

1. ingestao bruta;
2. normalizacao fiscal canonica;
3. enriquecimento por catalogos e regras;
4. agregacao analitica;
5. exposicao para UI.

Assim, uma mudanca legal afeta majoritariamente a camada de normalizacao/regras, e nao todas as telas.

### 3. Versionar regras fiscais

Criar tabela ou modulo de regras com:

- regime fiscal;
- periodo de vigencia;
- criterios de aplicacao;
- origem da regra;
- status;
- versao.

Esse ponto e o principal para escalar, porque evita hardcode de regra dentro de query SQL e de componente React.

### 4. Unificar contratos de frontend

Hoje `Painel/src/services/nfe.ts` e `Painel/src/services/sped.ts` repetem quase o mesmo contrato. A direcao ideal e:

- um contrato fiscal comum;
- uma camada de adaptacao por origem;
- componentes que renderizam metricas dinamicas, nao apenas campos fixos.

Exemplo de mudanca de mentalidade:

- de `total_icms` e `total_pis`;
- para `totais_por_tributo['ICMS']` e `totais_por_tributo['CBS']`.

### 5. Tratar IBPT como enriquecimento, nao como motor

A tabela `ncm_tributacao` e util para consulta e contextualizacao, mas nao deve virar a fonte unica da reforma.

Ela deve servir para:

- referencia;
- comparacao;
- explainability;
- apoio comercial e analitico.

Nao para substituir o motor de regras fiscais.

## Roadmap sugerido

### Fase 1. Preparacao de arquitetura

- mapear todos os contratos fixos de tributo na API e no frontend;
- introduzir modelo canonico de tributos;
- adicionar dimensao `regime_fiscal` e `vigencia`;
- criar camada adaptadora para transformar legado em modelo canonico.

### Fase 2. Compatibilidade e transicao

- manter endpoints atuais funcionando;
- expor novos endpoints ou nova versao de resposta com estrutura extensivel;
- publicar dashboards com metrica dinamica por tributo;
- permitir comparar periodo legado vs periodo reforma.

### Fase 3. Regras e automacao

- plugar base de regras versionadas;
- suportar calculo e explainability por item e documento;
- registrar origem do numero exibido na UI;
- preparar alertas e inconsistencias para divergencia de regime e vigencia.

### Fase 4. Escala operacional

- cache de agregacoes por empresa, periodo, regime e origem;
- processamento incremental;
- reprocessamento controlado por mudanca de regra;
- trilha de auditoria para explicar diferencas entre calculos.

## Backlog inicial de alto impacto

- Criar `FiscalMetric` e `FiscalTributo` como contratos comuns na API.
- Refatorar schemas de KPI para suportar colecoes de tributos alem dos campos legados.
- Introduzir uma tabela de configuracao de regime fiscal por empresa.
- Criar uma camada de adaptacao comum para `NFe` e `SPED`.
- Refatorar o painel para renderizar cards e series por metadados de tributo.
- Acrescentar vigencia e fonte em respostas de analise fiscal.
- Isolar regras de classificacao fiscal hoje embutidas em SQL.
- Preparar trilha de comparacao entre apuracao atual e nova.

## Leitura final

Se quisermos escalar a plataforma com seguranca, o caminho nao e "adicionar IBS/CBS". O caminho e transformar o fiscal em plataforma configuravel:

- multi-origem;
- multi-regime;
- multi-vigencia;
- auditavel;
- extensivel por tributo e regra.

Sem isso, cada nova etapa da reforma vai aumentar a duplicacao e a fragilidade do produto.
