# Plano de Implementacao 2FA

Este documento estrutura a implementacao de autenticacao em dois fatores (2FA) na
Plataforma Fiscal. Ele parte do fluxo atual de autenticacao por email/senha com
JWT HS256 em cookie HttpOnly e header `Authorization: Bearer`.

A implementacao foi dividida em duas etapas:

- **Etapa 1 (V1) - Codigo por email**: codigo de 6 digitos enviado ao email do
  login a cada acesso. Prioriza baixo atrito para o usuario.
- **Etapa 2 (V2) - Aplicativo autenticador (TOTP)**: fator mais forte, opcional
  para quem quiser mais seguranca e candidato a obrigatorio para perfis
  sensiveis.

## Objetivo

Adicionar uma segunda etapa de verificacao ao login para reduzir o risco de
acesso indevido quando a senha do usuario for comprometida.

Fora do escopo das duas etapas:

- SMS.
- WhatsApp.
- WebAuthn/passkeys.
- Gestao administrativa completa de usuarios.

## Estado Atual

Arquivos de referencia:

- `API/app/api/auth/routes.py`
- `API/app/core/security.py`
- `API/app/services/nfe/auth/login_service.py`
- `API/app/models/nfe/auth/schemas.py`
- `Painel/src/contexts/AuthContext.tsx`
- `Painel/src/pages/Login.tsx`
- `Painel/src/services/api.ts`
- `docs/security.md`
- `docs/api-contracts.md`

Fluxo atual:

1. `POST /api/auth/entrar` recebe email e senha.
2. `LoginService.autenticar` valida credenciais, lockout e retorna dados do login.
3. A rota cria um JWT completo com `create_access_token`.
4. A API grava o token em cookie HttpOnly por `set_auth_cookie`.
5. O frontend tambem recebe `access_token` no payload e guarda dados de sessao.
6. `GET /api/auth/sessao` valida cookie/header e hidrata a sessao.

Com 2FA habilitado, o passo 3 nao deve emitir a sessao completa imediatamente.
Antes disso, a API deve criar um desafio temporario para validar o segundo fator.

Pontos relevantes do estado atual:

- O email usado no 2FA e o de `public.login.email` (um por usuario, `UNIQUE`).
  A tabela `empresas` nao tem email proprio.
- A API **ainda nao envia email**. Nao existe SMTP nem provedor configurado.
  Criar essa infraestrutura e pre-requisito da Etapa 1.
- Nao existe fluxo de "esqueci minha senha" por email hoje. Quando existir, ele
  deve respeitar as regras da secao "Relacao com Recuperacao de Senha".

## Decisoes de Produto

| Tema | Etapa 1 (email) | Etapa 2 (TOTP) |
| --- | --- | --- |
| Fator | Codigo de 6 digitos por email | App autenticador (Google/Microsoft Authenticator, etc.) |
| Ativacao | Opcional por usuario, obrigatorio via `TWO_FACTOR_REQUIRED` | Opcional por usuario |
| Recuperacao | Nao precisa (o email e o proprio fator) | Codigos de recuperacao de uso unico |
| Confirmacao para ativar/desativar | Senha atual + codigo enviado por email | Senha atual + codigo TOTP ou de recuperacao |
| Lembrar dispositivo | Sim, opcional, 30 dias | Sim, reaproveitado da Etapa 1 |

Trade-offs aceitos na Etapa 1:

- Email e um fator mais fraco que TOTP: se o atacante tiver a senha do email do
  usuario, ele passa pelos dois fatores. A Etapa 2 existe para mitigar isso.
- A entrega depende de provedor externo. Falha do provedor bloqueia login de quem
  tem 2FA ativo; a API deve responder `503` com mensagem clara.
- Emails compartilhados entre varias pessoas (ex.: caixa do escritorio) reduzem
  o valor do segundo fator. Orientar o cliente a usar email individual.

Estados esperados por usuario:

- 2FA nao configurado.
- 2FA por email pendente de confirmacao.
- 2FA por email ativo.
- (Etapa 2) 2FA por TOTP pendente de confirmacao.
- (Etapa 2) 2FA por TOTP ativo.
- 2FA bloqueado temporariamente por tentativas invalidas.

---

# Etapa 1 - Codigo por Email

## Infraestrutura de Email

Componentes novos:

- `API/app/services/notifications/email_sender.py`: interface `EmailSender`
  com `send(to, subject, html, text)`.
- Implementacoes: `SmtpEmailSender` (generico) e uma implementacao do provedor
  escolhido (ex.: Resend, Amazon SES ou Brevo). Selecionada por `EMAIL_PROVIDER`.
- `FakeEmailSender` para testes, guardando mensagens em memoria.
- `API/app/services/notifications/templates/two_factor_code.(html|txt)`.
- Task Celery `send_two_factor_email` na fila `default`
  (`API/app/workers/notification_tasks.py`).

Regras:

- O envio sai por Celery para nao travar o request. Se a task nao puder ser
  enfileirada, o desafio e invalidado e a API responde `503`.
- O corpo do email contem apenas o codigo, a validade e um aviso de "se nao foi
  voce, troque sua senha". Nunca incluir link que faca login direto.
- Configurar SPF, DKIM e DMARC no dominio remetente antes de ir para producao.
- O payload da task leva o codigo porque precisa envia-lo, entao a task nao deve
  logar seus argumentos (nem em retry/erro).

Variaveis de ambiente:

| Variavel | Descricao |
| --- | --- |
| `EMAIL_PROVIDER` | `smtp`, `resend`, `ses`, `brevo` ou `fake` |
| `EMAIL_FROM` | Remetente, ex.: `Plataforma Fiscal <nao-responda@dominio>` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS` | Somente para `smtp` |
| `EMAIL_API_KEY` | Chave do provedor quando nao for SMTP |

## Modelo de Dados

### `public.login_2fa`

Configuracao de 2FA por usuario. Tabela separada para nao inflar `public.login`.

| Campo | Tipo | Observacao |
| --- | --- | --- |
| `login_id` | BIGINT PK/FK | Referencia `public.login(id)` `ON DELETE CASCADE` |
| `email_enabled` | BOOLEAN | `true` somente apos confirmacao |
| `email_confirmed_at` | TIMESTAMPTZ NULL | Quando o 2FA por email foi ativado |
| `last_used_at` | TIMESTAMPTZ NULL | Ultima verificacao bem-sucedida |
| `failed_attempts` | INTEGER | Falhas recentes somando todos os desafios |
| `locked_until` | TIMESTAMPTZ NULL | Bloqueio temporario do segundo fator |
| `created_at` | TIMESTAMPTZ | Criacao |
| `updated_at` | TIMESTAMPTZ | Atualizacao |

A Etapa 2 adiciona colunas de TOTP nesta mesma tabela.

### `public.login_2fa_challenges`

Desafios temporarios, usados para login e para confirmar acoes sensiveis.

| Campo | Tipo | Observacao |
| --- | --- | --- |
| `id` | UUID PK | `challenge_id` |
| `login_id` | BIGINT FK | Usuario ja validado por senha |
| `purpose` | VARCHAR(20) | `login`, `enable_email`, `disable` |
| `method` | VARCHAR(20) | `email` (Etapa 2 adiciona `totp` e `recovery_code`) |
| `code_hash` | VARCHAR(64) NULL | HMAC-SHA256 do codigo; nulo para `totp` |
| `expires_at` | TIMESTAMPTZ | 5 minutos apos o ultimo envio |
| `used_at` | TIMESTAMPTZ NULL | Marca uso unico |
| `failed_attempts` | INTEGER | Falhas dentro do desafio |
| `send_count` | INTEGER | Quantidade de envios (inclui reenvios) |
| `last_sent_at` | TIMESTAMPTZ NULL | Controle de cooldown de reenvio |
| `created_at` | TIMESTAMPTZ | Criacao |

Indices:

- `(login_id, purpose) WHERE used_at IS NULL` para invalidar desafios abertos.
- `(expires_at)` para limpeza periodica.

### `public.login_2fa_trusted_devices`

Dispositivos lembrados ("nao pedir codigo neste navegador por 30 dias").

| Campo | Tipo | Observacao |
| --- | --- | --- |
| `id` | UUID PK | |
| `login_id` | BIGINT FK | `ON DELETE CASCADE` |
| `token_hash` | VARCHAR(64) UNIQUE | SHA-256 do token do cookie |
| `user_agent` | TEXT NULL | Apenas para exibicao ao usuario |
| `expires_at` | TIMESTAMPTZ | Padrao: 30 dias |
| `revoked_at` | TIMESTAMPTZ NULL | |
| `created_at` | TIMESTAMPTZ | |

### Seguranca dos dados

- O codigo de 6 digitos tem apenas 1 milhao de combinacoes, entao um hash simples
  seria revertido por forca bruta a partir de um dump. Usar
  `HMAC-SHA256(TWO_FACTOR_CODE_PEPPER, challenge_id + codigo)` e comparar com
  `hmac.compare_digest`.
- Gerar o codigo com `secrets.randbelow(10**6)`, formatado com zeros a esquerda.
- Nunca retornar `code_hash` ou `token_hash` pela API.
- Nunca guardar o token de dispositivo em texto puro.

Variaveis de ambiente:

| Variavel | Padrao | Descricao |
| --- | --- | --- |
| `TWO_FACTOR_EMAIL_ENABLED` | `false` | Liga o fluxo de 2FA por email |
| `TWO_FACTOR_REQUIRED` | `false` | Exige 2FA para todos os usuarios |
| `TWO_FACTOR_CODE_PEPPER` | obrigatoria se habilitado | Chave do HMAC dos codigos, separada de `AUTH_SECRET_KEY` |
| `TWO_FACTOR_CODE_TTL_SECONDS` | `300` | Validade do codigo |
| `TWO_FACTOR_MAX_ATTEMPTS` | `5` | Tentativas por desafio |
| `TWO_FACTOR_RESEND_COOLDOWN_SECONDS` | `60` | Intervalo minimo entre reenvios |
| `TWO_FACTOR_MAX_SENDS_PER_HOUR` | `5` | Limite de envios por login por hora |
| `TWO_FACTOR_LOCK_MINUTES` | `15` | Duracao do bloqueio apos excesso de falhas |
| `TWO_FACTOR_TRUSTED_DEVICE_DAYS` | `30` | `0` desliga "lembrar dispositivo" |

## Contratos de API

### Login com 2FA desabilitado

Mantem o contrato atual:

```http
POST /api/auth/entrar
```

Response:

```json
{
  "status": "ok",
  "login_id": 1,
  "empresa_id": 1,
  "cnpj": "12345678000199",
  "email": "user@example.com",
  "empresa_nome": "Empresa Exemplo",
  "tem_sped": false,
  "tem_conta_azul": false,
  "tem_xml": true,
  "tem_xml_importado_valido": false,
  "expires_in": 28800,
  "access_token": "eyJ..."
}
```

O mesmo contrato vale quando o usuario tem 2FA ativo mas envia cookie de
dispositivo confiavel valido.

### Login com 2FA habilitado

Quando email/senha estiverem corretos e o usuario tiver 2FA ativo, a rota cria o
desafio, enfileira o envio do codigo e responde sem criar cookie de sessao final.

```http
POST /api/auth/entrar
```

Response:

```json
{
  "status": "2fa_required",
  "challenge_id": "uuid",
  "expires_in": 300,
  "methods": ["email"],
  "email_mascarado": "us***@example.com",
  "reenvio_disponivel_em": 60
}
```

Observacoes:

- Nao definir cookie de sessao final nesta resposta.
- Nao retornar dados de empresa antes do segundo fator.
- Criar um novo desafio de login invalida desafios de login abertos do mesmo usuario.
- Se o envio nao puder ser enfileirado: `503`.

### Confirmar desafio de login

```http
POST /api/auth/2fa/verificar
```

Request:

```json
{
  "challenge_id": "uuid",
  "codigo": "123456",
  "lembrar_dispositivo": true
}
```

Response de sucesso: mesmo payload do login sem 2FA. Se
`lembrar_dispositivo=true`, a API tambem grava o cookie HttpOnly
`pf_trusted_device` (`Secure`, `SameSite=Lax`, validade de
`TWO_FACTOR_TRUSTED_DEVICE_DAYS`).

Erros esperados:

- `400`: codigo invalido ou desafio expirado.
- `401`: desafio inexistente ou ja usado.
- `429`: excesso de tentativas no desafio ou usuario bloqueado.

### Reenviar codigo

```http
POST /api/auth/2fa/reenviar
```

Request:

```json
{
  "challenge_id": "uuid"
}
```

Response:

```json
{
  "status": "ok",
  "expires_in": 300,
  "reenvio_disponivel_em": 60
}
```

Regras:

- Gera um codigo novo, substitui o `code_hash` e renova `expires_at`.
- Respeita cooldown e limite por hora; excesso retorna `429`.
- Nao zera `failed_attempts` do desafio.

### Consultar status de 2FA

Exige sessao autenticada.

```http
GET /api/auth/2fa/status
```

Response:

```json
{
  "status": "ok",
  "enabled": true,
  "method": "email",
  "confirmed_at": "2026-09-29T12:00:00Z",
  "email_mascarado": "us***@example.com",
  "dispositivos_confiaveis": 2,
  "obrigatorio": false
}
```

### Ativar 2FA por email

Exige sessao autenticada. Em dois passos, para garantir que o email recebe
mensagens antes de depender dele para entrar.

```http
POST /api/auth/2fa/email/ativar
```

Request:

```json
{
  "senha": "SenhaAtual@123"
}
```

Response:

```json
{
  "status": "pending",
  "challenge_id": "uuid",
  "expires_in": 300,
  "email_mascarado": "us***@example.com"
}
```

```http
POST /api/auth/2fa/email/ativar/confirmar
```

Request:

```json
{
  "challenge_id": "uuid",
  "codigo": "123456"
}
```

Response:

```json
{
  "status": "ok",
  "message": "2FA por email ativado com sucesso."
}
```

### Desativar 2FA

Exige sessao autenticada. Tambem em dois passos: senha dispara o codigo, codigo
confirma. Nao permitido quando `TWO_FACTOR_REQUIRED=true` (`400`).

```http
POST /api/auth/2fa/desativar
```

Request:

```json
{
  "senha": "SenhaAtual@123"
}
```

Response: igual a `POST /api/auth/2fa/email/ativar`.

```http
POST /api/auth/2fa/desativar/confirmar
```

Request:

```json
{
  "challenge_id": "uuid",
  "codigo": "123456"
}
```

Response:

```json
{
  "status": "ok",
  "message": "2FA desativado com sucesso."
}
```

Desativar revoga todos os dispositivos confiaveis do usuario.

### Revogar dispositivos confiaveis

Exige sessao autenticada.

```http
DELETE /api/auth/2fa/dispositivos
```

Response:

```json
{
  "status": "ok",
  "revogados": 2
}
```

## Arquitetura Backend

Novos componentes:

- `API/app/api/auth/two_factor_routes.py`
- `API/app/services/auth/two_factor_service.py`
- `API/app/domain/auth/two_factor_codes.py` (geracao e HMAC do codigo, puro)
- `API/app/repositories/auth/two_factor_repository.py`
- `API/app/models/auth/two_factor_schemas.py`
- `API/app/services/notifications/email_sender.py`
- `API/app/workers/notification_tasks.py`

Responsabilidades:

- Rota: validar request, chamar service, converter erros para HTTP, gravar cookies.
- Service: orquestrar desafio, envio, verificacao, ativacao, desativacao e dispositivos.
- Repository: unico lugar com SQL das tabelas de 2FA.
- Domain: gerar codigo, calcular e comparar HMAC, mascarar email. Sem I/O.
- Email sender: abstrair o provedor; nenhuma regra de 2FA aqui.

## Fluxo Backend de Login

1. `LoginService.autenticar` continua validando email/senha e lockout de senha.
2. A rota consulta `TwoFactorService.status(login_id)`.
3. Se 2FA nao estiver ativo (e nao for obrigatorio), emite JWT como hoje.
4. Se houver cookie `pf_trusted_device` valido para o `login_id`, emite JWT como hoje.
5. Se 2FA estiver ativo:
   - verifica `locked_until` (`429` se bloqueado);
   - invalida desafios de login abertos;
   - cria desafio, gera codigo, grava HMAC;
   - enfileira envio do email;
   - retorna `status="2fa_required"` sem cookie final.
6. `POST /api/auth/2fa/verificar` valida desafio, expiracao, uso e codigo.
7. Em sucesso: marca `used_at`, zera falhas, atualiza `last_used_at`, emite JWT e
   grava cookie final (e cookie de dispositivo, se pedido).
8. Em falha: incrementa falhas no desafio e no usuario; ao atingir o limite,
   invalida o desafio e aplica `locked_until`.

Limpeza: task Celery beat diaria remove desafios expirados ha mais de 24h e
dispositivos expirados ou revogados ha mais de 30 dias.

## Politica de Obrigatoriedade

Com `TWO_FACTOR_REQUIRED=true`:

- Usuario sem 2FA ativo recebe desafio por email no login mesmo assim. O
  primeiro login bem-sucedido ativa o 2FA por email automaticamente, pois o
  recebimento do codigo ja confirma o email.
- Desativacao fica bloqueada.

## Relacao com Recuperacao de Senha

Quando o fluxo de "esqueci minha senha" for criado:

- Reset de senha revoga todos os dispositivos confiaveis.
- Reset de senha nao desativa o 2FA.
- Na Etapa 1, email ja e o fator, entao quem controla o email consegue resetar a
  senha e passar pelo 2FA. Esse e o limite conhecido do fator email e a razao
  da Etapa 2.
- Na Etapa 2, usuario com TOTP ativo continua precisando do TOTP ou de um codigo
  de recuperacao apos resetar a senha.

## Frontend

Telas/estados:

- Login normal.
- Etapa de codigo quando `status="2fa_required"`: input de 6 digitos,
  email mascarado, contador de reenvio, checkbox "lembrar este dispositivo".
- Configuracoes: card de 2FA com status, botao ativar/desativar e botao
  "esquecer dispositivos".
- Dialogos de ativacao e desativacao (senha -> codigo).

Pontos de codigo:

- `Painel/src/contexts/AuthContext.tsx`
- `Painel/src/pages/Login.tsx`
- `Painel/src/features/configuracoes`
- `Painel/src/services/configuracoes.ts`

Fluxo no `AuthContext`:

1. `login(email, password)` passa a aceitar dois resultados:
   - sessao completa;
   - `twoFactorRequired` com `challengeId`, `emailMascarado`, `reenvioDisponivelEm`.
2. A pagina de login exibe o input de codigo.
3. `verifyTwoFactor(challengeId, code, rememberDevice)` conclui a sessao.
4. `resendTwoFactorCode(challengeId)` reenvia.
5. Persistencia local so ocorre apos sessao final.

## Auditoria

Eventos para `log_security_event`:

- `2fa_email_enable_started`
- `2fa_enabled`
- `2fa_disabled`
- `2fa_challenge_created`
- `2fa_code_sent`
- `2fa_code_resent`
- `2fa_email_send_failed`
- `2fa_challenge_succeeded`
- `2fa_challenge_failed`
- `2fa_locked`
- `2fa_trusted_device_created`
- `2fa_trusted_device_used`
- `2fa_trusted_devices_revoked`

Dados permitidos em log:

- `login_id`
- `empresa_id`
- `challenge_id`
- `purpose`, `method`
- `email` sanitizado pelo logger
- `cnpj` sanitizado pelo logger
- `outcome`
- `reason`

Nunca logar:

- Codigo enviado por email.
- `code_hash`, token ou `token_hash` de dispositivo.
- Corpo do email.
- (Etapa 2) Codigo TOTP, codigo de recuperacao, secret TOTP, `otpauth_url`.

## Regras de Seguranca

- Codigo: 6 digitos via `secrets`, validade de 5 minutos, uso unico.
- Armazenamento: somente HMAC com pepper proprio.
- Tentativas: 5 por desafio; excesso invalida o desafio.
- Lockout: falhas acumuladas por usuario bloqueiam o segundo fator por 15 minutos.
- Reenvio: cooldown de 60s e maximo de 5 envios por hora por login.
- Sessao: nao emitir cookie final antes do segundo fator.
- Nao emitir JWT intermediario reutilizavel; o `challenge_id` sozinho nao da acesso.
- Acoes sensiveis (ativar/desativar) exigem senha atual e codigo recem-enviado.
- UX: mensagens de erro nao confirmam se email existe ou se 2FA esta ativo antes
  da senha ser validada.
- Email mascarado na UI: primeiros 2 caracteres do usuario + dominio completo.

## Plano de Implementacao - Etapa 1

### Fase 1.1 - Infraestrutura de email

- Escolher provedor e configurar dominio (SPF/DKIM/DMARC).
- Criar `EmailSender`, implementacoes e `FakeEmailSender`.
- Criar task `send_two_factor_email` e template.
- Adicionar variaveis ao `.env.example` e ao `docker-compose.yml`.

### Fase 1.2 - Base backend de 2FA

- Migrations `login_2fa`, `login_2fa_challenges`, `login_2fa_trusted_devices`.
- Helper puro de codigo/HMAC.
- Repository, service e schemas.

### Fase 1.3 - Login em duas etapas

- Ajustar `POST /api/auth/entrar` para retornar `2fa_required`.
- Criar `verificar` e `reenviar`.
- Dispositivo confiavel.
- Auditoria, lockout e rate limit.

### Fase 1.4 - Configuracoes do usuario

- Endpoints de status, ativar, desativar e revogar dispositivos.
- UI em configuracoes e etapa de codigo no login.

### Fase 1.5 - Obrigatoriedade

- `TWO_FACTOR_REQUIRED` e ativacao automatica no primeiro login.
- Atualizar documentacao operacional.

## Testes - Etapa 1

Backend:

- Login sem 2FA preserva contrato atual.
- Login com 2FA ativo retorna `2fa_required`, nao define cookie final e enfileira email.
- Falha ao enfileirar retorna `503` e invalida o desafio.
- Codigo correto conclui login e define cookie.
- Codigo invalido retorna `400` e incrementa falha.
- Quinta falha invalida desafio e bloqueia usuario (`429`).
- Desafio expirado nao autentica.
- Desafio usado nao autentica novamente.
- Novo login invalida desafio anterior.
- Reenvio respeita cooldown e limite por hora.
- Reenvio invalida o codigo anterior.
- Dispositivo confiavel valido pula o desafio; expirado ou revogado nao pula.
- Ativacao exige senha e so ativa com codigo valido.
- Desativacao exige senha e codigo; bloqueada com `TWO_FACTOR_REQUIRED=true`.
- Codigo, hashes e tokens nao aparecem em logs nem responses.

Frontend:

- Login comum continua funcionando.
- `2fa_required` mostra etapa de codigo com email mascarado.
- Codigo correto conclui autenticacao e navega para o app.
- Codigo invalido mostra erro sem perder o desafio.
- Botao de reenvio respeita o contador.
- Ativacao e desativacao pedem senha e depois codigo.
- Status aparece em configuracoes.

---

# Etapa 2 - Aplicativo Autenticador (TOTP)

Adiciona TOTP como fator mais forte. Reaproveita desafios, lockout, dispositivos
confiaveis, auditoria e UI da Etapa 1.

## Modelo de Dados

Novas colunas em `public.login_2fa`:

| Campo | Tipo | Observacao |
| --- | --- | --- |
| `totp_secret_encrypted` | TEXT NULL | Secret criptografado com Fernet |
| `totp_enabled` | BOOLEAN | `true` somente apos confirmacao |
| `totp_confirmed_at` | TIMESTAMPTZ NULL | |
| `totp_last_step` | BIGINT NULL | Ultimo time-step aceito, impede replay do mesmo codigo |
| `recovery_codes_hash` | JSONB | Hashes dos codigos de recuperacao validos |

Variaveis de ambiente:

- `TWO_FACTOR_ENCRYPTION_KEY`: chave Fernet do secret TOTP, separada de
  `AUTH_SECRET_KEY` e de `TWO_FACTOR_CODE_PEPPER`.
- `TWO_FACTOR_ISSUER`: nome exibido no app autenticador, padrao `Plataforma Fiscal`.

Bibliotecas:

- `pyotp` para TOTP.
- `cryptography.fernet` (ja esta em `requirements.txt`).
- Frontend gera o QR Code a partir do `otpauth_url` (ex.: `qrcode.react`).

## Regras

- Usuario com TOTP ativo recebe `methods: ["totp", "recovery_code"]` no login.
  O email deixa de ser oferecido para ele, senao o fator mais fraco anula o forte.
- Janela TOTP: no maximo um passo anterior/posterior.
- Mesmo codigo TOTP nao pode ser aceito duas vezes (`totp_last_step`).
- Codigos de recuperacao: 10 codigos longos e aleatorios, uso unico, armazenados
  com hash, exibidos uma unica vez.
- Setup e troca de secret exigem senha atual.
- Desativar TOTP exige senha atual + TOTP ou codigo de recuperacao; o usuario
  volta para 2FA por email.

## Contratos de API

### Iniciar setup de TOTP

```http
POST /api/auth/2fa/totp/setup
```

Request:

```json
{
  "senha": "SenhaAtual@123"
}
```

Response:

```json
{
  "status": "pending",
  "otpauth_url": "otpauth://totp/...",
  "secret_preview": "ABCD EFGH IJKL MNOP"
}
```

O secret fica salvo com `totp_enabled=false` ate a confirmacao.

### Confirmar setup de TOTP

```http
POST /api/auth/2fa/totp/setup/confirmar
```

Request:

```json
{
  "codigo": "123456"
}
```

Response:

```json
{
  "status": "ok",
  "recovery_codes": ["ABCD-1234-EFGH", "IJKL-5678-MNOP"]
}
```

### Verificar login

Mesmo endpoint da Etapa 1 (`POST /api/auth/2fa/verificar`), com campo `metodo`
opcional (`totp` ou `recovery_code`).

### Regenerar codigos de recuperacao

```http
POST /api/auth/2fa/totp/recovery-codes
```

Request:

```json
{
  "senha": "SenhaAtual@123",
  "codigo": "123456"
}
```

Response: nova lista de `recovery_codes`; os anteriores sao invalidados.

### Desativar TOTP

```http
DELETE /api/auth/2fa/totp
```

Request:

```json
{
  "senha": "SenhaAtual@123",
  "codigo": "123456"
}
```

### Status

`GET /api/auth/2fa/status` passa a retornar `method: "totp"` e
`recovery_codes_remaining`.

## Auditoria Adicional

- `2fa_totp_setup_started`
- `2fa_totp_enabled`
- `2fa_totp_disabled`
- `2fa_recovery_code_used`
- `2fa_recovery_codes_rotated`

## Plano de Implementacao - Etapa 2

- Migration com colunas de TOTP.
- Crypto helper Fernet (`API/app/core/two_factor_crypto.py`).
- Service de TOTP e codigos de recuperacao.
- Ajustar `verificar` e status para multiplos metodos.
- UI de setup com QR Code, exibicao unica dos codigos, regeneracao e desativacao.
- Avaliar exigir TOTP para usuarios internos/admins.

## Testes - Etapa 2

- Setup exige senha e so ativa com codigo valido.
- Login com TOTP ativo nao oferece email.
- Codigo TOTP fora da janela e rejeitado.
- Mesmo codigo TOTP nao e aceito duas vezes.
- Codigo de recuperacao funciona uma vez e depois fica invalido.
- Regenerar invalida codigos anteriores.
- Desativar TOTP volta para 2FA por email.
- Secret, `otpauth_url` e codigos nao aparecem em logs.

---

## Atualizacoes de Documentacao

Ao implementar cada etapa, atualizar:

- `docs/security.md`: 2FA, pepper/chaves, dispositivos confiaveis, auditoria.
- `docs/api-contracts.md`: endpoints novos e alteracao de login.
- `docs/jobs.md`: tasks de envio de email e limpeza.
- `.env.example`: variaveis de email e 2FA.
- `README.md` ou `docs/setup.md`: configuracao do provedor de email local
  (`EMAIL_PROVIDER=fake` para desenvolvimento).

## Perguntas Abertas

- Qual provedor de email (Resend, Amazon SES, Brevo ou SMTP proprio)?
- A Etapa 1 entra opcional ou ja com `TWO_FACTOR_REQUIRED=true` em producao?
- Admins ou usuarios internos terao politica diferente (ex.: TOTP obrigatorio)?
- A sessao atual deve ser encerrada quando o usuario ativa/desativa 2FA?
- Havera recuperacao assistida por suporte para quem perder acesso ao email?

## Checklist de Pronto

Etapa 1:

- [ ] Provedor de email configurado com SPF/DKIM/DMARC.
- [ ] Migrations criadas e testadas.
- [ ] Codigos armazenados apenas como HMAC.
- [ ] Login em duas etapas sem cookie final antes da verificacao.
- [ ] Reenvio com cooldown e limite por hora.
- [ ] Lockout do segundo fator.
- [ ] Dispositivos confiaveis com revogacao.
- [ ] Auditoria sem dados sensiveis.
- [ ] Testes backend e frontend cobrindo fluxo feliz e erros.
- [ ] Documentacao de seguranca e contratos atualizada.

Etapa 2:

- [ ] Secret TOTP criptografado em repouso.
- [ ] Protecao contra replay de codigo TOTP.
- [ ] Recovery codes apenas como hash e exibidos uma vez.
- [ ] Email desabilitado como fator para usuarios com TOTP.
- [ ] Testes backend e frontend cobrindo TOTP e recovery codes.
