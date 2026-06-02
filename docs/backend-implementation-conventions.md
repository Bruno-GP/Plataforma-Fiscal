# Convencoes de Implementacao Backend

Este guia transforma a arquitetura alvo em regras praticas para novas features, refatoracoes e manutencao evolutiva do backend.

Use este documento junto com:

- `docs/backend-architecture.md`
- `docs/backend-target-structure.md`
- `docs/backend-error-handling.md`
- `docs/backend-pr-checklist.md`
- `docs/backend-refactoring-roadmap.md`

## Regra Geral

Todo codigo novo deve ter uma responsabilidade facil de explicar em uma frase.

Se uma funcao precisa consultar banco, aplicar regra fiscal, formatar response e tratar erro HTTP ao mesmo tempo, ela deve ser quebrada antes de crescer.

## Novas Rotas

Rotas devem ser finas.

Permitido:

- Ler parametros de request.
- Usar dependencies de autenticacao, escopo e perfil operacional.
- Chamar um service ou use case.
- Converter erro esperado em `HTTPException`.
- Retornar schema de resposta.

Evitar:

- SQL.
- `psycopg.connect`.
- Loops grandes de transformacao.
- Parse de XML/SPED.
- Regra fiscal.
- Chamadas diretas para OpenAI, Redis, Celery ou banco.

Modelo:

```python
@router.get("/recurso", response_model=RecursoResponse)
def consultar_recurso(cnpj: str = Query(...)):
    try:
        resultado = RecursoService().executar(cnpj=cnpj)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RecursoResponse(**resultado)
```

## Novos Services

Services devem orquestrar casos de uso.

Permitido:

- Coordenar repositories.
- Aplicar regra de aplicacao.
- Chamar helpers puros de dominio.
- Controlar transacao quando o fluxo precisar de atomicidade.
- Montar resultado interno para a rota.

Evitar:

- SQL longo dentro do service.
- Retornar `HTTPException`.
- Misturar importacao, processamento, persistencia e dashboard no mesmo metodo.
- Conhecer detalhes de request/response HTTP.
- Criar dependencias circulares com outros services.

Sinais de alerta:

- Service passando de 300 linhas sem separacao clara.
- Metodo passando de 60 linhas.
- Mais de uma conexao de banco no mesmo caso de uso.
- Mesmo calculo repetido em NFe e SPED.

## Novos Repositories

Repositories devem concentrar acesso ao banco.

Permitido:

- SQL.
- Parametros simples.
- Receber `conn` ou `cur` quando uma transacao externa estiver aberta.
- Retornar dicts, listas, tuplas ou tipos internos simples.

Evitar:

- Importar FastAPI.
- Levantar `HTTPException`.
- Retornar schema HTTP/Pydantic.
- Fazer regra fiscal complexa.
- Chamar services.
- Abrir conexao escondida quando o chamador ja controla transacao.

Modelo:

```python
class RecursoRepository:
    def listar_por_periodo(self, conn, *, cnpj: str, data_inicio: date, data_fim: date) -> list[dict]:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, valor_total
                FROM recursos
                WHERE cnpj = %s
                  AND data_emissao BETWEEN %s AND %s
                """,
                (cnpj, data_inicio, data_fim),
            )
            return cur.fetchall()
```

## Helpers de Dominio

Helpers devem ser puros sempre que possivel.

Bom candidato para helper:

- normalizacao de CNPJ;
- classificacao fiscal;
- calculo deterministico;
- extracao de campos de XML;
- transformacao de estrutura sem I/O.

Evitar:

- abrir conexao;
- ler variavel de ambiente;
- chamar API externa;
- depender de FastAPI.

## Formatadores e DTOs

Use formatadores quando a transformacao for grande demais para a rota ou service.

Formatadores podem:

- converter dicts internos em estrutura de response;
- agrupar totais;
- ordenar rankings;
- padronizar campos opcionais.

Formatadores nao devem:

- consultar banco;
- aplicar regra fiscal nova;
- decidir permissao;
- chamar services.

## Transacoes

Quando um fluxo precisa alterar varias tabelas de forma consistente:

- abra a transacao em um ponto de orquestracao;
- passe `conn` ou `cur` para repositories;
- deixe claro quem faz `commit` e `rollback`;
- evite repositories abrindo conexoes independentes no meio do fluxo.

Exemplos sensiveis:

- processamento de XML importado;
- processamento de SPED;
- backfill de Reforma Tributaria;
- criacao e atualizacao de jobs.

## Testes Para Codigo Novo

Regra minima:

- rota nova: teste de contrato HTTP;
- service novo: teste de caso feliz e erro esperado;
- helper puro: teste direto com entradas representativas;
- repository novo: teste de parametros/resultado ou teste de integracao quando houver banco descartavel;
- erro novo: teste de status HTTP e mensagem relevante.

Antes de refatorar arquivo P0/P1:

- adicione teste de caracterizacao;
- preserve assinatura publica;
- rode a suite rapida;
- faca commit pequeno e reversivel.
- consulte `docs/backend-refactoring-roadmap.md` para criterios de entrada, saida e rollback.

## Nomes e Organizacao

Use nomes orientados a caso de uso ou responsabilidade.

Preferir:

- `NotasRepository`
- `ResumoRepository`
- `XmlImportadoRepository`
- `ProcessarImportacaoService`
- `MontarDashboardComprasService`

Evitar:

- `UtilsService`
- `Manager`
- `Helper` generico para regras de negocio grandes;
- `shared` para regra especifica de um dominio.

## Ordem Recomendada Para Uma Feature Backend

1. Definir contrato HTTP e permissao.
2. Verificar se ja existe service/repository reaproveitavel.
3. Criar ou ajustar repository para SQL novo.
4. Criar service/use case pequeno.
5. Criar helper puro se houver regra deterministica.
6. Converter erros na rota.
7. Adicionar testes minimos.
8. Atualizar documentacao quando contrato ou arquitetura mudar.

## O Que Nao Fazer Agora

- Reescrever todos os services de uma vez.
- Mudar contratos HTTP junto com refatoracao estrutural.
- Trocar tecnologia de persistencia.
- Criar uma camada generica demais antes de haver repeticao real.
- Mover arquivos apenas por organizacao visual sem teste de protecao.

## Criterio de Aceite Para Novas Mudancas

Uma mudanca backend esta pronta quando:

- a rota continua fina;
- SQL novo esta centralizado;
- regra fiscal esta fora da camada HTTP;
- erro esperado tem status claro;
- fluxo principal tem teste;
- nao houve duplicacao evidente com outro dominio;
- o arquivo alterado nao virou novo ponto de concentracao.
