# ADR 0001 — Biblioteca para consumo do NFeDistribuicaoDFe

Data: 2026-08-14
Status: Aceito

## Contexto

O módulo de Sincronização SEFAZ precisa, para cada empresa com certificado digital A1 ativo,
consultar diariamente o webservice `NFeDistribuicaoDFe` (`distDFeInt`) do Ambiente Nacional da
NF-e, cobrindo notas emitidas pelo CNPJ da empresa e notas emitidas contra o CNPJ (compras).
Isso exige três capacidades que o backend hoje não tem:

1. Montar/assinar XML com certificado A1 (assinatura XML-DSig, leitura de `.pfx`/`.p12`).
2. Falar SOAP com TLS mutual contra o Ambiente Nacional (ou SVRS, dependendo da UF do
   certificado), incluindo roteamento por UF e contingência.
3. Fazer parsing de `resNFe`/`resEvento`/`nfeProc` (schemas XSD da NF-e 4.00) e tratar `cStat`
   (137 = nenhum documento novo, 656 = consumo indevido/bloqueio).

Já existe um documento de mapeamento anterior (`docs/mapeamento-busca-xml-sefaz.md`,
2026-05-08) que cobria esse mesmo problema em escopo menor (client encapsulado, reaproveitando
o staging `notas_xml_importados`) e recomendava **não** usar lib fiscal pronta, para não
acoplar o domínio a uma dependência externa. O escopo atual é maior — schema `sefaz` dedicado,
Manifestação do Destinatário completa, tela própria de Integrações — o que muda o cálculo de
custo/benefício de reinventar a camada de assinatura/SOAP.

`API/app/requirements.txt` hoje não tem `lxml`, `zeep`, `signxml` nem qualquer lib de
assinatura A1/SOAP. `cryptography==43.0.1` já está presente (usado pelo Fernet do Conta Azul),
serve para ler o `.pfx`.

## Opções avaliadas

### A — Implementação direta (zeep + signxml + cryptography)

Escrever o client SOAP e a assinatura XML-DSig na mão, seguindo o manual de integração
`distDFeInt` publicado pela SEFAZ.

- Prós: controle total, zero dependência de terceiro para a parte crítica.
- Contras: superfície grande pra manter (schemas por UF/SVRS, mudanças de Nota Técnica,
  contingência, timeout/retry), maior risco de bug de segurança numa assinatura XML feita à
  mão (é uma área historicamente cheia de pegadinha — canonicalização, referência de
  transformação, etc.), nenhum precedente no time com essa camada.

### B — Bibliotecas Akretion/OCA: `nfelib` + `erpbrasil.assinatura` + `erpbrasil.edoc`

- `nfelib`: bindings Python gerados via `xsdata` a partir dos XSD oficiais da NF-e/NFC-e/CT-e/
  MDF-e/BP-e/NFS-e nacional. Mantido pela Akretion, usado por outros projetos do ecossistema
  fiscal brasileiro em Python.
- `erpbrasil.assinatura`: assinatura XML-DSig com certificado A1/A3.
- `erpbrasil.edoc`: client de transmissão (SOAP, roteamento por UF/SVRS, contingência),
  incluindo o fluxo `distDFeInt`.

Verificado em 2026-08-14: `erpbrasil.edoc` teve release 3.1.1 em 2026-01-08 (mantido ativamente
até período recente). `nfelib` está em 2.3.0, também com atividade recente.

- Prós: não reinventa a parte mais arriscada (assinatura + SOAP + roteamento UF), maintainers
  dedicados a acompanhar Notas Técnicas da SEFAZ, usado em produção por outros ERPs (ex.
  localização brasileira do Odoo).
- Contras: dependência de terceiro fora do controle do time; exige aprender a API dessas libs;
  se o projeto parar de ser mantido, herdamos a manutenção de qualquer forma — mas nesse caso
  partimos de uma base funcional em vez do zero.

### C — PyNFe

Lib histórica com client de webservice embutido.

- Contras: manutenção incerta, sem garantia de estar atualizada para a NT 2026.004 (CNPJ
  alfanumérico, vigente desde 2026-07-31) nem para mudanças recentes de schema. Descartada.

### D — Gateway pago (Nuvem Fiscal / Focus NFe / TecnoSpeed)

Terceiro cuida de assinatura/SOAP/contingência e, opcionalmente, custódia do certificado,
cobrando por consulta/empresa.

- É decisão de custo/produto, não técnica — não decidida nesta ADR. Perguntado ao usuário
  explicitamente; resposta: seguir com a opção B agora. Gateway pago fica descartado para este
  ciclo, pode ser revisitado depois se o volume/custo operacional da opção B não compensar.

## Decisão

Opção B: `nfelib` + `erpbrasil.assinatura` + `erpbrasil.edoc`, encapsuladas atrás de
`SefazDistribuicaoService` (ver spec de design) para que o resto do domínio `sefaz` nunca
importe essas libs diretamente — só esse serviço conhece a API delas. Isso preserva a
possibilidade de trocar de biblioteca (ou migrar pra opção A/D) sem reescrever
services/repositories/rotas que dependem de `sefaz_documentos`/`sefaz_eventos`.

## Consequências

- Novas dependências em `API/app/requirements.txt`: `nfelib`, `erpbrasil.assinatura`,
  `erpbrasil.edoc` (e transitivas: `lxml`, `xsdata`, `signxml` ou equivalente interno delas).
  Fixar versões exatas na implementação (Fase 2), não usar `>=` solto.
- Testes unitários dos services principais devem mockar a fronteira dessas libs (o client SOAP
  e a assinatura), não a rede real — mesmo padrão já usado nos testes do Conta Azul
  (mock no ponto de uso, sem infra real).
- `docs/mapeamento-busca-xml-sefaz.md` fica desatualizado no ponto "recomendaria encapsular...
  para não acoplar a uma dependência externa" — este ADR substitui essa recomendação para o
  escopo atual (schema `sefaz` dedicado + manifestação completa). O restante do documento
  (referências oficiais, regras de `cStat` 137/656, janela de espera) continua válido e é
  reaproveitado no design.
