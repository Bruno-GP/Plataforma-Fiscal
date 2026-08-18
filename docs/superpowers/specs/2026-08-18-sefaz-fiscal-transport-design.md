# SEFAZ documentos emitida -> banco Fiscal

## Contexto

Hoje existem dois mundos sem ponte. Upload manual de XML: `notas_xml_importados`
(staging) -> `XMLImportacaoService` (validacao especifica de upload, exige
`cnpj_emitente == cnpj_empresa_origem`) -> `ProcessarNFeService.executar_xmls_importados`
-> tabelas Fiscal (`notas`, `notas_itens`, `produtos`, KPIs, Reforma Tributaria).
Sync SEFAZ: `sefaz.documentos` guarda os documentos distribuidos pela SEFAZ, com
XML completo (`xml_armazenado`) somente quando o schema retornado e `nfeProc` --
`resNFe` e so resumo, sem itens.

`ProcessarNFeService.executar_xmls_importados(cnpj_emitente, xmls_importados)` ja
e agnostico de origem: recebe uma lista de tuplas `(id, nome, bytes)` e nao depende
da tabela de staging nem da validacao de upload. Isso permite alimentar o mesmo
nucleo de parsing/consolidacao fiscal a partir de `sefaz.documentos`, sem reusar
`XMLImportacaoService` e sem acoplar o caminho SEFAZ ao caminho de upload manual --
os dois ficam paralelos, convergindo so no nucleo de dominio. Isso importa porque
o upload manual pode ser descontinuado no futuro sem afetar este fluxo.

Ja existe um hook preparado exatamente pra isso: `sefaz_evento_documento_novo_task`
(`app/workers/sefaz_tasks.py`), disparado por `SefazDistribuicaoService._publicar_evento_documento_novo`
para cada documento novo inserido durante o sync (qualquer direcao), hoje um stub
que so loga.

`notas`/`notas_itens` fazem UPSERT por `(numero_nf, emitente_cnpj, modelo,
data_emissao)` (`app/repositories/nfe/nfe_repository.py`), entao reprocessar o
mesmo documento (por SEFAZ e por upload manual, ou por retry) e seguro e nao
duplica.

## Objetivo

Transportar automaticamente os itens dos documentos SEFAZ com `direcao='emitida'`
para as tabelas Fiscal existentes (`notas`, `notas_itens`, `produtos`, KPIs,
Reforma Tributaria), reaproveitando o `ProcessarNFeService` ja usado pelo upload
manual, sem exigir acao do usuario.

## Fora de escopo

- Documentos `direcao='recebida'` (compras de fornecedores) -- o pipeline Fiscal
  atual assume emitente = a propria empresa; tratar compras exige modelagem
  propria, fica pra uma iteracao futura.
- Descontinuar a rota de upload manual de XML -- decisao futura, fora deste
  design.
- Mudar `SefazDistribuicaoService`/`sefaz_sync_empresa_task` alem do necessario
  para disparar o backfill (ver secao 5).
- Endpoint novo para reprocessamento manual -- o backfill automatico (secao 5)
  cobre o caso de uso.

## Design

### 1. Migration (Alembic)

Nova coluna em `sefaz.documentos`:

```sql
ALTER TABLE sefaz.documentos
  ADD COLUMN processado_fiscal_em TIMESTAMPTZ NULL;
```

`NULL` = pendente (nunca processado, falhou na ultima tentativa, ou e `resNFe`
sem XML completo). Nao ha coluna de status separada -- a proxima tentativa
(hook ou backfill) resolve sozinha; nao ha necessidade de distinguir os motivos
de "pendente" para o funcionamento do fluxo.

Arquivo: `API/app/alembic/versions/20260818_0014_sefaz_documentos_processado_fiscal.py`.
Atualizar `docs/database.md` (secao "Modulo SEFAZ") com a nova coluna.

### 2. Repository -- `DocumentosRepository`

Dois metodos novos em `app/repositories/sefaz/documentos_repository.py`:

```python
def marcar_processado_fiscal(self, documento_id: int) -> None:
    """UPDATE sefaz.documentos SET processado_fiscal_em = NOW() WHERE id = %s"""

def listar_pendentes_fiscal(self, empresa_id: int) -> list[dict[str, Any]]:
    """
    SELECT * FROM sefaz.documentos
    WHERE empresa_id = %s
      AND direcao = 'emitida'
      AND xml_armazenado IS NOT NULL
      AND processado_fiscal_em IS NULL
    """
```

`obter_por_chave` (ja existente) cobre o caso do hook por documento unico.

### 3. Novo service -- `SefazFiscalTransportService`

Arquivo: `app/services/sefaz/sefaz_fiscal_transport_service.py`. Orquestra o
transporte de um lote de documentos SEFAZ para o Fiscal:

```python
class SefazFiscalTransportService:
    def transportar_documentos(
        self,
        *,
        empresa_id: int,
        cnpj_empresa: str,
        documentos: list[dict],  # linhas de sefaz.documentos
    ) -> None:
        elegiveis = [
            documento for documento in documentos
            if documento["direcao"] == "emitida"
            and documento.get("xml_armazenado")
            and not documento.get("processado_fiscal_em")
        ]
        if not elegiveis:
            return

        tuplas = [
            (documento["id"], documento["chave_acesso"], bytes(documento["xml_armazenado"]))
            for documento in elegiveis
        ]

        resposta, ids_processados = ProcessarNFeService().executar_xmls_importados(
            cnpj_emitente=cnpj_empresa,
            xmls_importados=tuplas,
        )

        if resposta.status != "processado":
            logger.warning("sefaz_fiscal_transport_falhou", extra={...})
            return  # nao propaga excecao -- best-effort

        repository = DocumentosRepository()
        for documento in elegiveis:
            if documento["id"] in ids_processados:
                repository.marcar_processado_fiscal(documento["id"])
```

Documentos que nao entram em `elegiveis` (direcao != emitida, sem
`xml_armazenado`, ja processados) sao ignorados silenciosamente (log em nivel
`info`, sem erro).

Falha do `ProcessarNFeService` (parse invalido, CNPJ inconsistente, etc): loga
em `warning` e nao marca `processado_fiscal_em` -- o documento continua
elegivel para a proxima tentativa (proximo backfill ou proximo evento). Nao
propaga excecao para nao derrubar o sync nem o worker.

### 4. Gatilho automatico -- documento novo

`sefaz_evento_documento_novo_task` (`app/workers/sefaz_tasks.py`) passa a
chamar o service em vez de so logar:

```python
@celery_app.task(name="sefaz_evento_documento_novo_task", ...)
def sefaz_evento_documento_novo_task(empresa_id: int, chave_acesso: str) -> dict:
    documento = DocumentosRepository().obter_por_chave(empresa_id, chave_acesso)
    if documento is None:
        return {"status": "SUCCESS", "motivo": "documento_nao_encontrado"}

    SefazFiscalTransportService().transportar_documentos(
        empresa_id=empresa_id,
        cnpj_empresa=documento["cnpj_emitente"],
        documentos=[documento],
    )
    return {"status": "SUCCESS"}
```

`documento["cnpj_emitente"]` ja E o CNPJ da propria empresa quando
`direcao='emitida'` (e assim que `calcular_direcao` classifica) -- nao precisa
resolver `empresa_id -> cnpj` por nenhum service novo ou existente. Nenhuma
mudanca em `SefazDistribuicaoService._publicar_evento_documento_novo` (ja
dispara esse hook para todo documento novo, qualquer direcao -- o filtro de
direcao acontece dentro do service).

### 5. Backfill -- documentos ja existentes

Nova task `sefaz_backfill_fiscal_task(empresa_id, cnpj_empresa)` em
`sefaz_tasks.py`:

```python
@celery_app.task(name="sefaz_backfill_fiscal_task", ...)
def sefaz_backfill_fiscal_task(empresa_id: int, cnpj_empresa: str) -> dict:
    pendentes = DocumentosRepository().listar_pendentes_fiscal(empresa_id)
    SefazFiscalTransportService().transportar_documentos(
        empresa_id=empresa_id,
        cnpj_empresa=cnpj_empresa,
        documentos=pendentes,
    )
    return {"status": "SUCCESS", "total_pendentes": len(pendentes)}
```

Disparo: no fim de `sefaz_sync_empresa_task`, sempre enfileira
`sefaz_backfill_fiscal_task` (fire-and-forget, mesma fila `sefaz`). A propria
task consulta `listar_pendentes_fiscal` e sai cedo se a lista vier vazia --
nao precisa de flag "ja rodou uma vez", rodar em toda sincronizacao e
idempotente e barato (poucos documentos pendentes na maioria das execucoes,
dado que o hook por documento novo ja cobre o fluxo normal).

### 6. API

`app/models/sefaz/schemas.py::SefazDocumentoResponse` ganha:

```python
processado_fiscal_em: datetime | None = None
```

`_documento_response` em `app/api/sefaz/routes.py` repassa o campo. Nenhuma
rota nova, nenhum contrato quebrado (campo aditivo) -- sem necessidade de
atualizar `docs/api-contracts.md` alem de registrar o campo novo.

### 7. Frontend (Painel)

`SefazSection` (`Painel/src/features/configuracoes/components/SefazSection/`):

- `sefaz.types.ts`: adiciona `processadoFiscalEm: string | null` ao tipo do
  documento (mapeado de `processado_fiscal_em`).
- Componente de listagem: badge "No Fiscal" (verde) quando presente, "Pendente"
  (neutro, sem tom de erro -- reprocessa sozinho) quando `null`.

## Erros e validacao

- Falha de parsing/consolidacao no `ProcessarNFeService`: log `warning`,
  documento continua pendente, sem excecao propagada (nao derruba sync nem
  worker).
- Documento sem `xml_armazenado` (`resNFe`): ignorado silenciosamente, fica
  pendente indefinidamente ate a SEFAZ eventualmente reenviar como `nfeProc`
  (fora do controle deste fluxo).
- `sefaz_evento_documento_novo_task` com `documento is None` (corrida rara
  entre insercao e consulta): retorna sucesso sem erro, o backfill seguinte
  cobre.

## Testes

- `SefazFiscalTransportService`: elegibilidade (direcao, xml presente, ja
  processado), sucesso marca `processado_fiscal_em`, falha do
  `ProcessarNFeService` nao marca e nao propaga excecao.
- `sefaz_evento_documento_novo_task`: chama o service so quando documento
  existe; documento inexistente nao quebra a task.
- `sefaz_backfill_fiscal_task`: lista pendentes corretamente, roda 2x seguidas
  sem duplicar (segunda vez `listar_pendentes_fiscal` retorna vazio).
- `DocumentosRepository.listar_pendentes_fiscal`/`marcar_processado_fiscal`:
  teste de integracao se `PLATAFORMA_FISCAL_TEST_DATABASE_URL` disponivel,
  senão cobertura via mock nos testes acima.
- Regressao: `ProcessarNFeService.executar_xmls_importados` chamado com tuplas
  vindas de `sefaz.documentos` (chave_acesso no lugar do nome de arquivo) --
  confirmar que nao ha dependencia implicita do formato de nome usado no
  upload manual.
