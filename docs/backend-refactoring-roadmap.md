# Roadmap de Refatoracao Backend

Este roadmap orienta como continuar reduzindo debito tecnico depois das fases iniciais, sem reescrita completa e sem quebrar a aplicacao em producao.

Use este documento para planejar sprints de refatoracao, preparar PRs pequenos e decidir a ordem de ataque dos arquivos P0/P1.

## Objetivos

- Reduzir tamanho e acoplamento dos services criticos.
- Centralizar SQL em repositories.
- Remover regra de negocio de rotas.
- Separar transformacao de dados, persistencia e dominio.
- Aumentar cobertura de caracterizacao antes de cada mudanca sensivel.
- Preparar o backend para novas features sem aumentar a divida existente.

## Regras de Execucao

- Um PR deve atacar uma responsabilidade por vez.
- Toda refatoracao em arquivo P0/P1 deve iniciar com teste de caracterizacao.
- Contratos HTTP existentes devem ser preservados.
- Mudancas de schema devem ser separadas de refatoracoes estruturais sempre que possivel.
- Nao mover arquivo grande inteiro sem antes extrair partes testaveis.
- Nao remover metodo legado enquanto houver rota, job ou worker usando a assinatura atual.

## Sequencia Padrao Para Refatorar Um Arquivo Critico

1. Mapear consumidores do arquivo.
2. Criar ou atualizar teste de caracterizacao.
3. Identificar SQL, helpers puros, formatadores e validadores.
4. Extrair helpers puros primeiro.
5. Extrair repositories mantendo a mesma query e parametros.
6. Extrair formatadores/DTOs quando a resposta for complexa.
7. Quebrar o service por caso de uso.
8. Ajustar rotas para ficarem finas, sem mudar contrato.
9. Rodar suite rapida.
10. Remover codigo legado somente quando nao houver mais uso.

## Criterios de Entrada

Antes de iniciar uma refatoracao:

- Fluxo critico esta listado em `docs/backend-debito-tecnico-fase-0.md`.
- Contrato esperado esta coberto por teste ou documentado.
- Dependencias externas foram isoladas com `monkeypatch` quando necessario.
- Existe plano de rollback simples.
- O PR tem escopo que cabe em revisao humana.

## Criterios de Saida

Uma refatoracao pode ser considerada concluida quando:

- Comportamento publico foi preservado.
- Suite rapida passou.
- SQL novo ou movido esta em repository.
- Rotas afetadas continuam sem regra de negocio extensa.
- Service ficou menor ou com responsabilidade mais clara.
- Documentacao foi atualizada se o padrao mudou.
- Nao restou duplicacao nova entre NFe, SPED e Reforma Tributaria.

## Ordem Recomendada Por Dominio

### 1. NFe

Prioridade:

- continuar reduzindo `API/app/services/nfe/nfe_consulta_service.py`;
- mover consultas analiticas restantes para repositories;
- extrair formatadores de dashboard e rankings;
- manter rotas NFe apenas como adaptadores HTTP.

Por que primeiro:

NFe tem alto impacto no produto, varios endpoints protegidos e forte risco de duplicacao com SPED.

### 2. SPED

Prioridade:

- quebrar `API/app/services/sped/sped_consulta_service.py` por caso de uso;
- separar queries de compras, vendas, clientes, CFOP, NCM e hierarquia;
- reduzir `API/app/services/sped/sped_importacao_service.py` separando parsing, staging e persistencia.

Por que depois de NFe:

Boa parte dos padroes extraidos em NFe pode orientar SPED, reduzindo decisoes repetidas.

### 3. Reforma Tributaria

Prioridade:

- continuar extraindo repositories do sync fiscal;
- separar sync NFe e sync SPED quando houver cobertura suficiente;
- manter helpers XML e calculos determinisiticos fora do service principal.

Por que em paralelo controlado:

E uma area fiscal sensivel, mas ja recebeu extracoes iniciais. Deve evoluir com testes de protecao fortes.

### 4. Importacao e Jobs

Prioridade:

- padronizar staging de XML e SPED;
- separar criacao de job, processamento e persistencia;
- garantir que workers chamem services sem repetir regra de rota.

Por que antes de escala:

Importacao e jobs tendem a crescer com volume, filas e reprocessamento.

### 5. Usuarios e Empresas

Prioridade:

- separar repository de login;
- isolar politica de senha, lockout e sessao;
- centralizar regras de escopo e perfil operacional.

Por que com cuidado:

Autenticacao e multiempresa sao areas de alto risco de seguranca. Mudancas exigem testes antes.

### 6. Relatorios e IA

Prioridade:

- separar montagem de prompt, chamada externa e formatacao de resposta;
- padronizar tratamento de indisponibilidade;
- garantir que dados fiscais enviados sejam intencionais e agregados.

Por que depois:

Depende de contratos e erros bem definidos, mas nao deve bloquear a reducao dos services fiscais centrais.

## Tamanho Recomendado Dos PRs

Preferir PRs com:

- ate 5 arquivos de codigo alterados;
- um fluxo principal protegido;
- uma extracao por vez;
- diff revisavel em menos de 30 minutos.

Evitar PRs com:

- mudanca estrutural em NFe e SPED ao mesmo tempo;
- refatoracao e regra fiscal nova misturadas;
- migration e mudanca de comportamento no mesmo pacote;
- renomeacao em massa sem necessidade funcional.

## Matriz de Risco

| Tipo de mudanca | Risco | Protecao minima |
|---|---|---|
| Extrair helper puro | Baixo | Teste direto do helper |
| Mover SQL para repository mantendo query | Medio | Teste de caracterizacao do service/rota |
| Separar service por caso de uso | Medio/Alto | Teste de caminho feliz e erro esperado |
| Alterar contrato HTTP | Alto | Teste de contrato e alinhamento com frontend |
| Alterar importacao/processamento | Alto | Teste de job, staging e persistencia esperada |
| Alterar auth/empresa | Alto | Teste de permissao, sessao e escopo |
| Alterar regra fiscal | Alto | Teste com exemplo fiscal representativo |

## Plano de Rollback

Para cada PR de refatoracao:

- preservar assinatura publica ate a migracao terminar;
- manter fachada temporaria quando quebrar service grande;
- evitar alteracao de schema no mesmo PR;
- registrar comando de teste executado;
- garantir que o commit possa ser revertido sem migracao manual.

## Indicadores de Progresso

A reducao de debito esta funcionando quando:

- services P0/P1 param de crescer;
- novas queries aparecem em repositories;
- rotas deixam de receber SQL novo;
- helpers puros ganham testes diretos;
- duplicacao entre NFe e SPED diminui;
- novas features passam pelo checklist antes do merge.

## Proximos Alvos Recomendados

1. `API/app/services/nfe/nfe_consulta_service.py`
2. `API/app/services/sped/sped_consulta_service.py`
3. `API/app/services/sped/sped_importacao_service.py`
4. `API/app/services/reforma_tributaria/reforma_tributaria_sync_service.py`
5. `API/app/services/nfe/auth/login_service.py`
