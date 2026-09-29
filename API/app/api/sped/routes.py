from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.api.shared.company_validation import validar_empresa_sped
from app.core.upload_security import validate_txt_uploads
from app.core.config import get_processamento_batch_root_dir
from app.core.path_security import resolve_safe_batch_path
from app.models.jobs.schemas import JobCreateResponse
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
  AnaliseClientesResponse,
  ConsultaClientesSpedResponse,
  AnaliseVendasResponse,
  AnaliseFiscalCfopResponse,
  AnaliseFiscalHierarquicaResponse,
  AnaliseFiscalNcmResponse,
  DashboardComprasResponse,
  DashboardVendasResponse,
)
from app.core.security import require_company_scope
from app.services.sped.sped_importacao_service import SpedImportacaoService
from app.services.sped.sped_process_service import ProcessarSpedFiscalService
from app.services.sped.sped_consulta_service import SpedConsultaService
from app.services.jobs.job_service import JobService
from app.services.shared.analise_relatorio_service import executar_analise_com_relatorio_ia
from app.services.shared.compras_dashboard_service import montar_dashboard_compras

router = APIRouter()
sped_router = APIRouter(prefix="/sped", tags=["SPED Fiscal"], dependencies=[Depends(require_company_scope)])

@sped_router.post("/processar", response_model=ProcessarSpedFiscalResponse)
def processar_sped_fiscal(
  request: ProcessarSpedFiscalRequest,
  cnpj_empresa_origem: str = Query(..., min_length=14, max_length=20),
):
  validar_empresa_sped(cnpj_empresa_origem)
  caminho_seguro = resolve_safe_batch_path(
    get_processamento_batch_root_dir(),
    request.arquivo_sped,
    tipo="SPED",
  )
  request_segura = request.model_copy(update={"arquivo_sped": caminho_seguro})
  return ProcessarSpedFiscalService().executar(request_segura)

@sped_router.post("/importar", response_model=ImportacaoSpedResponse)
async def importar_sped(
  arquivos: list[UploadFile] = File(...),
  cnpj_empresa_origem: str = Query(..., min_length=14, max_length=20),
):
  validar_empresa_sped(cnpj_empresa_origem)
  
  if len(arquivos) > 500:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="O limite máximo por importação é de 500 arquivos SPED.",
    )

  uploads_validados = await validate_txt_uploads(arquivos)
  conteudos = [(arquivo.filename, arquivo.content) for arquivo in uploads_validados]

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
  
@sped_router.get("/clientes", response_model=ConsultaClientesSpedResponse)
def consultar_clientes_sped(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int | None = Query(default=None, ge=1, le=1000),
  offset: int = Query(default=0, ge=0),
):
  validar_empresa_sped(emitente_cnpj)

  resultado = SpedConsultaService().listar_clientes(
    emitente_cnpj=emitente_cnpj,
    periodo_ano=periodo_ano,
    periodo_mes=periodo_mes,
    limite=limite,
    offset=offset,
  )

  return ConsultaClientesSpedResponse(status="ok", **resultado)
  
@sped_router.get("/analise/compras", response_model=AnaliseComprasResponse)
def consultar_analise_compras_sped(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int | None = Query(default=None, ge=1),
  gerar_relatorio_ia: bool = Query(default=False),
  formato_relatorio: str = Query(default="executivo", pattern="^(executivo|analitico)$"),
  layout: str | None = Query(default=None),
):
  validar_empresa_sped(emitente_cnpj)

  try:
    resultado = executar_analise_com_relatorio_ia(
      analise_fn=SpedConsultaService().analisar_compras,
      analise_kwargs={
        "emitente_cnpj": emitente_cnpj,
        "periodo_ano": periodo_ano,
        "periodo_mes": periodo_mes,
        "limite": limite,
      },
      gerar_relatorio_ia=gerar_relatorio_ia,
      tipo_relatorio="compras",
      formato_relatorio=formato_relatorio,
      layout=layout,
    )
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=str(exc),
    ) from exc

  except HTTPException:
    raise

  except Exception as exc:
    raise HTTPException(
      status_code=status.HTTP_502_BAD_GATEWAY,
      detail=f"Falha ao gerar relatório com IA: {exc}",
    ) from exc

  return AnaliseComprasResponse(status="ok", **resultado)

@sped_router.get("/analise/vendas", response_model=AnaliseVendasResponse)
def consultar_analise_vendas_sped(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int | None = Query(default=None, ge=1),
  gerar_relatorio_ia: bool = Query(default=False),
  formato_relatorio: str = Query(default="executivo", pattern="^(executivo|analitico)$"),
  layout: str | None = Query(default=None),
):
  validar_empresa_sped(emitente_cnpj)

  try:
    resultado = executar_analise_com_relatorio_ia(
      analise_fn=SpedConsultaService().analisar_vendas,
      analise_kwargs={
        "emitente_cnpj": emitente_cnpj,
        "periodo_ano": periodo_ano,
        "periodo_mes": periodo_mes,
        "limite": limite,
      },
      gerar_relatorio_ia=gerar_relatorio_ia,
      tipo_relatorio="vendas",
      formato_relatorio=formato_relatorio,
      layout=layout,
    )
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=str(exc),
    ) from exc

  except HTTPException:
    raise

  except Exception as exc:
    raise HTTPException(
      status_code=status.HTTP_502_BAD_GATEWAY,
      detail=f"Falha ao gerar relatório com IA: {exc}",
    ) from exc

  return AnaliseVendasResponse(status="ok", **resultado)

@sped_router.get("/analise/fiscal/cfop", response_model=AnaliseFiscalCfopResponse)
def consultar_analise_fiscal_cfop_sped(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int | None = Query(default=1000, ge=1, le=5000),
):
  validar_empresa_sped(emitente_cnpj)

  try:
    resultado = SpedConsultaService().analisar_fiscal_cfop(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      limite=limite,
    )
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=str(exc),
    ) from exc

  return AnaliseFiscalCfopResponse(status="ok", **resultado)

@sped_router.get("/analise/fiscal/ncm", response_model=AnaliseFiscalNcmResponse)
def consultar_analise_fiscal_ncm_sped(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int | None = Query(default=1000, ge=1, le=5000),
):
  validar_empresa_sped(emitente_cnpj)

  try:
    resultado = SpedConsultaService().analisar_fiscal_ncm(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      limite=limite,
    )
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=str(exc),
    ) from exc

  return AnaliseFiscalNcmResponse(status="ok", **resultado)

@sped_router.get("/analise/fiscal/hierarquia", response_model=AnaliseFiscalHierarquicaResponse)
def consultar_analise_fiscal_hierarquia_sped(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  nivel_atual: str | None = Query(default=None),
  estado: str | None = Query(default=None),
  cidade: str | None = Query(default=None),
  ncm: str | None = Query(default=None),
  produto_codigo: str | None = Query(default=None),
  limite: int | None = Query(default=1000, ge=1, le=5000),
  offset: int = Query(default=0, ge=0),
):
  validar_empresa_sped(emitente_cnpj)

  try:
    resultado = SpedConsultaService().analisar_fiscal_hierarquia(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      nivel_atual=nivel_atual,
      estado=estado,
      cidade=cidade,
      ncm=ncm,
      produto_codigo=produto_codigo,
      limite=limite,
      offset=offset,
    )
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=str(exc),
    ) from exc

  return AnaliseFiscalHierarquicaResponse(status="ok", **resultado)

@sped_router.get("/analise/compras/dashboard", response_model=DashboardComprasResponse)
def consultar_dashboard_compras_sped(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int = Query(default=5, ge=1, le=20),
):
  validar_empresa_sped(emitente_cnpj)
  dashboard = montar_dashboard_compras(
    consulta_service=SpedConsultaService(),
    emitente_cnpj=emitente_cnpj,
    origem_documento="sped",
    periodo_ano=periodo_ano,
    periodo_mes=periodo_mes,
    limite=limite,
  )
  return DashboardComprasResponse(**dashboard)

@sped_router.get("/analise/vendas/dashboard", response_model=DashboardVendasResponse)
def consultar_dashboard_vendas_sped(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int = Query(default=5, ge=1, le=20),
):
  validar_empresa_sped(emitente_cnpj)
  try:
    return SpedConsultaService().consultar_dashboard_vendas(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      limite=limite,
    )
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=str(exc),
    ) from exc

@sped_router.get("/analise/clientes", response_model=AnaliseClientesResponse)
def consultar_analise_clientes_sped(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int | None = Query(default=None, ge=1),
  gerar_relatorio_ia: bool = Query(default=False),
  formato_relatorio: str = Query(default="executivo", pattern="^(executivo|analitico)$"),
):
  validar_empresa_sped(emitente_cnpj)

  try:
    resultado = executar_analise_com_relatorio_ia(
      analise_fn=SpedConsultaService().analisar_clientes,
      analise_kwargs={
        "emitente_cnpj": emitente_cnpj,
        "periodo_ano": periodo_ano,
        "periodo_mes": periodo_mes,
        "limite": limite,
      },
      gerar_relatorio_ia=gerar_relatorio_ia,
      tipo_relatorio="clientes",
      formato_relatorio=formato_relatorio,
    )
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=str(exc),
    ) from exc

  except HTTPException:
    raise

  except Exception as exc:
    raise HTTPException(
      status_code=status.HTTP_502_BAD_GATEWAY,
      detail=f"Falha ao gerar relatÃ³rio com IA: {exc}",
    ) from exc

  return AnaliseClientesResponse(status="ok", **resultado)

@sped_router.get("/pendencias", response_model=ImportacaoSpedPendenciasResponse)
def consultar_pendencias_sped(cnpj_emitente: str = Query(..., min_length=14, max_length=20)):
  validar_empresa_sped(cnpj_emitente)
  service = SpedImportacaoService()
  total_pendentes = service.contar_pendentes(cnpj_emitente)

  return ImportacaoSpedPendenciasResponse(
    status="ok",
    cnpj_emitente=cnpj_emitente,
    total_pendentes=total_pendentes,
    possui_pendentes=total_pendentes > 0,
  )


@sped_router.post(
  "/processar-importados",
  response_model=JobCreateResponse,
  status_code=status.HTTP_202_ACCEPTED,
)
def processar_sped_importados(cnpj_emitente: str = Query(..., min_length=14, max_length=20)):
  validar_empresa_sped(cnpj_emitente)
  service = SpedImportacaoService()

  if service.contar_pendentes(cnpj_emitente) == 0:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Nenhum arquivo SPED pendente encontrado para o CNPJ informado.",
    )

  return JobService().criar_processamento_sped_importados(cnpj_emitente=cnpj_emitente)

@sped_router.get("/kpis", response_model=ConsultaKPIResponse)
def consultar_kpis_sped(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int = Query(default=100),
  offset: int = Query(default=0),
):
  validar_empresa_sped(emitente_cnpj)

  resultados = SpedConsultaService().listar_kpis(
    emitente_cnpj=emitente_cnpj,
    periodo_ano=periodo_ano,
    periodo_mes=periodo_mes,
    limite=limite,
    offset=offset,
  )

  return ConsultaKPIResponse(status="ok", total=len(resultados), resultados=resultados)

router.include_router(sped_router)
