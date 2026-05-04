# Auditoria Operacional

Este documento descreve eventos que deveriam ser auditados para operacao segura da Plataforma Fiscal. Ele diferencia o que ja aparece no codigo do que ainda e recomendacao futura.

## Arquivos de referencia no codigo

- `API/app/core/audit.py`
- `API/app/core/logger.py`
- `API/app/core/security.py`
- `API/app/core/upload_security.py`
- `API/app/api/auth/routes.py`
- `API/app/services/nfe/auth/login_service.py`
- `API/app/services/nfe/xml_importacao_service.py`
- `API/app/services/sped/sped_importacao_service.py`
- `API/app/services/AI/openai_report_service.py`
- `API/app/services/db_schema_service.py`

## Estado atual

Existe `log_security_event` em `API/app/core/audit.py`, usando logger `security.audit`.

Eventos ja registrados explicitamente:

- credencial ausente em rota protegida: `auth_required`;
- acesso negado por CNPJ ou email fora do escopo: `access_denied`;
- upload rejeitado por validacao de seguranca: `upload_rejected`;
- logout: `logout`;
- login bloqueado: `login_blocked`.

Tambem ha logs gerais de request em `API/app/core/logger.py` e logs de startup de schema em `db_schema_service.py`.

Fragilidade: nao foi encontrado trilho de auditoria persistente em banco para eventos fiscais. Se logs de aplicacao forem perdidos, a evidencia operacional tambem pode ser perdida.

## Eventos que devem ser auditados

| Evento | Status atual | Campos minimos recomendados | Observacao |
| --- | --- | --- | --- |
| Login bem-sucedido | Parcial | `login_id`, `empresa_id`, `email`, `cnpj`, `ip`, `user_agent`, horario | Verificar se o service registra sucesso em logs; ideal persistir em auditoria. |
| Login falho | Parcial | `email`, `motivo`, `tentativas_falhas`, `bloqueado_ate`, `ip` | O service controla tentativas e lockout, mas auditoria persistente ainda e recomendacao. |
| Logout | Implementado em log | `login_id` quando disponivel, horario | `POST /api/auth/sair` chama `log_security_event("logout")`. |
| Upload recebido | Pendente | `login_id`, `empresa_id`, `cnpj`, nomes sanitizados, quantidade, bytes totais, tipo | Hoje ha auditoria para rejeicao, nao para sucesso de upload. |
| Rejeicao de arquivo | Implementado em log | `filename`, `content_type`, `size_bytes`, `reason` | Feito em `upload_security.py`. |
| Importacao com erro parcial | Pendente | arquivo, CNPJ extraido, status, mensagem, hash, importacao/lote | Services retornam erros por arquivo, mas nao ha trilho dedicado de auditoria. |
| Processamento iniciado/finalizado | Parcial | CNPJ, periodo, total arquivos, total notas/documentos, status, duracao | NFe registra processamento no banco; SPED precisa de trilho equivalente mais claro. |
| Reprocessamento manual | Pendente | responsavel, motivo, SQL/acao executada, backup associado, ids afetados | Nao ha endpoint de reprocessamento; qualquer acao manual deve ser registrada fora do sistema. |
| Geracao de relatorio IA | Pendente | usuario, CNPJ, rota, categoria, formato, modelo, periodo, sucesso/erro | `openai_report_service.py` loga falhas, mas nao audita solicitacoes bem-sucedidas. |
| Alteracao de schema | Parcial | migration, hash, banco, responsavel, horario, resultado | Startup loga verificacoes, mas nao existe controle formal de migrations aplicadas. |
| Acesso negado por escopo multiempresa | Implementado em log | `login_id`, `empresa_id`, `email`, `cnpj`, parametro solicitado, rota | `require_company_scope` registra `access_denied`. |

## Recomendacoes

- Criar tabela `audit_events` ou integrar com solucao centralizada de logs imutaveis.
- Usar correlation/request id nos logs.
- Persistir eventos fiscais criticos por empresa e usuario.
- Registrar hash de arquivo importado tambem em auditoria.
- Registrar explicitamente geracao de relatorio IA, inclusive modelo e parametros.
- Registrar aplicacao de migration fora do startup, com hash do arquivo SQL.
- Definir retencao minima de logs conforme politica fiscal e LGPD.
