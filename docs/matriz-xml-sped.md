# Matriz XML versus SPED

O campo `tem_sped` define o fluxo operacional esperado da empresa.

## Arquivos de referencia no codigo

- `API/app/services/company_profile_service.py`
- `API/app/api/nfe/routes.py`
- `API/app/api/sped/routes.py`
- `Painel/src/App.tsx`
- `Painel/src/contexts/AuthContext.tsx`
- `Painel/src/services/nfe.ts`
- `Painel/src/services/sped.ts`
- `Painel/src/services/fiscal.ts`
- `Painel/src/services/operations.ts`

| Funcionalidade | `tem_sped=false` | `tem_sped=true` | Observacao |
| --- | --- | --- | --- |
| Importacao XML/NFe | Ativa | Bloqueada/redirecionada | API tambem valida perfil. |
| Importacao SPED | Bloqueada/redirecionada | Ativa | API tambem valida perfil. |
| Pendencias | XML | SPED | Cada fluxo tem staging proprio. |
| Processamento | XML importado | TXT SPED importado | Reprocessamento nao e endpoint publico. |
| Dashboards vendas | NFe | SPED | Mesma tela escolhe service conforme perfil. |
| Dashboards compras | NFe | SPED | Mesma tela escolhe service conforme perfil. |
| Analise fiscal | NFe | SPED | Hierarquia por estado, cidade, NCM e produto. |
| Clientes | NFe | SPED | Ha endpoint legado `/api/sped/clientes` e analise `/api/sped/analise/clientes`. |
| Reforma Tributaria | Consulta dados persistidos | Consulta dados persistidos | Disponibilidade depende de sincronizacao/dados existentes. |
| Relatorios IA | Compras, vendas, clientes | Compras, vendas, clientes | Exige `OPENAI_API_KEY` e `gerar_relatorio_ia=true`. |
| Inconsistencias | Pendencias XML e historico local | Pendencias SPED e historico local | Historico fica em `localStorage`. |

## Ponto de atencao

Nao misture XML e SPED para a mesma empresa sem uma decisao explicita de arquitetura. O codigo atual foi organizado para escolher um fluxo principal por empresa.
