from fastapi import APIRouter, Query, HTTPException, status, UploadFile, File

from app.services.nfe.process_nfe import ProcessarNFeService
from app.services.nfe.nfe_consulta_service import NFeConsultaService
from app.services.nfe.xml_importacao_service import XMLImportacaoService
from app.models.nfe.schemas import (
  ComparativoKPIMensalResponse,
  ConsultaNFeResponse,
  ConsultaKPIResponse,
  ImportacaoXMLResponse,
  ImportacaoXMLArquivoResultado,
  ProcessarNFeRequest,
  ProcessarNFeResponse
)

router = APIRouter()

nfe_router = APIRouter(prefix="/nfe", tags=["NFe"])

# -------------------------
# Processamento
# -------------------------
@nfe_router.post("/processar", response_model=ProcessarNFeResponse)
def processar_nfe(request: ProcessarNFeRequest):
  return ProcessarNFeService().executar(request)

@nfe_router.post("/xml/importar", response_model=ImportacaoXMLResponse)
async def importar_xml(arquivos: list[UploadFile] = File(...)):
  if len(arquivos) > 10000:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="O limite máximo por importação é de 10000 XMLs.",
    )

  conteudos: list[tuple[str, bytes]] = []
  for arquivo in arquivos:
    if not arquivo.filename.lower().endswith(".xml"):
      continue
    conteudos.append((arquivo.filename, await arquivo.read()))

  if not conteudos:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Nenhum arquivo XML válido foi enviado.",
    )

  resultados_service = XMLImportacaoService().importar_arquivos(conteudos)
  resultados = [ImportacaoXMLArquivoResultado(**resultado.__dict__) for resultado in resultados_service]

  return ImportacaoXMLResponse(
    status="ok",
    total_arquivos=len(resultados),
    importados=sum(1 for item in resultados if item.status == "importado"),
    duplicados=sum(1 for item in resultados if item.status == "duplicado"),
    erros=sum(1 for item in resultados if item.status == "erro"),
    resultados=resultados,
  )
  
@nfe_router.post("/xml/processar-importados", response_model=ProcessarNFeResponse)
def processar_xmls_importados(cnpj_emitente: str = Query(..., min_length=14, max_length=20)):
  service_importacao = XMLImportacaoService()
  xmls_importados = service_importacao.listar_xmls_importados_nao_processados(cnpj_emitente)

  if not xmls_importados:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Nenhum XML pendente encontrado para o CNPJ informado.",
    )

  resposta, ids_processados = ProcessarNFeService().executar_xmls_importados(
    cnpj_emitente=cnpj_emitente,
    xmls_importados=xmls_importados,
  )

  if resposta.status == "processado":
    service_importacao.marcar_como_processados(ids_processados)

  return resposta

# -------------------------
# Consulta de KPIs (consolidado)
# -------------------------
@nfe_router.get("/kpis", response_model=ConsultaKPIResponse)
def consultar_kpis(
    emitente_cnpj: str | None = Query(default=None),
    periodo_ano: int | None = Query(default=None),
    periodo_mes: int | None = Query(default=None),
    limite: int = Query(default=100),
    offset: int = Query(default=0),
):
    service = NFeConsultaService()

    emitente_resolvido = service._normalizar_cnpj_filtro(
        emitente_cnpj,
        permitir_zerado=False
    )

    if not emitente_resolvido:
        raise HTTPException(
            status_code=400,
            detail="Informe um emitente_cnpj válido.",
        )

    resultados = service.listar_kpis(
        emitente_cnpj=emitente_resolvido,
        periodo_ano=periodo_ano,
        periodo_mes=periodo_mes,
        limite=limite,
        offset=offset,
    )

    return ConsultaKPIResponse(
        status="ok",
        total=len(resultados),
        resultados=resultados,
    )
  
# -------------------------
# Comparativo mensal de KPIs
# -------------------------
@nfe_router.get(
  "/kpis/comparativo",
  response_model=ComparativoKPIMensalResponse,
)
def comparar_kpis_mensal(
  emitente_cnpj: str | None = Query(default=None),
  email: str | None = Query(default=None),
  periodo_ano: int = Query(..., ge=2000, le=2100),
  periodo_mes: int = Query(..., ge=1, le=12),
  periodo_anterior_ano: int | None = Query(default=None, ge=2000, le=2100),
  periodo_anterior_mes: int | None = Query(default=None, ge=1, le=12),
):
  if periodo_anterior_ano is None or periodo_anterior_mes is None:
    if periodo_mes == 1:
      periodo_anterior_mes = 12
      periodo_anterior_ano = periodo_ano - 1
    else:
      periodo_anterior_mes = periodo_mes - 1
      periodo_anterior_ano = periodo_ano

  service = NFeConsultaService()
  
  emitente_resolvido = service.resolver_emitente_cnpj(
    emitente_cnpj=emitente_cnpj,
    email=email,
  )
  
  if not emitente_resolvido:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="CNPJ inválido ou zerado não é permitido.",
    )
  
  kpis = service.comparar_kpis_mensal(
    emitente_cnpj=emitente_resolvido,
    periodo_ano=periodo_ano,
    periodo_mes=periodo_mes,
    periodo_anterior_ano=periodo_anterior_ano,
    periodo_anterior_mes=periodo_anterior_mes,
  )

  if not kpis:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=(
        "KPIs não encontrados para o período atual e/ou "
        "o período anterior."
      ),
    )

  return ComparativoKPIMensalResponse(
    status="ok",
    periodo_atual_ano=periodo_ano,
    periodo_atual_mes=periodo_mes,
    periodo_anterior_ano=periodo_anterior_ano,
    periodo_anterior_mes=periodo_anterior_mes,
    emitente_cnpj=emitente_resolvido,
    kpis=kpis,
  )

# -------------------------
# Comparativo mensal de KPIs (auto)
# -------------------------
@nfe_router.get(
  "/kpis/comparativo/atual",
  response_model=ComparativoKPIMensalResponse,
)
def comparar_kpis_mensal_atual(
  emitente_cnpj: str | None = Query(default=None),
  email: str | None = Query(default=None),
):
  service = NFeConsultaService()
  
  emitente_resolvido = service.resolver_emitente_cnpj(
    emitente_cnpj=emitente_cnpj,
    email=email,
  )
  
  if not emitente_resolvido:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Informe um emitente_cnpj válido ou um email cadastrado.",
    )
  
  try:
    periodos_disponiveis = service.obter_periodos_disponiveis(emitente_resolvido)
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=str(exc),
    ) from exc
    
  if not periodos_disponiveis:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Nenhum processamento encontrado para o emitente.",
    )

  periodo_ano, periodo_mes = periodos_disponiveis[0]
  if len(periodos_disponiveis) > 1:
    periodo_anterior_ano, periodo_anterior_mes = periodos_disponiveis[1]
  elif periodo_mes == 1:
    periodo_anterior_mes = 12
    periodo_anterior_ano = periodo_ano - 1
  else:
    periodo_anterior_mes = periodo_mes - 1
    periodo_anterior_ano = periodo_ano

  kpis = service.comparar_kpis_mensal(
    emitente_cnpj=emitente_resolvido,
    periodo_ano=periodo_ano,
    periodo_mes=periodo_mes,
    periodo_anterior_ano=periodo_anterior_ano,
    periodo_anterior_mes=periodo_anterior_mes
  )

  if not kpis:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=(
        "KPIs não encontrados para o período atual e/ou "
        "o período anterior."
      ),
    )

  return ComparativoKPIMensalResponse(
    status="ok",
    periodo_atual_ano=periodo_ano,
    periodo_atual_mes=periodo_mes,
    periodo_anterior_ano=periodo_anterior_ano,
    periodo_anterior_mes=periodo_anterior_mes,
    emitente_cnpj=emitente_resolvido,
    kpis=kpis,
  )

# -------------------------
# Consulta de notas (detalhado)
# -------------------------
@nfe_router.get("/notas", response_model=ConsultaNFeResponse)
def consultar_notas(
  emitente_cnpj: str | None = Query(default=None),
  periodo_ano: int | None = Query(default=None, ge=2000, le=2100),
  periodo_mes: int | None = Query(default=None, ge=1, le=12),
  limite: int = Query(default=100, ge=1, le=500),
  offset: int = Query(default=0, ge=0),
):
  # ⚠️ Ainda não existe um service de consulta detalhada de notas no seu código.
  # Mantive a rota separada para o front/Make já ficar com a arquitetura certa.
  raise HTTPException(
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    detail="Consulta detalhada de notas ainda não implementada. Use GET /nfe/kpis para KPIs consolidados.",
  )


router.include_router(nfe_router)