# Enriquecimento de CNPJ e recomendacao de indicadores por CNAE

## Visao geral

A ideia e transformar o cadastro da empresa em um ponto de partida inteligente para a Plataforma Fiscal.

Ao informar o CNPJ, a plataforma deve buscar dados cadastrais da empresa, identificar o CNAE principal e os CNAEs secundarios, classificar o tipo de negocio e sugerir os indicadores mais relevantes para acompanhamento inicial.

O CNAE nao deve ser tratado como verdade absoluta sobre a operacao real da empresa. Ele deve ser usado como primeiro sinal, complementado por confirmacao do usuario e, depois, pelos dados reais de XML, SPED, SEFAZ, Conta Azul e metas.

## Objetivos

- Reduzir friccao no cadastro da empresa.
- Preencher automaticamente dados cadastrais basicos sempre que possivel.
- Usar CNAE para montar um painel inicial coerente com o segmento do negocio.
- Reaproveitar o modulo existente de `indicadores`, `indicador_historico` e `metas`.
- Permitir que o usuario aceite, remova ou ajuste indicadores recomendados.
- Preparar a base para recomendacoes futuras mais inteligentes, usando dados fiscais e operacionais reais.

## Nao objetivos iniciais

- Emitir parecer fiscal ou tributario automatico.
- Inferir regime tributario quando a fonte cadastral nao fornecer dado confiavel.
- Criar recomendacao 100% automatica sem revisao ou confirmacao do usuario.
- Depender exclusivamente de IA para decidir indicadores.
- Construir benchmark setorial externo no MVP.

## Estado atual relacionado

O projeto ja possui uma base boa para evoluir este recurso:

- Cadastro e login de empresa em `POST /api/auth/registrar`.
- Perfil da empresa em `GET /api/auth/perfil`.
- Tabela `empresas`, usada como base de escopo por `empresa_id` e CNPJ.
- Catalogo de indicadores em `indicadores`.
- Historico materializado em `indicador_historico`.
- Metas por empresa em `metas`.
- Endpoints existentes:
  - `GET /api/indicadores?perfil=xml`
  - `GET /api/indicadores/{indicador_id}/historico`
  - `POST /api/metas`
  - `GET /api/metas`
  - `GET /api/metas/{meta_id}/analise`

O novo recurso deve nascer integrado a esse desenho, adicionando uma camada de enriquecimento cadastral e recomendacao.

## Fluxo desejado

1. Usuario informa o CNPJ no cadastro.
2. Backend normaliza e valida o CNPJ.
3. Backend consulta uma fonte externa de dados cadastrais.
4. Sistema salva um snapshot dos dados retornados.
5. Sistema extrai CNAE principal, CNAEs secundarios, razao social, nome fantasia, porte, natureza juridica, municipio e UF.
6. Sistema classifica a empresa em um segmento operacional interno.
7. Sistema busca os indicadores recomendados para esse segmento.
8. Frontend apresenta uma etapa de confirmacao:
   - dados cadastrais encontrados;
   - segmento sugerido;
   - indicadores sugeridos;
   - opcao para continuar mesmo se a consulta falhar.
9. Ao finalizar o cadastro, a plataforma salva as recomendacoes aceitas para a empresa.
10. Dashboard/metas usam essas recomendacoes como painel inicial.

## Fontes de dados de CNPJ

Para o objetivo inicial deste recurso, a unica informacao obrigatoria da consulta oficial e o CNAE principal.

Referencia oficial:

- `cnaePrincipal(3)` na API Consulta CNPJ da Receita Federal/Conecta: https://www.gov.br/conecta/catalogo/apis/consulta-cnpj/swagger_api_cnpj.md/swagger_view#section/Retorno/cnaePrincipal(3)

Campo critico:

```json
{
  "cnaePrincipal": {
    "codigo": "string",
    "descricao": "string"
  }
}
```

A regra de negocio do MVP deve depender principalmente de `cnaePrincipal.codigo`. A descricao deve ser salva e exibida para transparencia, mas o mapeamento para segmento e indicadores deve usar o codigo.

Fluxo minimo:

```text
CNPJ -> cnaePrincipal.codigo -> segmento interno -> indicadores recomendados
```

Campos opcionais que podem melhorar a experiencia, mas nao devem ser obrigatorios no MVP:

- `ni`, para conferir o CNPJ retornado;
- `nomeEmpresarial`, para preencher a razao social;
- `nomeFantasia`, para preencher nome de exibicao;
- `cnaeSecundarias`, para refinamento futuro;
- `porte`, `naturezaJuridica`, municipio e UF, para enriquecimento cadastral.

O sistema deve usar uma interface interna, sem acoplar o cadastro diretamente a um provedor especifico. Mesmo usando a API oficial da Receita/Conecta, o restante da aplicacao deve depender apenas do contrato normalizado interno.

Servico sugerido:

- `CnpjEnrichmentService`

Contrato conceitual:

```python
class CnpjEnrichmentService:
    def consultar(self, cnpj: str) -> CnpjEnrichmentResult:
        ...
```

Resultado minimo esperado:

```json
{
  "cnpj": "12345678000199",
  "cnae_principal": {
    "codigo": "4711302",
    "descricao": "Comercio varejista de mercadorias em geral..."
  },
  "fonte": "receita_conecta",
  "consultado_em": "2026-08-19T00:00:00Z"
}
```

Resultado enriquecido opcional:

```json
{
  "cnpj": "12345678000199",
  "razao_social": "Empresa Exemplo Ltda",
  "nome_fantasia": "Empresa Exemplo",
  "situacao_cadastral": "ativa",
  "porte": "ME",
  "natureza_juridica": "2062",
  "cnae_principal": {
    "codigo": "4711302",
    "descricao": "Comercio varejista de mercadorias em geral..."
  },
  "cnaes_secundarios": [
    {
      "codigo": "4721102",
      "descricao": "Padaria e confeitaria..."
    }
  ],
  "endereco": {
    "uf": "SP",
    "municipio": "Sao Paulo",
    "codigo_ibge": "3550308"
  },
  "fonte": "provedor_configurado",
  "consultado_em": "2026-08-19T00:00:00Z"
}
```

Requisitos para escolha do provedor:

- permitir consulta por CNPJ;
- retornar `cnaePrincipal.codigo` e `cnaePrincipal.descricao`;
- ter limites e termos de uso compativeis com producao;
- possuir timeout baixo e falha controlada;
- permitir cache local;
- nao bloquear o cadastro caso esteja indisponivel.

## Modelo de dados sugerido

### `empresa_dados_cadastrais`

Snapshot normalizado do retorno de CNPJ.

Campos sugeridos:

- `id`
- `empresa_id`
- `cnpj`
- `razao_social`
- `nome_fantasia`
- `situacao_cadastral`
- `porte`
- `natureza_juridica`
- `cnae_principal`
- `cnae_principal_descricao`
- `cnaes_secundarios` como `JSONB`
- `uf`
- `municipio`
- `codigo_ibge`
- `fonte`
- `payload_original` como `JSONB`
- `consultado_em`
- `criado_em`
- `atualizado_em`

Restricoes:

- `UNIQUE (empresa_id)`
- indice por `cnpj`
- indice por `cnae_principal`

### `segmentos_cnae`

Mapa interno entre faixas/codigos CNAE e segmentos operacionais da plataforma.

Campos sugeridos:

- `id`
- `segmento_chave`
- `segmento_nome`
- `cnae_prefixo`
- `cnae_codigo`
- `prioridade`
- `ativo`

Exemplos de segmentos:

- `comercio_varejista`
- `comercio_atacadista`
- `servicos_profissionais`
- `industria`
- `transporte_logistica`
- `construcao`
- `saude`
- `educacao`
- `alimentacao`
- `tecnologia`
- `agro`

Regra:

- `cnae_codigo` exato tem prioridade sobre `cnae_prefixo`.
- CNAE principal tem peso maior que CNAEs secundarios.
- Em caso de empate, retornar segmento mais generico e pedir confirmacao ao usuario.

### `indicador_segmento_recomendacao`

Relaciona segmentos internos aos indicadores existentes.

Campos sugeridos:

- `id`
- `segmento_chave`
- `indicador_id`
- `perfil` (`xml`, `sped` ou futuro `ambos`)
- `prioridade`
- `motivo`
- `obrigatorio`
- `ativo`

Exemplo:

```text
segmento_chave=comercio_varejista
indicador=faturamento
prioridade=10
motivo=Base para acompanhar volume de vendas e sazonalidade.
```

### `empresa_indicador_recomendado`

Salva o que foi recomendado, aceito, ocultado ou ajustado por empresa.

Campos sugeridos:

- `id`
- `empresa_id`
- `indicador_id`
- `segmento_chave`
- `origem` (`cnae`, `usuario`, `sistema`, `dados_reais`)
- `status` (`sugerido`, `aceito`, `ocultado`)
- `score`
- `motivo`
- `criado_em`
- `atualizado_em`

Restricao:

- `UNIQUE (empresa_id, indicador_id)`

## Regras iniciais de recomendacao

### Comercio varejista

Indicadores iniciais:

- Faturamento
- Ticket medio
- Quantidade de notas
- ICMS pago
- PIS+COFINS pago
- Top produtos por valor
- Top clientes por valor
- Sazonalidade mensal

Indicadores futuros:

- giro de estoque;
- margem bruta;
- estoque parado;
- inadimplencia;
- vendas por canal;
- recompra de clientes.

### Servicos

Indicadores iniciais:

- Faturamento
- Ticket medio
- Quantidade de notas
- PIS+COFINS pago
- Clientes recorrentes
- Concentracao de receita por cliente

Indicadores futuros:

- margem por contrato;
- folha sobre faturamento;
- retencoes na fonte;
- churn;
- produtividade por colaborador.

### Industria

Indicadores iniciais:

- Faturamento
- ICMS pago
- IPI pago
- PIS+COFINS pago
- Top produtos por valor
- Top NCMs
- CFOPs mais relevantes

Indicadores futuros:

- custo de producao;
- perdas;
- capacidade produtiva;
- credito tributario por insumo;
- margem por produto;
- custo unitario.

### Transporte e logistica

Indicadores iniciais:

- Faturamento
- Quantidade de documentos
- Ticket medio
- ICMS pago
- Top clientes por valor
- Faturamento por UF/cidade

Indicadores futuros:

- custo por rota;
- prazo medio de entrega;
- ocupacao da frota;
- custo de combustivel sobre receita.

## Contratos de API sugeridos

### `GET /api/cnpj/{cnpj}/enriquecer`

Consulta dados do CNPJ e retorna resultado normalizado.

Uso:

- pre-cadastro;
- tela de configuracoes;
- reprocessamento manual.

Resposta de sucesso:

```json
{
  "status": "ok",
  "dados": {
    "cnpj": "12345678000199",
    "razao_social": "Empresa Exemplo Ltda",
    "nome_fantasia": "Empresa Exemplo",
    "cnae_principal": {
      "codigo": "4711302",
      "descricao": "Comercio varejista..."
    },
    "cnaes_secundarios": [],
    "uf": "SP",
    "municipio": "Sao Paulo",
    "codigo_ibge": "3550308"
  }
}
```

Erros esperados:

- `400` CNPJ invalido;
- `404` CNPJ nao encontrado;
- `429` limite do provedor;
- `502` falha do provedor;
- `504` timeout.

### `GET /api/empresas/me/recomendacoes-indicadores`

Retorna recomendacoes para a empresa autenticada.

Resposta:

```json
{
  "segmento_sugerido": "comercio_varejista",
  "segmento_nome": "Comercio varejista",
  "fonte": "cnae",
  "indicadores": [
    {
      "indicador_id": 1,
      "chave": "faturamento",
      "nome": "Faturamento",
      "prioridade": 10,
      "status": "sugerido",
      "motivo": "Indicador base para acompanhar volume de vendas."
    }
  ]
}
```

### `PATCH /api/empresas/me/recomendacoes-indicadores`

Permite aceitar, ocultar ou reordenar indicadores recomendados.

Request:

```json
{
  "indicadores": [
    {
      "indicador_id": 1,
      "status": "aceito"
    },
    {
      "indicador_id": 4,
      "status": "ocultado"
    }
  ]
}
```

### Extensao futura em `POST /api/auth/registrar`

O cadastro pode aceitar dados enriquecidos confirmados pelo usuario, sem obrigar que a consulta aconteca dentro da mesma transacao.

Campos opcionais:

```json
{
  "cnpj_enrichment_token": "uuid-ou-hash-do-snapshot",
  "segmento_confirmado": "comercio_varejista",
  "indicadores_aceitos": [1, 2, 3]
}
```

## Backend: componentes sugeridos

### Services

- `app/services/cnpj/cnpj_enrichment_service.py`
- `app/services/cnpj/cnpj_provider_client.py`
- `app/services/cnpj/cnae_classifier_service.py`
- `app/services/metas/indicador_recommendation_service.py`

### Repositories

- `app/repositories/cnpj/empresa_dados_cadastrais_repository.py`
- `app/repositories/cnpj/segmentos_cnae_repository.py`
- `app/repositories/metas/indicador_recomendacoes_repository.py`

### API

- `app/api/cnpj/routes.py`
- `app/api/empresas/recomendacoes_routes.py`

### Schemas

- `app/models/cnpj/schemas.py`
- extensoes em `app/models/metas/schemas.py` se a resposta reusar `IndicadorResponse`.

## Frontend: experiencia sugerida

### Cadastro

Quando o usuario digitar um CNPJ valido:

- mostrar estado de carregamento discreto;
- preencher razao social, cidade e UF quando encontrados;
- exibir CNAE principal;
- sugerir segmento;
- exibir indicadores sugeridos com checkbox/toggle;
- permitir continuar se a consulta falhar.

Importante:

- nao bloquear cadastro por indisponibilidade de fonte externa;
- indicar que os dados devem ser conferidos pelo usuario;
- permitir edicao manual de nome, cidade e UF.

### Configuracoes

Adicionar uma area "Dados cadastrais e segmento":

- dados vindos do CNPJ;
- data da ultima consulta;
- botao para atualizar dados cadastrais;
- segmento atual;
- indicadores recomendados ativos/ocultos.

### Metas e dashboard

Usar recomendacoes para:

- ordenar indicadores sugeridos;
- destacar os principais indicadores ao criar meta;
- montar um painel inicial antes de o usuario configurar metas manualmente.

## MVP recomendado

Premissa do MVP:

- a informacao obrigatoria e `cnaePrincipal.codigo`;
- `cnaePrincipal.descricao` deve ser armazenada para exibicao e auditoria;
- dados como endereco, porte, natureza juridica, Simples Nacional, inscricoes estaduais e QSA ficam fora do caminho critico;
- CNAEs secundarios podem ser armazenados se vierem no retorno, mas nao devem bloquear nem complicar a primeira versao.

### Fase 1: base tecnica

- Criar tabelas:
  - `empresa_dados_cadastrais`;
  - `segmentos_cnae`;
  - `indicador_segmento_recomendacao`;
  - `empresa_indicador_recomendado`.
- Criar `CnpjEnrichmentService` com interface de provedor.
- Implementar cache por CNPJ.
- Criar classificador simples por `cnaePrincipal.codigo`.
- Criar seed inicial de segmentos e recomendacoes.
- Criar testes unitarios para:
  - normalizacao de CNPJ;
  - tratamento de falha do provedor;
  - classificacao por CNAE principal;
  - recomendacao por segmento.

### Fase 2: API e integracao com cadastro

- Criar `GET /api/cnpj/{cnpj}/enriquecer`.
- Criar endpoint autenticado de recomendacoes da empresa.
- Integrar cadastro do frontend com pre-busca de CNPJ.
- Persistir pelo menos CNPJ, `cnaePrincipal.codigo`, `cnaePrincipal.descricao`, fonte e data da consulta ao concluir cadastro.
- Se a consulta falhar, permitir cadastro manual.

### Fase 3: UX de recomendacoes

- Criar tela/componente de confirmacao no cadastro.
- Exibir lista de indicadores sugeridos.
- Permitir aceitar/ocultar indicadores.
- Usar recomendacoes aceitas na tela de metas.
- Ajustar `GET /api/indicadores` para suportar ordenacao por recomendacao da empresa, sem quebrar contrato atual.

### Fase 4: inteligencia incremental

- Ajustar recomendacoes com base nos dados importados.
- Detectar divergencia entre CNAE e operacao real.
- Sugerir indicadores adicionais apos primeiro processamento de XML/SPED.
- Exibir motivos mais ricos:
  - "CNAE de comercio varejista";
  - "empresa possui vendas em varios estados";
  - "concentracao alta em poucos clientes";
  - "volume relevante de ICMS/IPI".

## Ordem de implementacao recomendada

1. Criar migracao de tabelas e seeds.
2. Criar schemas e repositories.
3. Criar classificador de CNAE puro, sem rede.
4. Criar recomendador de indicadores puro, sem rede.
5. Criar cliente de provedor de CNPJ atras de interface.
6. Criar endpoint de enriquecimento.
7. Integrar com cadastro do frontend.
8. Integrar recomendacoes com indicadores/metas.
9. Adicionar reprocessamento nas configuracoes.
10. Expandir regras por segmento.

## Riscos e cuidados

- CNAE pode estar desatualizado ou nao representar a operacao real.
- Fonte externa pode ter limite, custo, instabilidade ou termos restritivos.
- Dados cadastrais podem conter informacoes pessoais em algumas situacoes; tratar com cuidado de LGPD.
- Recomendacoes nao devem ser apresentadas como obrigacoes fiscais.
- Cadastro nao pode depender de rede externa para funcionar.
- E preciso guardar `fonte`, `consultado_em` e, se possivel, o payload original para auditoria.
- Dados enriquecidos devem respeitar o escopo da empresa autenticada.

## Criterios de aceite do MVP

- Ao informar CNPJ valido, o sistema tenta buscar dados cadastrais.
- Se a busca retornar CNAE, o sistema sugere um segmento interno.
- O sistema retorna pelo menos 5 indicadores recomendados para segmentos principais.
- Usuario consegue concluir cadastro mesmo se a busca de CNPJ falhar.
- Recomendacoes aceitas ficam persistidas por empresa.
- Catalogo existente de indicadores continua funcionando sem regressao.
- Testes cobrem sucesso, falha de provedor, CNAE desconhecido e aceite/ocultacao de indicadores.

## Perguntas em aberto

- Qual provedor de consulta de CNPJ sera usado em producao?
- O enriquecimento deve ocorrer antes ou depois de criar a conta?
- O usuario podera trocar o segmento manualmente?
- Recomendacoes aceitas devem criar metas automaticamente ou apenas sugerir indicadores?
- Como tratar empresas com multiplos CNAEs muito diferentes?
- O modulo deve considerar Conta Azul quando a integracao estiver habilitada?

## Decisao recomendada para comecar

Comecar sem IA e sem dependencia forte de provedor externo:

1. Criar o modelo de dados e o classificador local por CNAE.
2. Criar um seed simples de segmentos e indicadores.
3. Criar endpoint de recomendacao baseado em dados ja salvos.
4. Depois plugar o provedor de CNPJ.

Assim a arquitetura nasce testavel e util mesmo quando a fonte externa estiver indisponivel.
