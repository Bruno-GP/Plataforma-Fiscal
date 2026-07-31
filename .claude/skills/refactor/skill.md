---
name: refactor
description: >
  Refatoração estratégica de código para Python e TypeScript. Use esta skill SEMPRE que o usuário mencionar refatoração, "arquivo grande", "código confuso", "precisa limpar o código", "muito acoplado", "difícil de manter", "separar responsabilidades", "código duplicado", ou quando pedir para varrer o projeto em busca de arquivos que precisam de atenção. A skill analisa o arquivo (ou o projeto inteiro), monta um plano detalhado com mapa de impacto e estimativa de risco, apresenta tudo para aprovação do usuário, e SÓ executa a refatoração após autorização explícita. Nunca aplica mudanças sem confirmar antes.
---

# Skill: Refatoração Estratégica de Código

## Visão Geral

Esta skill guia uma refatoração completa em duas fases:
1. **Análise** — lê o código, identifica problemas, monta plano + impacto + risco
2. **Execução** — aguarda autorização do usuário e só então aplica as mudanças

O código original é modificado in-place. Não cria arquivos paralelos nem branches — reorganiza o arquivo diretamente, de forma limpa e incremental.

---

## FASE 1 — Análise (sempre primeiro, nunca pule)

### 1A. Modo Arquivo Específico

Quando o usuário indicar um arquivo:

```
Ler o arquivo completo → executar checklist de diagnóstico → gerar relatório
```

### 1B. Modo Varredura do Projeto

Quando o usuário pedir para varrer o projeto:

1. Mapear todos os arquivos `.py` e `.ts`/`.tsx`/`.js` do projeto (excluir `node_modules/`, `venv/`, `.venv/`, `__pycache__/`, `dist/`, `build/`, `.git/`)
2. Para cada arquivo, calcular os critérios abaixo
3. Montar tabela de candidatos ordenada por severidade
4. Perguntar ao usuário qual arquivo quer refatorar primeiro

**Critérios de triagem (qualquer um já classifica como candidato):**
| Critério | Threshold |
|---|---|
| Linhas totais | > 300 |
| Função/método mais longa | > 50 linhas |
| Profundidade de aninhamento (ifs/loops) | > 4 níveis |
| Responsabilidades misturadas | lógica de negócio + I/O + banco na mesma função |
| Código duplicado | blocos ≥ 10 linhas repetidos 2+ vezes |

---

## Checklist de Diagnóstico (para o arquivo escolhido)

Rode mentalmente cada item e registre os achados:

```
[ ] Tamanho total (linhas)
[ ] Número de funções/classes
[ ] Função mais longa (nome + linhas)
[ ] Profundidade máxima de aninhamento
[ ] Responsabilidades identificadas (listar)
[ ] Blocos duplicados (listar pares)
[ ] Imports não utilizados
[ ] Constantes hardcoded que deveriam ser config/env
[ ] Tipos ausentes (TypeScript sem tipagem, Python sem type hints onde seria útil)
[ ] Acoplamento externo (dependências que dificultam teste unitário)
```

---

## Relatório de Análise (formato obrigatório)

Apresente sempre nesta estrutura antes de qualquer mudança:

---

### 📋 Plano de Refatoração — `<nome_do_arquivo>`

**Diagnóstico resumido**
> Uma frase descrevendo o problema central do arquivo.

**Problemas encontrados**
| # | Problema | Localização | Severidade |
|---|---|---|---|
| 1 | Descrição curta | função/linha | 🔴 Alta / 🟡 Média / 🟢 Baixa |

**O que vai mudar**

Para cada mudança planejada:
- **O quê:** descrição da mudança
- **Por quê:** justificativa técnica
- **Como:** estratégia (ex: extrair função, criar módulo separado, substituir lógica duplicada por helper)

**📍 Mapa de Impacto**

Liste cada arquivo externo que importa ou usa o arquivo sendo refatorado:
```
arquivo_sendo_refatorado.py
├── importado por: service_a.py (linha 12), route_b.py (linha 5)
├── função X usada em: controller_c.py (linha 88)
└── efeito esperado: nenhuma assinatura pública será alterada / [ou: as seguintes assinaturas mudarão...]
```

Se nenhuma assinatura pública mudar, deixar explícito: *"Nenhuma interface pública será alterada. Impacto externo: zero."*

**⚠️ Estimativa de Risco**

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Descrição do risco | Baixa/Média/Alta | Como evitar ou reverter |

**Risco geral:** 🟢 Baixo / 🟡 Moderado / 🔴 Alto

---

> 🔒 **Aguardando sua autorização.**
> Digite **CONFIRMAR** para aplicar a refatoração ou **CANCELAR** para abortar.

---

## FASE 2 — Execução (somente após autorização explícita)

### Regras de execução

1. **Nunca executar sem receber "CONFIRMAR"** — se o usuário disser "ok", "pode ir", "faz aí" sem clareza, perguntar: *"Confirmo como CONFIRMAR?"*
2. **Aplicar mudanças de forma incremental** — uma responsabilidade de cada vez, na ordem do plano
3. **Preservar comportamento** — refatoração não é reescrita. Lógica de negócio deve permanecer idêntica
4. **Manter assinaturas públicas** — a menos que o plano aprovado explicitamente preveja mudança de interface
5. **Não apagar comentários úteis** — só remover comentários redundantes (que apenas repetem o que o código já diz)
6. **Testar mentalmente cada extração** — antes de mover um bloco, confirmar que todas as variáveis necessárias estão disponíveis no novo escopo

### Padrões por linguagem

Leia o arquivo de referência da linguagem relevante antes de executar:
- Python → `references/python-patterns.md`
- TypeScript/JavaScript → `references/typescript-patterns.md`

### Relatório pós-execução

Após aplicar todas as mudanças, apresentar:

```
✅ Refatoração concluída — `<nome_do_arquivo>`

Mudanças aplicadas:
  ✔ [descrição breve de cada mudança feita]

Antes × Depois:
  Linhas: 487 → 210 (no arquivo principal)
  Funções: 12 → 9 (3 extraídas para helpers)
  Responsabilidades: 4 → 1

Arquivos criados/modificados:
  • arquivo_principal.py (modificado)
  • helpers/validators.py (criado)   ← se houve extração para novo módulo

Próximos passos sugeridos:
  • Rodar os testes existentes para validar comportamento
  • [qualquer outro ponto relevante identificado durante a execução]
```

---

## Comportamento em Casos Especiais

**Arquivo sem problemas graves:** Apresentar diagnóstico positivo e sugerir apenas melhorias opcionais. Não forçar refatoração onde não é necessária.

**Arquivo gerado automaticamente** (migrations, `__init__.py` simples, arquivos de config): Avisar o usuário antes de qualquer análise.

**Arquivo com testes existentes:** Mencionar explicitamente no mapa de impacto. Sugerir rodar testes antes e depois.

**Arquivo muito grande (+800 linhas):** Sugerir dividir a refatoração em etapas — uma por sessão — para não perder contexto.