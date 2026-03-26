from decimal import Decimal

from fastapi import APIRouter, Query, HTTPException, status, UploadFile, File

from app.services.nfe.process_nfe import ProcessarNFeService
from app.services.nfe.nfe_consulta_service import NFeConsultaService
from app.services.company_profile_service import CompanyProfileService
from app.services.nfe.xml_importacao_service import XMLImportacaoService
from app.services.AI.openai_report_service import OpenAIReportService
from app.models.nfe.schemas import (
  ComparativoKPIMensalResponse,
  ConsultaNFeResponse,
  ConsultaKPIResponse,
  ImportacaoXMLResponse,
  ImportacaoXMLArquivoResultado,
  ImportacaoXMLPendenciasResponse,
  ProcessarNFeRequest,
  ProcessarNFeResponse,
  ProcessarNFeResponse,
  AnaliseComprasResponse,
  AnaliseVendasResponse,
  AnaliseClientesResponse,
  DashboardComprasResponse,
  DashboardVendasResponse,
  DashboardVendasResumo,
  SerieMensalComprasItem,
  SerieMensalVendasItem,
)

router = APIRouter()

# Sub-roteador de NFe/NFCe. Centraliza upload, processamento e consultas analíticas.

nfe_router = APIRouter(prefix="/nfe", tags=["NFe"])

def _validar_empresa_xml(cnpj: str):
  if CompanyProfileService().empresa_tem_sped(cnpj):
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Esta empresa está configurada para SPED Fiscal e não para XML.",
    )

def _obter_periodo_anterior(periodo_ano: int, periodo_mes: int | None) -> tuple[int, int | None]:
  if periodo_mes is None:
    return periodo_ano - 1, None
  if periodo_mes > 1:
    return periodo_ano, periodo_mes - 1
  return periodo_ano - 1, 12

def _agrupar_ranking_por_chave(itens: list[dict], chave: str, limite: int = 5) -> list[dict]:
  agrupado: dict[str, Decimal] = {}
  for item in itens:
    nome = str(item.get(chave) or "").strip() or f"{chave.title()} nÃ£o identificado"
    valor_total = Decimal(str(item.get("valor_total") or 0))
    agrupado[nome] = agrupado.get(nome, Decimal("0.00")) + valor_total

  return [
    {chave: nome, "valor_total": valor_total}
    for nome, valor_total in sorted(
      agrupado.items(),
      key=lambda entry: entry[1],
      reverse=True,
    )[:limite]
  ]

def _resumo_vendas_por_kpis(resultados: list, limite: int = 5) -> DashboardVendasResumo:
  total_vendido = Decimal("0.00")
  quantidade_notas = 0
  total_impostos = Decimal("0.00")
  top_clientes: list[dict] = []
  top_produtos: list[dict] = []
  top_cidades: list[dict] = []

  for item in resultados:
    kpis = item.kpis
    total_vendido += Decimal(str(kpis.total_vendas or 0))
    quantidade_notas += int(kpis.quantidade_notas or 0)
    total_impostos += (
      Decimal(str(kpis.total_icms or 0))
      + Decimal(str(kpis.total_ipi or 0))
      + Decimal(str(kpis.total_pis or 0))
      + Decimal(str(kpis.total_cofins or 0))
    )
    top_clientes.extend(kpis.top_clientes or [])
    top_produtos.extend(kpis.top_produtos or [])
    top_cidades.extend(kpis.top_cidades or [])

  ticket_medio = total_vendido / quantidade_notas if quantidade_notas else Decimal("0.00")

  return DashboardVendasResumo(
    total_vendido=total_vendido,
    quantidade_notas=quantidade_notas,
    total_impostos=total_impostos,
    ticket_medio=ticket_medio,
    top_clientes=_agrupar_ranking_por_chave(top_clientes, "cliente", limite),
    top_produtos=_agrupar_ranking_por_chave(top_produtos, "produto", limite),
    top_cidades=_agrupar_ranking_por_chave(top_cidades, "cidade", limite),
  )

# -------------------------
# Processamento
# -------------------------

"""Processa XMLs disponíveis em pasta (origem batch/legado)."""
@nfe_router.post("/processar", response_model=ProcessarNFeResponse)
def processar_nfe(request: ProcessarNFeRequest):
  return ProcessarNFeService().executar(request)

"""Recebe arquivos XML e persiste no staging de importação sem processar KPIs."""
@nfe_router.post("/xml/importar", response_model=ImportacaoXMLResponse)
async def importar_xml(
  arquivos: list[UploadFile] = File(...),
  cnpj_empresa_origem: str = Query(..., min_length=14, max_length=20),
):
  _validar_empresa_xml(cnpj_empresa_origem)
  
  if len(arquivos) > 10000:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="O limite máximo por importação é de 10000 XMLs.",
    )
    # `conteudos` mantém apenas nome + bytes dos arquivos válidos para o serviço de importação.

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

  try:
    resultados_service = XMLImportacaoService().importar_arquivos(
      conteudos,
      cnpj_empresa_origem=cnpj_empresa_origem,
    )
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=str(exc),
    ) from exc
    
  resultados = [ImportacaoXMLArquivoResultado(**resultado.__dict__) for resultado in resultados_service]

  return ImportacaoXMLResponse(
    status="ok",
    total_arquivos=len(resultados),
    importados=sum(1 for item in resultados if item.status == "importado"),
    duplicados=sum(1 for item in resultados if item.status == "duplicado"),
    erros=sum(1 for item in resultados if item.status == "erro"),
    resultados=resultados,
  )
    
"""Informa quantos XMLs já importados ainda não foram processados."""
@nfe_router.get("/xml/pendencias", response_model=ImportacaoXMLPendenciasResponse)
def consultar_pendencias_xml(cnpj_emitente: str = Query(..., min_length=14, max_length=20)):
  _validar_empresa_xml(cnpj_emitente)
  service_importacao = XMLImportacaoService()
  total_pendentes = service_importacao.contar_xmls_pendentes(cnpj_emitente)

  return ImportacaoXMLPendenciasResponse(
    status="ok",
    cnpj_emitente=cnpj_emitente,
    total_pendentes=total_pendentes,
    possui_pendentes=total_pendentes > 0,
  )
  
"""Executa processamento do staging e marca XMLs como processados em caso de sucesso."""  
@nfe_router.post("/xml/processar-importados", response_model=ProcessarNFeResponse)
def processar_xmls_importados(cnpj_emitente: str = Query(..., min_length=14, max_length=20)):
  _validar_empresa_xml(cnpj_emitente)
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

  # A marcação evita reprocessamento dos mesmos arquivos em chamadas futuras.
  if resposta.status == "processado":
    service_importacao.marcar_como_processados(ids_processados)

  return resposta

# -------------------------
# Consulta de KPIs (consolidado)
# -------------------------

"""Consulta KPIs consolidados por filtros de emitente/periodicidade e paginação."""
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
  
@nfe_router.get("/analise/compras", response_model=AnaliseComprasResponse)
def consultar_analise_compras_nfe(
  emitente_cnpj: str | None = Query(default=None),
  email: str | None = Query(default=None),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int | None = Query(default=None, ge=1),
  gerar_relatorio_ia: bool = Query(default=False),
  formato_relatorio: str = Query(default="executivo", pattern="^(executivo|analitico)$"),
  layout: str | None = Query(default=None),
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
    resultado = service.analisar_compras(
      emitente_cnpj=emitente_resolvido,
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

@nfe_router.get("/analise/vendas", response_model=AnaliseVendasResponse)
def consultar_analise_vendas_nfe(
  emitente_cnpj: str | None = Query(default=None),
  email: str | None = Query(default=None),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int | None = Query(default=None, ge=1),
  gerar_relatorio_ia: bool = Query(default=False),
  formato_relatorio: str = Query(default="executivo", pattern="^(executivo|analitico)$"),
  layout: str | None = Query(default=None),
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
    resultado = service.analisar_vendas(
      emitente_cnpj=emitente_resolvido,
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

@nfe_router.get("/analise/compras/dashboard", response_model=DashboardComprasResponse)
def consultar_dashboard_compras_nfe(
  emitente_cnpj: str | None = Query(default=None),
  email: str | None = Query(default=None),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int = Query(default=5, ge=1, le=20),
):
  service = NFeConsultaService()

  emitente_resolvido = service.resolver_emitente_cnpj(
    emitente_cnpj=emitente_cnpj,
    email=email,
  )

  if not emitente_resolvido:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Informe um emitente_cnpj vÃ¡lido ou um email cadastrado.",
    )

  anos_disponiveis = sorted(
    {
      item.periodo_ano
      for item in service.listar_kpis(emitente_cnpj=emitente_resolvido, limite=120)
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

  ano_anterior, mes_anterior = _obter_periodo_anterior(ano_referencia, periodo_mes)

  try:
    resumo_atual = service.analisar_compras(
      emitente_cnpj=emitente_resolvido,
      periodo_ano=ano_referencia,
      periodo_mes=periodo_mes,
      limite=limite,
    )
    resumo_anterior = service.analisar_compras(
      emitente_cnpj=emitente_resolvido,
      periodo_ano=ano_anterior,
      periodo_mes=mes_anterior,
      limite=limite,
    )
    serie_mensal = [
      SerieMensalComprasItem(
        periodo_ano=ano_referencia,
        periodo_mes=mes,
        total_comprado=service.analisar_compras(
          emitente_cnpj=emitente_resolvido,
          periodo_ano=ano_referencia,
          periodo_mes=mes,
          limite=limite,
        )["total_comprado"],
      )
      for mes in range(1, 13)
    ]
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=str(exc),
    ) from exc

  return DashboardComprasResponse(
    status="ok",
    emitente_cnpj=emitente_resolvido,
    periodo_ano=ano_referencia,
    periodo_mes=periodo_mes,
    anos_disponiveis=anos_disponiveis,
    resumo_atual=AnaliseComprasResponse(status="ok", **resumo_atual),
    resumo_anterior=AnaliseComprasResponse(status="ok", **resumo_anterior),
    serie_mensal=serie_mensal,
  )

@nfe_router.get("/analise/vendas/dashboard", response_model=DashboardVendasResponse)
def consultar_dashboard_vendas_nfe(
  emitente_cnpj: str | None = Query(default=None),
  email: str | None = Query(default=None),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int = Query(default=5, ge=1, le=20),
):
  service = NFeConsultaService()

  emitente_resolvido = service.resolver_emitente_cnpj(
    emitente_cnpj=emitente_cnpj,
    email=email,
  )

  if not emitente_resolvido:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Informe um emitente_cnpj vÃ¡lido ou um email cadastrado.",
    )

  resultados_anos = service.listar_kpis(emitente_cnpj=emitente_resolvido, limite=120)
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
    emitente_cnpj=emitente_resolvido,
    periodo_ano=ano_referencia,
    limite=120,
  )
  resultados_ano_anterior = service.listar_kpis(
    emitente_cnpj=emitente_resolvido,
    periodo_ano=ano_referencia - 1,
    limite=120,
  )

  if periodo_mes is not None:
    resultados_filtrados = [item for item in resultados_ano_atual if item.periodo_mes == periodo_mes]
    ano_anterior, mes_anterior = _obter_periodo_anterior(ano_referencia, periodo_mes)
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
    emitente_cnpj=emitente_resolvido,
    periodo_ano=ano_referencia,
    periodo_mes=periodo_mes,
    anos_disponiveis=anos_disponiveis,
    resumo_atual=_resumo_vendas_por_kpis(resultados_filtrados, limite),
    resumo_anterior=_resumo_vendas_por_kpis(resultados_anteriores, limite),
    serie_mensal=serie_mensal,
  )

@nfe_router.get("/analise/clientes", response_model=AnaliseClientesResponse)
def consultar_analise_clientes_nfe(
  emitente_cnpj: str | None = Query(default=None),
  email: str | None = Query(default=None),
  periodo_ano: int | None = Query(default=None),
  periodo_mes: int | None = Query(default=None),
  limite: int | None = Query(default=None, ge=1),
  gerar_relatorio_ia: bool = Query(default=False),
  formato_relatorio: str = Query(default="executivo", pattern="^(executivo|analitico)$"),
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
    resultado = service.analisar_clientes(
      emitente_cnpj=emitente_resolvido,
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
      detail=f"Falha ao gerar relatório com IA: {exc}",
    ) from exc

  return AnaliseClientesResponse(status="ok", **resultado)
  
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
