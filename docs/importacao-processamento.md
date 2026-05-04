# Importacao e Processamento Fiscal

O fluxo e em duas fases: importacao para staging e processamento posterior. Isso permite receber varios arquivos, consultar pendencias e processar em lote.

## Arquivos de referencia no codigo

- `API/app/api/nfe/routes.py`
- `API/app/api/sped/routes.py`
- `API/app/core/upload_security.py`
- `API/app/services/nfe/xml_importacao_service.py`
- `API/app/services/nfe/process_nfe.py`
- `API/app/services/sped/sped_importacao_service.py`
- `API/app/services/sped/sped_process_service.py`
- `API/app/domain/sped/reader.py`
- `Painel/src/pages/ImportacaoXML.tsx`
- `Painel/src/pages/ImportacaoSPED.tsx`
- `Painel/src/services/nfe.ts`
- `Painel/src/services/sped.ts`

## XML/NFe

Endpoints:

- `POST /api/nfe/xml/importar`
- `GET /api/nfe/xml/pendencias`
- `POST /api/nfe/xml/processar-importados`

Regras implementadas:

- permitido apenas para empresas com `tem_sped=false`;
- aceita ate 10.000 arquivos por chamada na rota;
- todos os arquivos devem ser `.xml`;
- valida tamanho por arquivo e tamanho total;
- extrai CNPJ do emitente e compara com `cnpj_empresa_origem`;
- rejeita duplicidade por `cnpj_emitente + hash_arquivo`;
- rejeita NFC-e cancelada/inutilizada e NFSe cancelada quando identificavel;
- grava staging em `notas_xml_importados`;
- marca `processado_em` apos processamento.

Falhas parciais sao retornadas por arquivo em `resultados`. Um arquivo rejeitado nao impede necessariamente a importacao de outros arquivos validos.

## SPED Fiscal

Endpoints:

- `POST /api/sped/importar`
- `GET /api/sped/pendencias`
- `POST /api/sped/processar-importados`

Regras implementadas:

- permitido apenas para empresas com `tem_sped=true`;
- aceita ate 500 arquivos por chamada na rota;
- todos os arquivos devem ser `.txt`;
- valida tamanho por arquivo e tamanho total;
- le o registro `0000` para obter o CNPJ;
- rejeita arquivo cujo CNPJ difere da empresa autenticada;
- rejeita duplicidade por `cnpj_emitente + hash_arquivo`;
- grava staging em `sped_importados`;
- no processamento, carrega participantes, produtos, documentos, itens, KPIs e apuracao ICMS quando os registros existem.

## Reprocessamento

O reprocessamento automatico de arquivos ja marcados com `processado_em` nao e exposto por endpoint. Para reprocessar, hoje seria necessario procedimento operacional controlado no banco, com backup e registro de auditoria.

## Comportamento esperado em falhas

- Arquivo invalido: `400` ou item com `status=erro`.
- Fluxo fiscal incorreto para a empresa: `400`.
- CNPJ fora do escopo autenticado: `403`.
- Sem pendencias: resposta com `possui_pendentes=false` ou erro operacional dependendo da rota.
- Falha de banco: `503` ou erro interno conforme ponto de falha.

## Checklist operacional

- Confirmar `tem_sped` da empresa antes de importar.
- Conferir CNPJ do arquivo.
- Importar lote pequeno primeiro em ambiente novo.
- Consultar pendencias.
- Processar pendencias.
- Validar dashboards e analises do periodo.
- Conferir inconsistencias e logs de erros parciais.
