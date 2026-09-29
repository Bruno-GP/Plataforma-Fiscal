# Mapeamento: busca de XML na SEFAZ com certificado digital

Este documento mapeia a evolucao do fluxo atual de importacao manual de XML para uma busca direta na SEFAZ usando certificado digital.

## Base tecnica SEFAZ

O caminho correto para baixar documentos de interesse da empresa e o Web Service `NFeDistribuicaoDFe`, metodo `nfeDistDFeInteresse`, do Ambiente Nacional da NF-e. A consulta e feita com certificado digital e trabalha com NSU, retornando lotes de documentos compactados.

Referencias oficiais consultadas:

- Portal NF-e, Nota Tecnica 2014.002: `https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=0rPhVp1wRqc%3D`
- Portal NF-e, aviso sobre NT 2014.002 v1.20: `https://www.nfe.fazenda.gov.br/portal/informe.aspx?Informe=7oVQ6T+1Tyg%3D&ehCTG=false`
- Portal NF-e, regras de uso indevido publicadas em 04/03/2022: `https://www.nfe.fazenda.gov.br/portal/informe.aspx?ehCTG=false&page=14&pagesize=15`

## Situacao atual do projeto

O projeto ja tem uma esteira boa para receber XML:

- `POST /api/nfe/xml/importar` recebe arquivos via upload.
- `XMLImportacaoService` grava os XMLs em `notas_xml_importados`.
- `POST /api/nfe/xml/processar-importados` cria job Celery.
- `processar_nfe_importados_task` busca XMLs pendentes no staging e chama `ProcessarNFeService`.
- O Painel acompanha importacao, processamento e progresso do job em `ImportacaoXML.tsx`.

Ou seja: a integracao SEFAZ nao precisa reinventar o processamento fiscal. Ela deve apenas substituir a origem "upload do usuario" por "download SEFAZ", gravando no mesmo staging.

## Fluxo alvo

1. Empresa cadastra certificado digital A1 `.pfx`/`.p12` e senha.
2. Backend valida se o CNPJ base do certificado corresponde ao CNPJ da empresa autenticada.
3. Usuario clica em "Buscar XML na SEFAZ".
4. API cria um job de sincronizacao SEFAZ.
5. Worker consulta `NFeDistribuicaoDFe` usando `distNSU` a partir do ultimo NSU salvo para o CNPJ.
6. Para cada `docZip` retornado:
   - descompacta GZip/Base64;
   - identifica se e XML completo, resumo ou evento;
   - grava XML completo em `notas_xml_importados`;
   - registra resumo/evento em tabela propria para auditoria e manifestacao futura.
7. Quando nao houver mais documentos (`cStat=137`), grava o horario e respeita janela de espera antes de nova consulta.
8. Ao final, opcionalmente dispara o processamento dos XMLs importados usando o job existente `NFE_PROCESSAMENTO_IMPORTADOS`.

## Componentes backend sugeridos

Novos arquivos:

- `API/app/services/nfe/sefaz/certificado_service.py`
- `API/app/services/nfe/sefaz/distribuicao_dfe_client.py`
- `API/app/services/nfe/sefaz/sefaz_sync_service.py`
- `API/app/workers/sefaz_tasks.py`
- `API/app/api/sefaz/routes.py` ou subrotas em `API/app/api/nfe/routes.py`

Responsabilidades:

- `certificado_service.py`: carregar A1, validar senha, extrair CNPJ/validade e preparar certificado para TLS mutual.
- `distribuicao_dfe_client.py`: montar SOAP `distDFeInt`, enviar para ambiente nacional, tratar XML de retorno.
- `sefaz_sync_service.py`: controlar NSU, interpretar `cStat`, gravar documentos e integrar com `XMLImportacaoService`.
- `sefaz_tasks.py`: executar sincronizacao em background e atualizar `processing_jobs`.

## Endpoints propostos

### Certificado

`POST /api/nfe/certificado`

- multipart com arquivo `.pfx`/`.p12`;
- campo `senha`;
- valida CNPJ base, validade e senha;
- nunca retorna senha nem conteudo do certificado.

`GET /api/nfe/certificado/status`

Retorno sugerido:

```json
{
  "status": "ok",
  "cnpj": "12345678000199",
  "cnpj_base": "12345678",
  "valido_ate": "2027-05-01T12:00:00",
  "dias_para_vencer": 358
}
```

### Busca SEFAZ

`POST /api/nfe/sefaz/sincronizar`

Body sugerido:

```json
{
  "cnpj_emitente": "12345678000199",
  "ambiente": "producao",
  "processar_apos_importar": true
}
```

Retorno:

```json
{
  "job_id": "00000000-0000-0000-0000-000000000000",
  "status": "QUEUED",
  "message": "Sincronizacao SEFAZ enviada para fila"
}
```

`GET /api/nfe/sefaz/status?cnpj_emitente=12345678000199`

Retorno sugerido:

```json
{
  "status": "ok",
  "cnpj_emitente": "12345678000199",
  "ultimo_nsu": "000000000000123",
  "max_nsu": "000000000000130",
  "ultima_sincronizacao": "2026-05-08T16:30:00",
  "bloqueado_ate": null,
  "ultimo_cstat": "137",
  "ultimo_motivo": "Nenhum documento localizado"
}
```

## Banco de dados

Tabela para certificado:

```sql
CREATE TABLE certificados_digitais (
  id BIGSERIAL PRIMARY KEY,
  empresa_cnpj VARCHAR(14) NOT NULL UNIQUE,
  cnpj_base VARCHAR(8) NOT NULL,
  certificado_encriptado BYTEA NOT NULL,
  senha_encriptada BYTEA NOT NULL,
  valido_ate TIMESTAMPTZ,
  criado_em TIMESTAMPTZ DEFAULT NOW(),
  atualizado_em TIMESTAMPTZ DEFAULT NOW()
);
```

Tabela para controle NSU:

```sql
CREATE TABLE sefaz_distribuicao_controle (
  id BIGSERIAL PRIMARY KEY,
  cnpj_emitente VARCHAR(14) NOT NULL UNIQUE,
  ambiente VARCHAR(20) NOT NULL DEFAULT 'producao',
  ultimo_nsu VARCHAR(15) NOT NULL DEFAULT '000000000000000',
  max_nsu VARCHAR(15),
  ultimo_cstat VARCHAR(10),
  ultimo_motivo TEXT,
  bloqueado_ate TIMESTAMPTZ,
  ultima_sincronizacao TIMESTAMPTZ,
  atualizado_em TIMESTAMPTZ DEFAULT NOW()
);
```

Tabela para documentos retornados pela SEFAZ:

```sql
CREATE TABLE sefaz_distribuicao_documentos (
  id BIGSERIAL PRIMARY KEY,
  cnpj_emitente VARCHAR(14) NOT NULL,
  nsu VARCHAR(15) NOT NULL,
  schema_xml VARCHAR(80),
  chave_acesso VARCHAR(44),
  tipo_documento VARCHAR(40),
  hash_conteudo VARCHAR(64) NOT NULL,
  conteudo_xml BYTEA NOT NULL,
  importado_staging_em TIMESTAMPTZ,
  criado_em TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (cnpj_emitente, nsu),
  UNIQUE (cnpj_emitente, hash_conteudo)
);
```

Observacao: XML completo deve continuar sendo inserido em `notas_xml_importados` para reaproveitar o processamento atual.

## Regras fiscais e operacionais importantes

- A consulta deve ser por CNPJ/CPF interessado e certificado valido.
- Para PJ, a validacao operacional deve exigir o mesmo CNPJ base entre certificado e empresa.
- `distNSU` e o modo ideal para sincronizacao continua.
- Ao receber `cStat=137`, nao consultar novamente antes de 1 hora.
- Ao receber `cStat=656`, registrar bloqueio e pausar novas consultas ate cumprir a janela de espera.
- Resumos de NF-e podem exigir Manifestacao do Destinatario para liberar XML completo em alguns cenarios.
- `NFeDistribuicaoDFe` cobre NF-e e eventos de interesse; NFSe municipal nao entra nesse fluxo.

## Dependencias Python provaveis

Hoje `API/app/requirements.txt` nao possui bibliotecas para certificado A1/TLS mutual/SOAP. Opcoes:

- `cryptography`: leitura/validacao de certificado A1.
- `requests` ou `httpx` com certificado temporario PEM para TLS mutual.
- `lxml`: montagem e parsing XML/SOAP mais robustos.

Tambem e possivel usar biblioteca fiscal pronta, mas eu recomendaria encapsular em `distribuicao_dfe_client.py` para nao acoplar o dominio inteiro do projeto a uma dependencia externa.

## Ajustes no Painel

Na tela `Painel/src/pages/ImportacaoXML.tsx`, adicionar uma segunda acao ao lado do upload:

- botao "Buscar na SEFAZ";
- status do certificado;
- ultima sincronizacao;
- ultimo NSU;
- progresso do job;
- alerta quando a SEFAZ pedir espera de 1 hora.

Nao e necessario criar uma tela separada no primeiro ciclo. O usuario ja entende essa pagina como o ponto de entrada dos XMLs.

## Sequencia recomendada de implementacao

1. Criar migrations das tabelas `certificados_digitais`, `sefaz_distribuicao_controle` e `sefaz_distribuicao_documentos`.
2. Implementar cadastro/status de certificado A1 com criptografia em repouso.
3. Implementar client `NFeDistribuicaoDFe` em homologacao.
4. Criar job `SEFAZ_DFE_SYNC` com controle de NSU e regras `137`/`656`.
5. Gravar XML completo no staging atual `notas_xml_importados`.
6. Disparar processamento atual quando `processar_apos_importar=true`.
7. Adicionar UI no Painel.
8. Cobrir com testes unitarios de parsing, NSU, cStat e duplicidade.

## Riscos

- Certificado digital e senha sao altamente sensiveis; precisam de criptografia, auditoria e controle de acesso.
- Regras de uso indevido da SEFAZ podem bloquear o CNPJ temporariamente.
- A busca por NSU nao deve ser chamada em loop agressivo.
- Sem Manifestacao do Destinatario, alguns documentos podem aparecer apenas como resumo.
- NFSe continua dependendo de integracoes municipais separadas.
- **Correcao 2026-08-18 (retifica entrada anterior deste mesmo dia):** a hipotese de que
  `distDFeInt` "nao traz notas emitidas por design" estava **errada** e foi descartada.
  A causa raiz real eram dois bugs de configuracao no client (`distribuicao_dfe_client.py`):
  (1) `NFeTransmissor` era criado sem `versao`, herdando o default `"4.00"` (versao de
  autorizacao de NFe) para o envelope `distDFeInt`, que so aceita `"1.01"` -> SEFAZ rejeitava
  com `cStat=239` ("Versao do arquivo XML nao suportada"); (2) `cUFAutor` estava hardcoded
  em `"91"` (codigo generico de Ambiente Nacional usado em outros webservices de NFe), mas o
  schema `distDFeInt` exige o codigo IBGE real da UF do autor da consulta -> SEFAZ rejeitava
  com `cStat=215` ("Falha no esquema xml"). O client tambem descartava o `xMotivo` da
  resposta e tratava qualquer `cStat` desconhecido como sucesso silencioso — por isso o erro
  ficou mascarado em varias execucoes seguidas com `documentos_novos=0` e status "sucesso".
  Corrigido: `versao="1.01"` fixo no client; `cUFAutor` resolvido a partir de `empresas.estado`
  (`app/domain/sefaz/uf_codigos.py`); `xMotivo` agora persistido e `cStat` fora de
  `{137, 138, 656}` marca a sincronizacao como erro real. Validado ao vivo: apos o fix, a
  consulta retornou `cStat=138` com lote real de documentos.

