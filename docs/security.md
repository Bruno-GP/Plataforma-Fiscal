# Seguranca

## Arquivos de referencia no codigo

- `API/app/core/security.py`
- `API/app/core/upload_security.py`
- `API/app/core/config.py`
- `API/app/core/audit.py`
- `API/app/api/nfe/routes.py`
- `API/app/api/sped/routes.py`
- `API/app/api/ncm/routes.py`
- `API/app/api/reforma_tributaria/routes.py`
- `Painel/src/contexts/AuthContext.tsx`
- `Painel/src/services/api.ts`

## Autenticacao e sessao

A API emite JWT HS256 com dados de usuario e empresa. O token pode ser enviado por:

- cookie HttpOnly configurado por `set_auth_cookie`;
- header `Authorization: Bearer <token>`.

O frontend persiste dados de sessao em `localStorage` para hidratar a UI (`Painel/src/contexts/AuthContext.tsx` e `Painel/src/services/api.ts`). Isso melhora a experiencia, mas traz risco em caso de XSS: dados de usuario e CNPJ podem ser lidos por scripts maliciosos. O token sensivel deve permanecer no cookie HttpOnly.

## Autorizacao por empresa

Rotas fiscais usam `require_company_scope`, que compara os parametros `emitente_cnpj`, `cnpj_emitente` e `cnpj_empresa_origem` com o CNPJ do usuario autenticado. Divergencia retorna `403`.

Limitacao atual: a verificacao depende dos parametros de query. Endpoints ou services novos devem usar o mesmo mecanismo ou receber explicitamente o usuario autenticado para evitar vazamento multiempresa.

## Matriz de autenticacao e escopo das rotas fiscais

Todas as rotas abaixo estao em roteadores com dependencia de autenticacao. O escopo multiempresa e mais forte quando a rota recebe `emitente_cnpj`, `cnpj_emitente`, `cnpj_empresa_origem` ou `email`, porque `require_company_scope` compara esses parametros contra a sessao.

| Rota | Exige autenticacao | Exige escopo de empresa | Parametro usado para escopo | Risco/observacao |
| --- | --- | --- | --- | --- |
| `POST /api/nfe/processar` | Sim | Parcial | Nenhum parametro de query | Fragil: usa `require_company_scope`, mas a rota batch recebe apenas body com pasta; nao ha CNPJ em query para comparacao direta. |
| `POST /api/nfe/xml/importar` | Sim | Sim | `cnpj_empresa_origem` | Tambem valida `tem_sped=false` e CNPJ do XML. |
| `GET /api/nfe/xml/pendencias` | Sim | Sim | `cnpj_emitente` | Tambem valida `tem_sped=false`. |
| `POST /api/nfe/xml/processar-importados` | Sim | Sim | `cnpj_emitente` | Tambem valida `tem_sped=false`. |
| `GET /api/nfe/kpis` | Sim | Parcial | `emitente_cnpj` ou `email` quando enviados | Se nenhum parametro for enviado, o service resolve pela sessao, mas o escopo nao e comparado via query. |
| `GET /api/nfe/analise/compras` | Sim | Parcial | `emitente_cnpj` ou `email` quando enviados | Mesmo risco das rotas NFe que permitem resolver por sessao. |
| `GET /api/nfe/analise/vendas` | Sim | Parcial | `emitente_cnpj` ou `email` quando enviados | Mesmo risco das rotas NFe que permitem resolver por sessao. |
| `GET /api/nfe/analise/clientes` | Sim | Parcial | `emitente_cnpj` ou `email` quando enviados | Mesmo risco das rotas NFe que permitem resolver por sessao. |
| `GET /api/nfe/analise/fiscal/cfop` | Sim | Parcial | `emitente_cnpj` ou `email` quando enviados | Mesmo risco das rotas NFe que permitem resolver por sessao. |
| `GET /api/nfe/analise/fiscal/ncm` | Sim | Parcial | `emitente_cnpj` ou `email` quando enviados | Mesmo risco das rotas NFe que permitem resolver por sessao. |
| `GET /api/nfe/analise/fiscal/hierarquia` | Sim | Parcial | `emitente_cnpj` ou `email` quando enviados | Filtros de drill-down nao sao escopo de empresa. |
| `GET /api/nfe/analise/compras/dashboard` | Sim | Parcial | `emitente_cnpj` ou `email` quando enviados | Mesmo risco das rotas NFe que permitem resolver por sessao. |
| `GET /api/nfe/analise/vendas/dashboard` | Sim | Parcial | `emitente_cnpj` ou `email` quando enviados | Mesmo risco das rotas NFe que permitem resolver por sessao. |
| `GET /api/nfe/kpis/comparativo` | Sim | Parcial | `emitente_cnpj` ou `email` quando enviados | Periodo nao participa do escopo. |
| `GET /api/nfe/kpis/comparativo/atual` | Sim | Parcial | `emitente_cnpj` ou `email` quando enviados | Depende da resolucao por sessao. |
| `GET /api/nfe/notas` | Sim | Parcial | `emitente_cnpj` quando enviado | O codigo possui comentario indicando service detalhado incompleto. |
| `GET /api/nfe/notas/detalhado` | Sim | Parcial | `emitente_cnpj` ou `email` quando enviados | Depende da resolucao por sessao. |
| `POST /api/sped/processar` | Sim | Parcial | Nenhum parametro de query | Fragil: rota batch recebe caminho no body e nao valida CNPJ/perfil por query. |
| `POST /api/sped/importar` | Sim | Sim | `cnpj_empresa_origem` | Tambem valida `tem_sped=true` e CNPJ do registro `0000`. |
| `GET /api/sped/pendencias` | Sim | Sim | `cnpj_emitente` | Tambem valida `tem_sped=true`. |
| `POST /api/sped/processar-importados` | Sim | Sim | `cnpj_emitente` | Tambem valida `tem_sped=true`. |
| `GET /api/sped/kpis` | Sim | Sim | `emitente_cnpj` | Valida `tem_sped=true`. |
| `GET /api/sped/clientes` | Sim | Sim | `emitente_cnpj` | Endpoint legado/auxiliar de clientes SPED. |
| `GET /api/sped/analise/*` | Sim | Sim | `emitente_cnpj` | Inclui compras, vendas, clientes, fiscal CFOP/NCM/hierarquia. |
| `GET /api/sped/analise/*/dashboard` | Sim | Sim | `emitente_cnpj` | Inclui dashboards de compras e vendas. |
| `POST /api/ncm/ibpt/sincronizar` | Sim | Nao | Nenhum CNPJ | Usa `get_current_user`, mas a operacao e global de catalogo/IBPT. Risco: qualquer usuario autenticado consegue disparar sincronizacao. |
| `GET /api/ncm/tributacao` | Sim | Nao | Nenhum CNPJ | Consulta global por NCM/UF. |
| `GET /api/reforma-tributaria/tributos` | Sim | Parcial | Nenhum CNPJ | Catalogo global; usa `require_company_scope`, mas nao ha parametro de empresa. |
| `GET /api/reforma-tributaria/apuracao` | Sim | Sim | `emitente_cnpj` | Consulta por empresa. |
| `GET /api/reforma-tributaria/documentos/{origem_documento}/{documento_id}/tributos` | Sim | Sim | `emitente_cnpj` | Origem aceita apenas `nfe` ou `sped`. |
| `GET /api/reforma-tributaria/itens/{origem_item}/{item_id}/tributos` | Sim | Sim | `emitente_cnpj` | Origem aceita apenas `nfe` ou `sped`. |
| `GET /api/reforma-tributaria/memoria-calculo` | Sim | Sim | `emitente_cnpj` | Limite maximo de pagina: 1000. |

## CORS

Configuracoes:

- `CORS_ALLOW_ORIGINS`;
- `CORS_ALLOW_CREDENTIALS`;
- `CORS_ALLOW_ORIGIN_REGEX`.

Em producao, a API exige origem ou regex configurada. Se `CORS_ALLOW_ORIGINS=*`, credenciais sao desabilitadas. Recomenda-se listar apenas dominios do painel.

## Uploads

Arquivos passam por validacao de extensao, tamanho e conteudo minimo:

- XML: `.xml`, nao vazio, limite por arquivo `UPLOAD_MAX_XML_BYTES`, limite total `UPLOAD_MAX_TOTAL_BYTES`, conteudo iniciando como XML.
- SPED: `.txt`, nao vazio, limite por arquivo `UPLOAD_MAX_TXT_BYTES`, limite total `UPLOAD_MAX_TOTAL_BYTES`, conteudo textual.

Riscos restantes:

- validacao nao equivale a antivirus;
- XML malformado e rejeitado, mas XML semanticamente incorreto pode falhar depois no processamento;
- arquivos ficam persistidos em staging no banco ate processamento.

## Variaveis sensiveis

Obrigatorias ou sensiveis em producao:

- `AUTH_SECRET_KEY`: trocar o valor padrao `dev-secret-change-me`.
- `POSTGRES_PASSWORD` e credenciais SPED.
- `OPENAI_API_KEY`, quando relatorios IA forem usados.
- configuracoes de cookie: `AUTH_COOKIE_SECURE`, `AUTH_COOKIE_SAMESITE`, `AUTH_COOKIE_DOMAIN`.

## OpenAI e dados fiscais

Relatorios com IA enviam dados analiticos agregados para a OpenAI quando `gerar_relatorio_ia=true`. Trate CNPJ, clientes, fornecedores, produtos e valores fiscais como dados sensiveis. Antes de habilitar em producao, valide base legal, contrato, politica de retencao e governanca interna.

O relatorio IA e apoio analitico. Ele pode interpretar dados incorretamente e nao substitui revisao humana ou parecer fiscal.

## Recomendacoes para producao

- Definir `APP_ENV=production`.
- Usar `AUTH_SECRET_KEY` forte e rotacionavel.
- Usar HTTPS e `AUTH_COOKIE_SECURE=true`.
- Restringir CORS ao dominio real do painel.
- Evitar expor Swagger publicamente sem controle adicional.
- Aplicar rate limiting em login e upload no proxy ou infraestrutura.
- Registrar auditoria de login, rejeicoes de upload e negacoes de acesso.
- Fazer backup criptografado do banco.
- Revisar qualquer novo endpoint para escopo multiempresa.
