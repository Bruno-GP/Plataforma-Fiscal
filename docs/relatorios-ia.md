# Relatorios com IA

Relatorios com IA sao opcionais e usam OpenAI somente quando a query envia `gerar_relatorio_ia=true`.

## Arquivos de referencia no codigo

- `API/app/services/AI/openai_report_service.py`
- `API/app/services/AI/Agents/compras_executivo.txt`
- `API/app/services/AI/Agents/compras_analitico.txt`
- `API/app/services/AI/Agents/vendas_executivo.txt`
- `API/app/services/AI/Agents/vendas_analitico.txt`
- `API/app/services/AI/Agents/clientes_executivo.txt`
- `API/app/services/AI/Agents/clientes_analitico.txt`
- `API/app/api/nfe/routes.py`
- `API/app/api/sped/routes.py`
- `Painel/src/pages/RelatoriosIA.tsx`
- `Painel/src/components/reports/IAReportPreview.tsx`

## Rotas suportadas

NFe/XML:

- `GET /api/nfe/analise/compras`
- `GET /api/nfe/analise/vendas`
- `GET /api/nfe/analise/clientes`

SPED:

- `GET /api/sped/analise/compras`
- `GET /api/sped/analise/vendas`
- `GET /api/sped/analise/clientes`

Parametros:

- `gerar_relatorio_ia`: `true` ou `false`;
- `formato_relatorio`: `executivo` ou `analitico`;
- `layout`: disponivel nas rotas de compras e vendas.

## Implementacao

- Service: `API/app/services/AI/openai_report_service.py`.
- Prompts: `API/app/services/AI/Agents/`.
- Variavel obrigatoria: `OPENAI_API_KEY`.
- Modelo padrao: `OPENAI_REPORT_MODEL`, com fallback `gpt-4o-mini`.
- A implementacao tenta usar `responses.create` e possui fallback para `chat.completions` se necessario.

## Limites e riscos

- O relatorio e apoio analitico, nao parecer fiscal oficial.
- A IA pode interpretar tendencias de forma incorreta ou exagerada.
- A qualidade depende dos dados importados e dos filtros aplicados.
- Dados fiscais sensiveis podem ser enviados para provedor externo.
- Erros de chave, rede, limite ou modelo podem retornar falha `502`/`503` conforme a rota.

## Validacao humana

Antes de usar o relatorio em decisao fiscal, valide:

- periodo;
- CNPJ;
- totais exibidos na tela;
- top clientes/produtos/fornecedores;
- coerencia com documentos fiscais;
- ausencia de conclusoes legais nao suportadas pelos dados.
