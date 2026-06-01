# Arquitetura Backend

Este guia define o caminho recomendado para evoluir o backend sem voltar a concentrar regra fiscal, SQL, transformacao de dados e contrato HTTP nos mesmos arquivos.

## Objetivo

- Manter rotas finas e previsiveis.
- Centralizar acesso a banco em repositories.
- Separar casos de uso de regras de infraestrutura.
- Reduzir duplicacao entre NFe, SPED e Reforma Tributaria.
- Facilitar testes de caracterizacao antes de refatoracoes.

Para a estrutura alvo de pastas e dominios, consulte `docs/backend-target-structure.md`.
Para o padrao de excecoes, mensagens e status HTTP, consulte `docs/backend-error-handling.md`.
Para convencoes praticas de implementacao, consulte `docs/backend-implementation-conventions.md`.
Para a ordem recomendada de refatoracoes, consulte `docs/backend-refactoring-roadmap.md`.

## Camadas

### `api`

Responsabilidade:

- Receber parametros HTTP.
- Validar dependencias de autorizacao e perfil operacional.
- Chamar services/use cases.
- Converter erros esperados para `HTTPException`.
- Retornar schemas de resposta.

Evitar:

- SQL.
- Conexao direta com banco.
- Montagem extensa de dashboards.
- Regra fiscal.
- Parse de XML/SPED.
- Transformacoes longas de dados.

Exemplos atuais:

- `API/app/api/nfe/routes.py`
- `API/app/api/sped/routes.py`
- `API/app/api/reforma_tributaria/routes.py`
- `API/app/api/shared/company_validation.py`

### `services`

Responsabilidade:

- Orquestrar casos de uso.
- Aplicar regras de aplicacao.
- Chamar repositories e helpers de dominio.
- Coordenar fluxos transacionais quando ainda nao houver use case dedicado.

Evitar:

- Crescer como arquivo unico por dominio.
- Misturar parsing, SQL, DTO e regra fiscal no mesmo metodo.
- Abrir varias conexoes quando uma transacao unica for necessaria.

Services grandes devem ser quebrados gradualmente em:

- helpers puros;
- repositories;
- services menores por caso de uso;
- formatters/builders;
- validators.

Exemplos atuais:

- `API/app/services/shared/compras_dashboard_service.py`
- `API/app/services/shared/analise_relatorio_service.py`
- `API/app/services/shared/ia_report_service.py`
- `API/app/services/reforma_tributaria/xml_helpers.py`

### `repositories`

Responsabilidade:

- Executar consultas SQL.
- Controlar detalhes de persistencia.
- Receber conexao/cursor quando a transacao for coordenada por outro fluxo.
- Retornar dados simples para services.

Evitar:

- `HTTPException`.
- Regra de apresentacao.
- Conhecimento de schemas Pydantic de resposta HTTP.
- Chamadas para OpenAI, jobs ou upload.

Exemplos atuais:

- `API/app/repositories/nfe/notas_repository.py`
- `API/app/repositories/reforma_tributaria/backfill_repository.py`
- `API/app/repositories/reforma_tributaria/resumo_repository.py`
- `API/app/repositories/reforma_tributaria/xml_importado_repository.py`

### `models/schemas`

Responsabilidade:

- Definir contratos de entrada e saida.
- Padronizar response models.
- Manter compatibilidade com o frontend.

Evitar:

- Consulta a banco.
- Regra fiscal.
- Transformacoes complexas.

### `domain`

Responsabilidade:

- Regras puras de dominio.
- Parsing ou extracao sem dependencia de HTTP/banco.
- Funcoes deterministicas e faceis de testar.

Exemplo atual:

- `API/app/domain/nfe/extractor.py`

## Padrao Para Novas Rotas

Uma rota nova deve seguir este fluxo:

1. Resolver autenticacao/escopo.
2. Validar parametros HTTP e perfil operacional.
3. Chamar um service ou use case.
4. Converter excecoes esperadas.
5. Retornar schema.

Modelo recomendado:

```python
@router.get("/exemplo", response_model=ExemploResponse)
def consultar_exemplo(cnpj: str = Query(...)):
  validar_empresa_xml(cnpj)
  try:
    resultado = ExemploService().executar(cnpj=cnpj)
  except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
  return ExemploResponse(status="ok", **resultado)
```

Se a rota precisar de mais de 30 a 40 linhas, revise se alguma responsabilidade deveria estar em service, repository, formatter ou validator.

Erros esperados devem seguir o mapa de status de `docs/backend-error-handling.md`. Em codigo novo, evite criar `HTTPException` dentro de services ou repositories.

## Padrao Para Services

Um service deve ter uma responsabilidade principal.

Aceitavel:

- Orquestrar um fluxo de importacao.
- Montar um dashboard chamando repositories.
- Coordenar uma sincronizacao fiscal.

Sinal de alerta:

- Metodos com SQL longo.
- Varios `psycopg.connect` no mesmo arquivo.
- Parse de XML e escrita em banco no mesmo metodo.
- Montagem de response HTTP dentro do service.
- Condicionais fiscais crescendo por excecoes de cliente/regra.

Ao refatorar services grandes:

1. Adicione teste de caracterizacao.
2. Extraia helpers puros primeiro.
3. Extraia repositories com a mesma query.
4. Preserve assinatura publica do service.
5. Rode a suite rapida.

## Padrao Para Repositories

Repositories podem receber:

- parametros simples;
- `conn` ou `cur` quando o fluxo externo controla transacao;
- um service legado durante transicao, se isso reduzir risco.

Evitar criar repository que:

- instancia FastAPI;
- retorna schema HTTP;
- executa regra de IA;
- altera mais de um agregado sem transacao explicita.

## Padrao Para Testes

Antes de refatorar arquivo P0/P1:

- Criar teste de caracterizacao do contrato atual.
- Testar erro esperado e caminho feliz.
- Usar `monkeypatch` para isolar banco, OpenAI, Redis e Celery.
- Testar helpers puros diretamente.
- Para repositories, validar parametros das queries quando o teste nao usa banco real.

Comando rapido:

```powershell
.\API\.venv-local\Scripts\python.exe -m pytest API/app/tests -q
```

## Checklist Para Novas Funcionalidades

- A rota ficou sem SQL?
- A rota ficou sem regra fiscal extensa?
- O acesso ao banco esta em repository ou service legado controlado?
- Existe teste do contrato HTTP?
- Existe teste do helper puro, se houver regra deterministica?
- A resposta usa schema existente ou novo schema claro?
- O tratamento de erro segue `docs/backend-error-handling.md`?
- Ha duplicacao com NFe/SPED/Reforma Tributaria?
- O arquivo alterado cresceu demais?
- A mudanca preserva compatibilidade com frontend e jobs?

Para revisao de PRs, use tambem `docs/backend-pr-checklist.md`.
Para novas features, use tambem `docs/backend-implementation-conventions.md`.

## Ordem Recomendada Para Refatoracoes Futuras

1. Proteger comportamento com testes.
2. Extrair helpers puros.
3. Extrair repositories.
4. Separar services por caso de uso.
5. Padronizar schemas/formatters.
6. Remover codigo legado nao usado.

Evite reescrita completa. O caminho mais seguro e transformar arquivos grandes em pequenos pontos de responsabilidade ao longo de commits curtos e reversiveis.

Para planejar sprints de refatoracao por dominio, use `docs/backend-refactoring-roadmap.md`.
