# Padrao de Erros Backend

Este guia define como o backend deve tratar erros esperados, falhas de infraestrutura e respostas HTTP durante a evolucao dos modulos fiscais.

O objetivo e evitar que cada rota ou service escolha status, mensagens e excecoes de forma diferente. Isso reduz regressao no frontend, facilita testes e impede vazamento de detalhes sensiveis.

## Principios

- Rotas convertem erros para HTTP.
- Services e use cases retornam resultado de aplicacao ou levantam excecoes esperadas.
- Repositories nao importam FastAPI e nao levantam `HTTPException`.
- Erros de dominio devem ter mensagens claras para o usuario ou para suporte.
- Erros de infraestrutura devem preservar causa interna em logs, mas retornar mensagem segura.
- Status HTTP devem ser estaveis para contratos ja usados pelo frontend.

## Onde Cada Erro Deve Ficar

### `api`

Responsabilidade:

- Validar parametros HTTP e dependencias de seguranca.
- Converter excecoes esperadas em `HTTPException`.
- Preservar status e formato de resposta usados pelo frontend.

Pode usar:

- `HTTPException`
- `status.HTTP_...`
- mensagens seguras para a API

### `services` e `use_cases`

Responsabilidade:

- Aplicar regra de aplicacao.
- Detectar erro esperado de negocio.
- Levantar excecao de aplicacao ou `ValueError` enquanto o legado ainda nao possui excecoes tipadas.

Evitar:

- `HTTPException` em codigo novo.
- Detalhes de banco na mensagem.
- Misturar captura de infraestrutura com formatacao HTTP.

Observacao de transicao:

Alguns services atuais ainda levantam `HTTPException`. Esse comportamento deve ser preservado ate haver teste de caracterizacao, mas novas mudancas devem preferir excecoes de aplicacao convertidas na camada `api`.

### `repositories`

Responsabilidade:

- Executar SQL.
- Propagar erro de banco para o chamador ou encapsular futuramente em excecao de infraestrutura.

Evitar:

- `HTTPException`.
- Schema Pydantic de resposta.
- Mensagem para usuario final.
- Tratamento generico que esconda falhas reais de persistencia.

## Mapa de Status HTTP

| Status | Quando usar | Exemplos |
|---|---|---|
| `400` | Entrada invalida ou regra de negocio esperada | CNPJ invalido, periodo invalido, arquivo fora do padrao |
| `401` | Falha de autenticacao | Login invalido, sessao ausente ou expirada |
| `403` | Usuario autenticado sem permissao/escopo | Empresa fora do escopo do usuario |
| `404` | Recurso esperado nao encontrado | Job inexistente, periodo sem dados quando o contrato atual usa 404 |
| `409` | Conflito de estado ou duplicidade | Importacao duplicada, recurso ja processado |
| `422` | Validacao automatica do FastAPI/Pydantic | Campo obrigatorio ausente, tipo invalido |
| `502` | Dependencia externa falhou | IA, API externa, integracao fora do banco principal |
| `503` | Infraestrutura indisponivel | Banco indisponivel, fila indisponivel, provedor obrigatorio indisponivel |

## Padrao Recomendado em Rotas

```python
@router.get("/exemplo")
def consultar_exemplo(cnpj: str):
    try:
        return ExemploService().executar(cnpj=cnpj)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except psycopg.Error as exc:
        logger.exception("Falha de banco ao consultar exemplo")
        raise HTTPException(
            status_code=503,
            detail="Banco de dados indisponivel no momento.",
        ) from exc
```

## Mensagens de Erro

Mensagens para usuario podem informar:

- campo invalido;
- recurso nao encontrado;
- regra de negocio violada;
- indisponibilidade temporaria;
- acao recomendada simples.

Mensagens para usuario nao devem expor:

- SQL;
- string de conexao;
- token;
- stack trace;
- payload fiscal completo;
- dados de outra empresa;
- detalhes internos de provedor externo.

## Testes Obrigatorios Para Novos Erros

Ao adicionar ou alterar tratamento de erro:

- Teste o status HTTP retornado.
- Teste o `detail` quando ele for consumido pelo frontend.
- Teste que erro de banco vira `503`, quando aplicavel.
- Teste que falha de dependencia externa vira `502` ou `503` conforme o caso.
- Teste que erro de escopo de empresa nao retorna dados de outro CNPJ.

## Refatoracao Gradual

Ordem segura:

1. Criar teste de caracterizacao do erro atual.
2. Extrair erro esperado do service para excecao de aplicacao ou `ValueError`.
3. Converter a excecao na rota.
4. Remover `HTTPException` do service somente depois que a rota estiver protegida.
5. Repetir por fluxo critico, sem mudar todos os modulos de uma vez.

## Sinais de Alerta

- `HTTPException` novo dentro de repository.
- Rota com varios `except Exception`.
- Mensagens diferentes para o mesmo erro em NFe e SPED.
- Erro de banco retornando `500` generico quando o contrato espera indisponibilidade.
- Tratamento que engole erro e retorna lista vazia sem diferenciar ausencia real de falha.
- Service convertendo excecao tecnica em resposta HTTP.
