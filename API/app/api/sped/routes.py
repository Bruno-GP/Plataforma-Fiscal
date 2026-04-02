from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.api.shared.analytics import obter_periodo_anterior, resumir_vendas_por_kpis
from app.core.upload_security import validate_txt_uploads
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
  DashboardComprasResponse,
  DashboardVendasResponse,
  DashboardVendasResumo,
  SerieMensalComprasItem,
  SerieMensalVendasItem,
)
from app.core.security import require_company_scope
from app.services.sped.sped_importacao_service import SpedImportacaoService
from app.services.sped.sped_process_service import ProcessarSpedFiscalService
from app.services.company_profile_service import CompanyProfileService
from app.services.sped.sped_consulta_service import SpedConsultaService
from app.services.AI.openai_report_service import OpenAIReportService

router = APIRouter()
sped_router = APIRouter(prefix="/sped", tags=["SPED Fiscal"], dependencies=[Depends(require_company_scope)])

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
  _validar_empresa_sped(emitente_cnpj)

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
  _validar_empresa_sped(emitente_cnpj)

  try:
    resultado = SpedConsultaService().analisar_compras(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      limite=limite,
    )

    if gerar_relatorio_ia:
      ia_service = OpenAIReportService()
      if not ia_service.disponivel():
        raise HTTPException(
          status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
          detail=(
            "Integração com OpenAI indisponível. "
            "Configure OPENAI_API_KEY no ambiente da API."
          ),
        )

      resultado["relatorio_ia"] = ia_service.gerar_relatorio_compras(
        resultado,
        formato_relatorio,
        layout,
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
  _validar_empresa_sped(emitente_cnpj)

  try:
    resultado = SpedConsultaService().analisar_vendas(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      limite=limite,
    )

    if gerar_relatorio_ia:
      ia_service = OpenAIReportService()
      if not ia_service.disponivel():
        raise HTTPException(
          status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
          detail=(
            "Integração com OpenAI indisponível. "
            "Configure OPENAI_API_KEY no ambiente da API."
          ),
        )

      resultado["relatorio_ia"] = ia_service.gerar_relatorio_vendas(
        resultado,
        formato_relatorio,
        layout,
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
  limite: int | None = Query(default=20, ge=1),
):
  _validar_empresa_sped(emitente_cnpj)

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

@sped_router.get("/analise/compras/dashboard", response_model=DashboardComprasResponse)
def consultar_dashboard_compras_sped(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int = Query(default=5, ge=1, le=20),
):
  _validar_empresa_sped(emitente_cnpj)
  service = SpedConsultaService()

  anos_disponiveis = sorted(
    {
      item.periodo_ano
      for item in service.listar_kpis(emitente_cnpj=emitente_cnpj, limite=120)
      if item.periodo_ano
    },
    reverse=True,
  )
  ano_referencia = periodo_ano or (anos_disponiveis[0] if anos_disponiveis else None)

  if ano_referencia is None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Nenhum perÃ­odo disponÃ­vel para o emitente informado.",
    )

  ano_anterior, mes_anterior = obter_periodo_anterior(ano_referencia, periodo_mes)

  resumo_atual = service.analisar_compras(
    emitente_cnpj=emitente_cnpj,
    periodo_ano=ano_referencia,
    periodo_mes=periodo_mes,
    limite=limite,
  )
  resumo_anterior = service.analisar_compras(
    emitente_cnpj=emitente_cnpj,
    periodo_ano=ano_anterior,
    periodo_mes=mes_anterior,
    limite=limite,
  )
  serie_mensal = [
    SerieMensalComprasItem(
      periodo_ano=ano_referencia,
      periodo_mes=mes,
      total_comprado=service.analisar_compras(
        emitente_cnpj=emitente_cnpj,
        periodo_ano=ano_referencia,
        periodo_mes=mes,
        limite=limite,
      )["total_comprado"],
    )
    for mes in range(1, 13)
  ]

  return DashboardComprasResponse(
    status="ok",
    emitente_cnpj=emitente_cnpj,
    periodo_ano=ano_referencia,
    periodo_mes=periodo_mes,
    anos_disponiveis=anos_disponiveis,
    resumo_atual=AnaliseComprasResponse(status="ok", **resumo_atual),
    resumo_anterior=AnaliseComprasResponse(status="ok", **resumo_anterior),
    serie_mensal=serie_mensal,
  )

@sped_router.get("/analise/vendas/dashboard", response_model=DashboardVendasResponse)
def consultar_dashboard_vendas_sped(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int = Query(default=5, ge=1, le=20),
):
  _validar_empresa_sped(emitente_cnpj)
  service = SpedConsultaService()

  resultados_anos = service.listar_kpis(emitente_cnpj=emitente_cnpj, limite=120)
  anos_disponiveis = sorted(
    {item.periodo_ano for item in resultados_anos if item.periodo_ano},
    reverse=True,
  )
  ano_referencia = periodo_ano or (anos_disponiveis[0] if anos_disponiveis else None)

  if ano_referencia is None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Nenhum perÃ­odo disponÃ­vel para o emitente informado.",
    )

  resultados_ano_atual = service.listar_kpis(
    emitente_cnpj=emitente_cnpj,
    periodo_ano=ano_referencia,
    limite=120,
  )
  resultados_ano_anterior = service.listar_kpis(
    emitente_cnpj=emitente_cnpj,
    periodo_ano=ano_referencia - 1,
    limite=120,
  )

  if periodo_mes is not None:
    resultados_filtrados = [item for item in resultados_ano_atual if item.periodo_mes == periodo_mes]
    ano_anterior, mes_anterior = obter_periodo_anterior(ano_referencia, periodo_mes)
    resultados_anteriores = (
      [item for item in resultados_ano_atual if item.periodo_mes == mes_anterior]
      if ano_anterior == ano_referencia
      else [item for item in resultados_ano_anterior if item.periodo_mes == mes_anterior]
    )
  else:
    resultados_filtrados = resultados_ano_atual
    resultados_anteriores = resultados_ano_anterior

  serie_mensal = [
    SerieMensalVendasItem(
      periodo_ano=ano_referencia,
      periodo_mes=item.periodo_mes or 0,
      total_vendido=Decimal(str(item.kpis.total_vendas or 0)),
      quantidade_notas=int(item.kpis.quantidade_notas or 0),
      total_impostos=(
        Decimal(str(item.kpis.total_icms or 0))
        + Decimal(str(item.kpis.total_ipi or 0))
        + Decimal(str(item.kpis.total_pis or 0))
        + Decimal(str(item.kpis.total_cofins or 0))
      ),
    )
    for item in sorted(resultados_ano_atual, key=lambda resultado: resultado.periodo_mes or 0)
    if item.periodo_mes
  ]

  return DashboardVendasResponse(
    status="ok",
    emitente_cnpj=emitente_cnpj,
    periodo_ano=ano_referencia,
    periodo_mes=periodo_mes,
    anos_disponiveis=anos_disponiveis,
    resumo_atual=resumir_vendas_por_kpis(resultados_filtrados, DashboardVendasResumo, limite),
    resumo_anterior=resumir_vendas_por_kpis(resultados_anteriores, DashboardVendasResumo, limite),
    serie_mensal=serie_mensal,
  )

@sped_router.get("/analise/clientes", response_model=AnaliseClientesResponse)
def consultar_analise_clientes_sped(
  emitente_cnpj: str = Query(..., min_length=14, max_length=20),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int | None = Query(default=None, ge=1),
  gerar_relatorio_ia: bool = Query(default=False),
  formato_relatorio: str = Query(default="executivo", pattern="^(executivo|analitico)$"),
):
  _validar_empresa_sped(emitente_cnpj)

  try:
    resultado = SpedConsultaService().analisar_clientes(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      limite=limite,
    )

    if gerar_relatorio_ia:
      ia_service = OpenAIReportService()
      if not ia_service.disponivel():
        raise HTTPException(
          status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
          detail=(
            "IntegraÃ§Ã£o com OpenAI indisponÃ­vel. "
            "Configure OPENAI_API_KEY no ambiente da API."
          ),
        )

      resultado["relatorio_ia"] = ia_service.gerar_relatorio_clientes(resultado, formato_relatorio)

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
