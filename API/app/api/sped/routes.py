from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.models.nfe.schemas import ConsultaKPIResponse
from app.models.sped.schemas import (
  ImportacaoSpedArquivoResultado,
  ImportacaoSpedPendenciasResponse,
  ImportacaoSpedResponse,
  ProcessarSpedFiscalRequest,
  ProcessarSpedFiscalResponse,
  ProcessarSpedImportadosResponse,
  RegistroSpedResumo,
  AnaliseComprasResponse,
)
from app.services.sped.sped_importacao_service import SpedImportacaoService
from app.services.sped.sped_process_service import ProcessarSpedFiscalService
from app.services.company_profile_service import CompanyProfileService
from app.services.sped.sped_consulta_service import SpedConsultaService

router = APIRouter()
sped_router = APIRouter(prefix="/sped", tags=["SPED Fiscal"])

def _validar_empresa_sped(cnpj: str):
  if not CompanyProfileService().empresa_tem_sped(cnpj):
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Esta empresa está configurada para XML e não para SPED Fiscal.",
    )

@sped_router.post("/processar", response_model=ProcessarSpedFiscalResponse)
def processar_sped_fiscal(request: ProcessarSpedFiscalRequest):
  return ProcessarSpedFiscalService().executar(request)

@sped_router.post("/importar", response_model=ImportacaoSpedResponse)
async def importar_sped(
  arquivos: list[UploadFile] = File(...),
  cnpj_empresa_origem: str = Query(..., min_length=14, max_length=20),
):
  _validar_empresa_sped(cnpj_empresa_origem)
  
  if len(arquivos) > 500:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="O limite máximo por importação é de 500 arquivos SPED.",
    )

  conteudos: list[tuple[str, bytes]] = []
  for arquivo in arquivos:
    if not arquivo.filename.lower().endswith(".txt"):
      continue
    conteudos.append((arquivo.filename, await arquivo.read()))

  if not conteudos:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Nenhum arquivo TXT válido foi enviado.",
    )

  try:
    resultados_service = SpedImportacaoService().importar_arquivos(
      conteudos,
      cnpj_empresa_origem=cnpj_empresa_origem,
    )
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=str(exc),
    ) from exc

  resultados = [ImportacaoSpedArquivoResultado(**resultado.__dict__) for resultado in resultados_service]

  return ImportacaoSpedResponse(
    status="ok",
    total_arquivos=len(resultados),
    importados=sum(1 for item in resultados if item.status == "importado"),
    duplicados=sum(1 for item in resultados if item.status == "duplicado"),
    erros=sum(1 for item in resultados if item.status == "erro"),
    resultados=resultados,
  )
  
@sped_router.get("/analise/compras", response_model=AnaliseComprasResponse)
def consultar_analise_compras_sped(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int = Query(default=5, ge=1, le=20),
):
  _validar_empresa_sped(emitente_cnpj)

  resultado = SpedConsultaService().analisar_compras(
    emitente_cnpj=emitente_cnpj,
    periodo_ano=periodo_ano,
    periodo_mes=periodo_mes,
    limite=limite,
  )

  return AnaliseComprasResponse(status="ok", **resultado)

@sped_router.get("/pendencias", response_model=ImportacaoSpedPendenciasResponse)
def consultar_pendencias_sped(cnpj_emitente: str = Query(..., min_length=14, max_length=20)):
  _validar_empresa_sped(cnpj_emitente)
  service = SpedImportacaoService()
  total_pendentes = service.contar_pendentes(cnpj_emitente)

  return ImportacaoSpedPendenciasResponse(
    status="ok",
    cnpj_emitente=cnpj_emitente,
    total_pendentes=total_pendentes,
    possui_pendentes=total_pendentes > 0,
  )


@sped_router.post("/processar-importados", response_model=ProcessarSpedImportadosResponse)
def processar_sped_importados(cnpj_emitente: str = Query(..., min_length=14, max_length=20)):
  _validar_empresa_sped(cnpj_emitente)
  service = SpedImportacaoService()

  try:
    registros, total_linhas, ids_processados = service.processar_importados(cnpj_emitente)
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=str(exc),
    ) from exc

  if not ids_processados:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Nenhum arquivo SPED pendente encontrado para o CNPJ informado.",
    )

  service.marcar_como_processados(ids_processados)
  config = ProcessarSpedFiscalService().config

  resumo_ordenado = sorted(registros.items(), key=lambda item: (-item[1], item[0]))

  return ProcessarSpedImportadosResponse(
    status="processado",
    cnpj_emitente=cnpj_emitente,
    total_linhas=total_linhas,
    total_registros_identificados=sum(registros.values()),
    total_arquivos_processados=len(ids_processados),
    resumo_registros=[
      RegistroSpedResumo(registro=registro, quantidade=quantidade)
      for registro, quantidade in resumo_ordenado
    ],
    banco_sped=config["database"],
  )

@sped_router.get("/kpis", response_model=ConsultaKPIResponse)
def consultar_kpis_sped(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int = Query(default=100),
  offset: int = Query(default=0),
):
  _validar_empresa_sped(emitente_cnpj)

  resultados = SpedConsultaService().listar_kpis(
    emitente_cnpj=emitente_cnpj,
    periodo_ano=periodo_ano,
    periodo_mes=periodo_mes,
    limite=limite,
    offset=offset,
  )

  return ConsultaKPIResponse(status="ok", total=len(resultados), resultados=resultados)

router.include_router(sped_router)