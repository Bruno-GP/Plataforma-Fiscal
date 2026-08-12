# Próximos Passos — Plataforma Fiscal

Gerado em 2026-08-07 a partir de leitura direta do código (`API/`, `Painel/`), documentação em `docs/`, testes e histórico de commits. Nenhuma alteração de código foi feita.

## Nota sobre o pedido original

O prompt que originou este relatório descrevia uma arquitetura de integração com um sistema externo "Plataforma-Matriz" (JWT emitido por ela, webhooks HMAC-assinados com idempotência via Redis, canal de retorno Celery para eventos de uso, `empresa_id` UUID compartilhado). **Essa arquitetura não existe neste repositório.** Confirmado por grep e leitura de código:

- Não há módulo, rota, service ou doc de integração com "Plataforma-Matriz". A única ocorrência de "matriz" no repo é `docs/matriz-xml-sped.md`, que usa a palavra no sentido comum (mapeamento), não como produto externo.
- HMAC existe apenas em `API/app/core/security.py`, para assinar/validar o JWT interno de login (`hmac.new(...)`, `hmac.compare_digest(...)`) — não é webhook.
- Não existe endpoint de webhook nem consumidor de webhook no código.
- `empresa_id` é usado como identificador interno normal, não como claim de um sistema de autenticação externo.

Este relatório documenta portanto o **estado real** da Plataforma Fiscal (FastAPI + React, perfis XML/SPED), não a arquitetura descrita no prompt original. Se "Plataforma-Matriz" for um projeto separado ainda não integrado, ele precisa ser apontado explicitamente (repo/caminho) para ser mapeado.

## Estado geral confirmado

- Estrutura backend segue o padrão documentado em `docs/backend-target-structure.md`: `API/app/{api,services,repositories,domain,models,workers}` por domínio (`nfe`, `sped`, `reforma_tributaria`, `ncm`, `jobs`, `geo/municipios`, `auth`, `conta_azul`, `fiscal`, `shared`).
- Nenhum `TODO`/`FIXME`/`NotImplementedError` encontrado em `API/app` nem em `Painel/src` — sinal de que o débito técnico documentado (`docs/backend-debito-tecnico-fase-0.md`) já vem sendo tratado de forma disciplinada (Fases 0 a 4 concluídas, com testes de caracterização).
- Integração Conta Azul existe e está em produção (`API/app/api/conta_azul`, `API/app/services/conta_azul`, `API/integracoes/conta_azul/`, OAuth + sync KPIs via Celery beat), mas **desenvolvimento novo está pausado por decisão do usuário desde 2026-08-06**. Bugs/segurança na integração existente continuam valendo; expansão de escopo não está listada abaixo por causa dessa pausa.
- Suite rápida de testes (`API/app/tests`) tinha, na última rodada documentada (Fase 2), 172 testes passando e 5 pulados.

---

## 🔴 Crítico

| # | O que fazer | Arquivo/Módulo | Complexidade | Dependências |
|---|---|---|---|---|
| 1 | ✅ **Resolvido (2026-08-12).** Reinstaladas dependências do `.venv-local` (`tenacity`, `psycopg2-binary`, `cryptography` fixado 43.0.1). Suite pytest local voltou a coletar; revelou 8 falhas de drift entre código e teste (mensagens de erro genéricas, fallback UF/cidade na hierarquia fiscal, `empresa_tem_conta_azul` faltando nos fakes, vazamento de `app/.env` real em `test_postgres_config.py`), todas corrigidas. Suite: 228 passed, 10 skipped. Commit `2d11c6f`. | `API/.venv-local`, `API/app/tests/*` | Simples | Nenhuma |
| 2 | ✅ **Resolvido (2026-08-12).** Rota `POST /api/ncm/ibpt/sincronizar` agora exige `require_ibpt_sync_admin`: email do usuário autenticado precisa estar na allowlist `IBPT_SYNC_ADMIN_EMAILS` (env var, fail-closed — `403` se ausente/vazia ou email fora da lista). Cooldown (`IBPT_SYNC_MIN_INTERVAL_SECONDS`) continua valendo em conjunto. Documentado em `docs/security.md` e `app/.env.example`. | `API/app/core/security.py`, `API/app/core/config.py`, `API/app/api/ncm/routes.py` | Médio | Nenhuma |

---

## 🟡 Importante

| # | O que fazer | Arquivo/Módulo | Complexidade | Dependências |
|---|---|---|---|---|
| 3 | 🔶 **Em andamento (2026-08-12).** `nfe_consulta_service.py`: extraídos 4 helpers privados (`_montar_rankings_compras`, `_montar_rankings_vendas`, `_montar_dados_dashboard_vendas`, `_montar_dados_hierarquia_fiscal`) dos métodos públicos mais longos (`analisar_compras` 79→62 linhas, `analisar_vendas` 88→62, `consultar_dashboard_vendas` 84→58, `analisar_fiscal_hierarquia` 103→89). Zero mudança de contrato/assinatura pública. Suite: 229 passed, 10 skipped. `_normalizar_top_cidades` (linha 505) segue como código morto, decisão em aberto. Ainda faltam: `sped_consulta_service.py` → `sped_importacao_service.py` → `reforma_tributaria_sync_service.py` → `login_service.py`. | `API/app/services/nfe/nfe_consulta_service.py`, `API/app/services/sped/sped_consulta_service.py`, `API/app/services/sped/sped_importacao_service.py`, `API/app/services/reforma_tributaria/reforma_tributaria_sync_service.py`, `API/app/services/nfe/auth/login_service.py` | Complexo (cada um) | Teste de caracterização antes de cada extração; preservar contratos HTTP listados em `docs/backend-debito-tecnico-fase-0.md` |
| 4 | ✅ **Resolvido (2026-08-12).** Rota `GET /api/nfe/notas` (stub `501`, sem consumidor) removida do roteador. `GET /api/nfe/notas/detalhado` (a rota real, usada pelo Painel) intocada. Atualizado `API/README.md` e `docs/security.md`; removido teste de caracterização obsoleto (`test_nfe_notas_nao_implementado_preserva_501`). `docs/backend-debito-tecnico-fase-0.md` mantido intacto por ser registro histórico de fase já concluída. Suite: 229 passed, 10 skipped. | `API/app/api/nfe/routes.py` | Simples | Nenhuma |
| 5 | Validação legal/fiscal completa da Reforma Tributária (CBS, IBS, IBS_UF, IBS_MUN, IS) segue como lacuna intencional, registrada em `docs/backend-debito-tecnico-fase-0.md` ("Lacunas intencionais deixadas para suites de integração"). Sem isso, a confiabilidade fiscal dos cálculos de Reforma Tributária não está validada ponta a ponta. | `API/app/services/reforma_tributaria/`, `docs/reforma-tributaria.md` | Complexo | Exige revisão fiscal/legal externa, não só técnica |
| 6 | Auditoria de segurança recomendada em `docs/security.md` (login, rejeições de upload, negações de acesso) hoje só existe como log estruturado via `logging` (`API/app/core/audit.py`), sem persistência/consulta dedicada. Se auditoria precisa ser consultável (compliance, investigação de incidente), decidir se log de aplicação é suficiente ou se precisa de tabela/sistema dedicado. | `API/app/core/audit.py` | Médio | Nenhuma |

---

## 🟢 Evolução

| # | O que fazer | Arquivo/Módulo | Complexidade | Dependências |
|---|---|---|---|---|
| 7 | Rodar a suite de testes de integração real com PostgreSQL (`PLATAFORMA_FISCAL_TEST_DATABASE_URL`), Redis/Celery reais e k6 — hoje só rodam sob demanda/manualmente, não fazem parte da suite rápida por design (`docs/testing.md`). Vale automatizar em CI separado se ainda não existe. | `API/app/tests/test_database_schema.py`, `k6-tests/` | Médio | Ambiente descartável de Postgres/Redis |
| 8 | Reativar (ou remover de vez) features com código pronto mas desligado: `ChatWidget` comentado em `Painel/src/components/layout/MainLayout.tsx:12` e rota "Atualizações" em `Painel/src/App.tsx`. Código morto comentado tende a apodrecer sem uso — decidir reativar ou excluir. | `Painel/src/components/layout/MainLayout.tsx`, `Painel/src/App.tsx` | Simples | Nenhuma |
| 9 | Rate limiting de login/upload é recomendado em `docs/security.md` para produção mas fica a cargo de proxy/infraestrutura — confirmar se já está configurado no ambiente de produção real (fora do escopo deste repo) ou se falta implementar no nível de infra. | Infraestrutura (fora do código da API) | Médio | Depende do provedor de infra usado em produção |
| 10 | `GET /api/reforma-tributaria/tributos` usa `require_company_scope` mas não recebe parâmetro de CNPJ (catálogo global) — comportamento correto hoje, mas vale documentar explicitamente essa exceção junto às demais rotas globais (`docs/security.md` já lista, mas o padrão "catálogo global vs rota por empresa" poderia virar convenção formal no checklist de PR). | `docs/backend-pr-checklist.md` | Simples | Nenhuma |

---

## Fora de escopo por decisão já tomada

- **Conta Azul**: qualquer expansão (novos endpoints, novas telas, novos KPIs) está pausada desde 2026-08-06 por decisão do usuário. Retomar apenas quando o tópico for reaberto explicitamente.
