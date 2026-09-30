# Criptografia de dados sensiveis

Guia de como a Plataforma Fiscal protege em repouso os dados que, se vazarem,
permitem agir em nome do cliente: certificado digital A1, senha do certificado,
tokens OAuth de integracoes e (planejado) segredo TOTP do 2FA.

Complementa `docs/security.md` (escopo multiempresa, sessao, upload) e
`docs/database.md` (schema). Leia antes de criar qualquer coluna, tabela ou
service que guarde credencial de terceiro.

## 1. Principios

1. **Criptografar o que precisa ser lido de volta; fazer hash do que so precisa
   ser comparado.** Certificado e token precisam voltar ao valor original para
   uso, entao sao cifrados (reversivel). Senha de login so e comparada, entao e
   hash (irreversivel).
2. **Uma chave por dominio.** Vazamento ou rotacao de uma chave nao afeta outro
   dominio. Nunca reaproveitar chave entre SEFAZ, Conta Azul e 2FA.
3. **Chave fora do banco.** Chave vive em variavel de ambiente/secret manager;
   ciphertext vive no PostgreSQL. Quem tem so o dump do banco nao le nada.
4. **Descriptografar o mais tarde possivel, no menor escopo possivel.** Plaintext
   so existe em memoria do processo que vai usar, nunca em resposta HTTP, log,
   payload de job Celery ou cache Redis.
5. **Falhar fechado.** Chave ausente = `RuntimeError` na primeira operacao;
   ciphertext invalido = `ValueError` com mensagem generica. Nunca cair para
   texto puro.

## 2. Inventario

| Dado | Onde fica | Protecao | Chave / parametro | Codigo |
| --- | --- | --- | --- | --- |
| Certificado A1 (`.pfx`/`.p12`) | `sefaz.certificados.arquivo_certificado` (`BYTEA`) | Fernet | `SEFAZ_CERT_ENCRYPTION_KEY` | `API/app/services/sefaz/crypto_service.py` |
| Senha do certificado | `sefaz.certificados.senha_criptografada` (`TEXT`) | Fernet | `SEFAZ_CERT_ENCRYPTION_KEY` | idem |
| `access_token` / `refresh_token` Conta Azul | integracoes Conta Azul, colunas `access_token_encrypted` / `refresh_token_encrypted` | Fernet | `CONTAAZUL_TOKEN_ENCRYPTION_KEY` | `API/app/services/conta_azul/crypto_service.py` |
| Segredo TOTP (planejado) | `totp_secret_encrypted` (ver `docs/2fa.md`) | Fernet | `TWO_FACTOR_ENCRYPTION_KEY` | a criar |
| Senha de login | tabela de usuarios | PBKDF2-HMAC-SHA256, salt 16 bytes, 120.000 iteracoes | — | `API/app/services/nfe/auth/login_service.py` |
| Token de sessao (JWT) | cookie HttpOnly | HMAC-SHA256 (assinatura, nao cifra) | `AUTH_SECRET_KEY` | `API/app/core/security.py` |

Metadados nao sensiveis ficam em claro de proposito, para consulta sem
descriptografar: `cnpj_titular`, `data_validade`, `ativo`, `token_expira_em`.

## 3. Algoritmo: Fernet

Todos os dominios usam `cryptography.fernet.Fernet`:

- AES-128-CBC + HMAC-SHA256 (encrypt-then-MAC), IV aleatorio por mensagem.
- Token carrega timestamp de criacao; adulteracao ou chave errada gera
  `InvalidToken`.
- Chave: 32 bytes aleatorios em base64 url-safe (44 caracteres).

Motivo da escolha: API simples, dificil de usar errado, sem decisao de modo/IV/
padding no codigo da aplicacao, suporte nativo a rotacao via `MultiFernet`.

Limitacao conhecida: Fernet nao aceita dado associado (AAD). O ciphertext nao
fica "amarrado" a `empresa_id`. Ver risco R5 na secao 8.

### Formato do modulo `crypto_service.py`

Cada dominio tem o proprio modulo. Contrato do SEFAZ (Conta Azul usa
`encrypt_token`/`decrypt_token`, equivalente a versao texto):

```python
def _fernet() -> Fernet:                   # le a chave do ambiente; RuntimeError se ausente
def encrypt_bytes(value: bytes) -> bytes
def decrypt_bytes(value: bytes) -> bytes   # ValueError generico em InvalidToken
def encrypt_text(value: str) -> str
def decrypt_text(value: str) -> str
```

Regras:

- Chave lida a cada chamada via `os.environ` (sem cache global): facilita teste
  com `monkeypatch.setenv` e troca de chave sem estado preso no import.
- Mensagem de erro nunca inclui chave, ciphertext ou plaintext.
- Repository nunca importa `crypto_service`. Quem cifra/decifra e o service;
  repository so recebe e devolve bytes/strings opacos.

## 4. Certificado digital A1 — ciclo de vida

### 4.1 Upload (`POST /api/sefaz/certificados`)

Rota em `API/app/api/sefaz/routes.py`, logica em
`API/app/services/sefaz/certificado_service.py`.

1. Rota sob `require_company_scope`; `empresa_id` e CNPJ vem da sessao, nunca
   de parametro.
2. Rota valida extensao (`.pfx`/`.p12`), arquivo nao vazio e tamanho maximo
   (10.000 bytes).
3. Service abre o PKCS#12 com a senha (`pkcs12.load_key_and_certificates`).
   Senha errada ou arquivo invalido = `CertificadoInvalidoError` (400).
4. Valida chave privada presente, certificado nao vencido e CN no padrao
   ICP-Brasil `NOME:CNPJ` com CNPJ igual ao da empresa logada.
5. Cifra arquivo e senha separadamente e grava via
   `CertificadosRepository.inserir`, que desativa o certificado anterior e
   insere o novo na mesma transacao (indice unico parcial
   `uq_sefaz_certificados_empresa_ativo` garante no maximo um ativo).
6. Resposta devolve so status: `ativo`, `cnpj_titular`, `data_validade`,
   `dias_restantes`. Nunca o arquivo, nunca a senha.

### 4.2 Uso (worker SEFAZ)

1. `SefazDistribuicaoService` chama
   `CertificadoService.obter_credenciais_descriptografadas(empresa_id)`.
2. Plaintext (`bytes` do pfx + senha) vai direto para `DistribuicaoDFeClient`,
   em memoria, dentro da task Celery.
3. O payload da task Celery carrega identificadores (empresa/job), nunca o
   certificado nem a senha. Redis nunca ve o segredo.
4. `erpbrasil.transmissao` precisa de arquivos PEM para o `requests` fazer TLS
   mutuo: `ArquivoCertificado` grava chave privada e certificado **em claro**
   em `tempfile.mkstemp()` durante a chamada SOAP e apaga no `__exit__`
   (ver risco R2).

### 4.3 Consulta de status (`GET /api/sefaz/certificados/status`)

Le apenas colunas em claro (`cnpj_titular`, `data_validade`). Nao descriptografa
nada.

### 4.4 Substituicao e remocao

- Novo upload desativa o anterior (`ativo = FALSE`), mas a linha antiga
  **continua no banco com o ciphertext** (ver risco R4).
- `ON DELETE CASCADE` em `empresa_id`: excluir a empresa apaga os certificados.

## 5. Gestao de chaves

### 5.1 Gerar

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Uma chave distinta para cada variavel:

| Variavel | Dominio |
| --- | --- |
| `SEFAZ_CERT_ENCRYPTION_KEY` | certificado A1 + senha |
| `CONTAAZUL_TOKEN_ENCRYPTION_KEY` | tokens OAuth Conta Azul |
| `TWO_FACTOR_ENCRYPTION_KEY` | segredo TOTP (quando implementado) |

### 5.2 Onde guardar

- **Local:** `API/app/.env` (fora do git). O `docker-compose.yml` injeta via
  `env_file` em API e workers.
- **Producao:** secret manager do provedor (ou variavel de ambiente protegida do
  orquestrador). Nunca no repositorio, nunca em imagem Docker, nunca no mesmo
  backup do banco.
- Processos que precisam da chave: API (cadastro) e worker da fila
  correspondente (`sefaz`, `conta_azul`). Beat e workers `nfe`/`sped` nao
  precisam — idealmente nao recebem.

### 5.3 Backup e perda

- Backup da chave separado do backup do banco. Dump + chave juntos = segredo
  exposto.
- **Perda da chave = perda irreversivel** dos certificados e tokens cifrados.
  Recuperacao: cada empresa recadastra o certificado e refaz o OAuth Conta Azul.
  Nao existe backdoor.

### 5.4 Rotacao (procedimento proposto, ainda nao implementado)

Fernet suporta rotacao com `MultiFernet`: a primeira chave cifra, todas
decifram, e `rotate()` recifra com a primeira.

Passos:

1. Alterar `_fernet()` para aceitar lista separada por virgula na variavel
   (`NOVA,ANTIGA`) e retornar `MultiFernet([Fernet(k) for k in chaves])`.
2. Deploy com `SEFAZ_CERT_ENCRYPTION_KEY=NOVA,ANTIGA`. Leituras antigas seguem
   funcionando; gravacoes novas usam `NOVA`.
3. Rodar comando de manutencao que le cada linha, aplica `MultiFernet.rotate()`
   em `arquivo_certificado` e `senha_criptografada` e grava de volta (em lote,
   com transacao por lote).
4. Validar: toda linha decifra so com `NOVA`.
5. Deploy com `SEFAZ_CERT_ENCRYPTION_KEY=NOVA`. Destruir `ANTIGA`.

Quando rotacionar: suspeita de vazamento (imediato), saida de pessoa com acesso
ao secret, ou periodicamente (sugestao: anual).

## 6. Regras para codigo novo

Checklist obrigatorio para qualquer PR que guarde credencial de terceiro:

- [ ] Coluna com sufixo que deixa claro que e cifrado (`*_encrypted` ou
      `*_criptografada`); tipo `BYTEA` para binario, `TEXT` para string.
- [ ] Chave nova e exclusiva do dominio, adicionada em `API/app/.env.example`
      (vazia), `docs/security.md` e na tabela da secao 5.1 deste documento.
- [ ] Cifrar/decifrar so no service, via `crypto_service.py` do dominio.
- [ ] Plaintext nunca em: resposta HTTP, `logger.*`, mensagem de excecao,
      payload Celery, Redis, `processing_jobs`, arquivo em disco persistente.
- [ ] Schema Pydantic de resposta nao tem campo do segredo (nem mascarado).
- [ ] Endpoint de escrita sob `require_company_scope`; dono do segredo vem da
      sessao.
- [ ] Testes: roundtrip cifra/decifra, chave ausente gera `RuntimeError`, chave
      errada/ciphertext corrompido gera `ValueError`, e teste de rota garantindo
      que a resposta nao contem o segredo.
- [ ] Fixtures de teste usam certificado autoassinado gerado no teste, nunca
      certificado real de cliente.

## 7. Testes existentes

| Arquivo | Cobre |
| --- | --- |
| `API/app/tests/test_sefaz_crypto.py` | roundtrip bytes/texto, chave ausente, ciphertext corrompido |
| `API/app/tests/test_sefaz_certificado_service.py` | certificado valido, senha incorreta, vencido, CNPJ divergente, roundtrip de credenciais |
| `API/app/tests/test_sefaz_certificados_repository.py` | um ativo por empresa, desativacao do anterior (exige PostgreSQL de teste) |
| `API/app/tests/test_conta_azul_crypto.py` | roundtrip, chave ausente, token corrompido |
| `API/app/tests/test_conta_azul_postgres_token_store.py` | save/load com roundtrip cifrado |

## 8. Riscos conhecidos e backlog

Ordenado por prioridade sugerida.

| # | Risco | Impacto | Mitigacao proposta |
| --- | --- | --- | --- |
| R1 | TLS com a SEFAZ roda com `verify=False` (default de `TransmissaoSOAP.cliente` no `erpbrasil.transmissao`) | MITM na rede do worker poderia ler/alterar respostas da SEFAZ. Chave privada do cliente nao trafega, mas integridade das respostas nao e garantida | Passar CA bundle da cadeia ICP-Brasil/SEFAZ e habilitar verificacao; testar em homologacao |
| R2 | `erpbrasil` grava chave privada **em claro** em `tempfile` durante cada chamada SOAP | Se o worker for morto (`SIGKILL`, OOM) no meio da chamada, o PEM fica no diretorio temporario. Em host compartilhado, outro processo com acesso ao diretorio pode ler | Worker `sefaz` em container dedicado com `TMPDIR` apontando para `tmpfs` (memoria, some ao reiniciar) e permissao so do usuario do processo; limpeza de `tmp*` antigos no startup do worker |
| R3 | `SEFAZ_CERT_ENCRYPTION_KEY` ausente em `API/app/.env.example` | Setup novo sobe sem a chave e so falha no primeiro upload | Adicionar linha vazia no `.env.example` |
| R4 | Certificados substituidos ficam no banco para sempre (`ativo = FALSE`) | Mais ciphertext exposto em caso de vazamento de banco + chave; certificado antigo pode ainda estar valido | Purgar (`DELETE`) inativos apos N dias, ou apagar na substituicao se nao houver necessidade de auditoria |
| R5 | Ciphertext nao amarrado a `empresa_id` (Fernet sem AAD) | Quem tem escrita no banco pode copiar o certificado de uma empresa para a linha de outra | Baixo — exige escrita no banco. Se necessario: cifrar envelope `{empresa_id, payload}` e conferir no decrypt, ou migrar para AES-GCM com `empresa_id` como AAD |
| R6 | Sem rotacao de chave implementada | Vazamento de chave exige recadastro manual de todas as empresas | Implementar secao 5.4 |
| R7 | `crypto_service.py` duplicado por dominio (SEFAZ, Conta Azul, futuro 2FA) | Correcao/rotacao precisa ser replicada em cada copia | Consolidar em `app/core/crypto.py` com `get_cipher(nome_da_variavel)` quando o 2FA for implementado |
| R8 | Login aceita senha armazenada sem `:` comparando texto puro (`_verificar_senha`, fallback legado) | Usuarios antigos podem ter senha em claro no banco | Script: detectar senhas sem salt e forcar redefinicao; depois remover o fallback |
| R9 | PBKDF2 com 120.000 iteracoes | Abaixo da recomendacao OWASP atual (600.000 para PBKDF2-HMAC-SHA256) | Guardar iteracoes no formato (`pbkdf2$600000$salt$hash`) e fazer rehash no proximo login bem-sucedido |
| R10 | Backup do banco sem criptografia garantida (ja listado em `docs/security.md`) | Dump vazado expoe metadados e ciphertext | Backup cifrado; chaves Fernet guardadas em local diferente |

## 9. Resposta a incidente

**Suspeita de vazamento da chave:**

1. Gerar chave nova e executar rotacao (secao 5.4) imediatamente.
2. Se houver vazamento simultaneo do banco: tratar certificados como
   comprometidos. Avisar as empresas para revogar o A1 na AC emissora e
   recadastrar; desconectar integracoes Conta Azul e refazer OAuth.

**Suspeita de vazamento so do banco (chave intacta):** ciphertext sem chave nao
e utilizavel. Ainda assim rotacionar a chave por precaucao e investigar como o
dump saiu.

**Perda da chave:** ver secao 5.3.

## 10. Referencias

- `docs/security.md` — variaveis sensiveis e escopo multiempresa
- `docs/database.md` — schema `sefaz`
- `docs/2fa.md` — plano do segredo TOTP
- `docs/superpowers/specs/2026-08-14-sefaz-distribuicao-dfe-design.md` — design original do armazenamento do certificado
- Fernet: https://cryptography.io/en/latest/fernet/
- OWASP Password Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
