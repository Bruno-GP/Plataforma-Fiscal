from pydantic import BaseModel, Field, field_serializer
from typing import List, Optional, Dict
from datetime import date, datetime
from decimal import Decimal

# =========================
# REQUEST
# =========================

class ProcessarNFeRequest(BaseModel):
  empresa_id: Optional[str] = Field(
    None,
    description="Identificador interno da empresa (opcional; se não informado será identificado pelo CNPJ do XML)"
  )
  origem: str = Field(..., description="Origem dos XMLs")
  pasta_xml: str = Field(..., description="Pasta onde estão os XMLs")
  periodo: Optional[str] = Field(
    None,
    description="Período esperado (YYYY-MM). Apenas informativo"
  )

# =========================
# DOMÍNIO NFE
# =========================

class NFeItemTributo(BaseModel):
  tributo_codigo: str
  tributo_nome: str
  base_calculo: Decimal = Decimal("0.00")
  aliquota: Optional[Decimal] = None
  valor_debito: Decimal = Decimal("0.00")
  valor_credito: Decimal = Decimal("0.00")
  valor_tributo: Decimal = Decimal("0.00")
  natureza: Optional[str] = None
  origem: Optional[str] = None
  status: Optional[str] = None


class NFeItem(BaseModel):
  id: Optional[int] = None
  item_numero: int
  produto_codigo: str
  descricao: str
  ncm: str
  descricao_ncm: Optional[str] = None
  cfop: str

  quantidade: Decimal
  valor_unitario: Decimal
  valor_total: Decimal

  icms_cst_csosn: Optional[str] = None
  icms_base: Optional[Decimal] = None
  icms_aliquota: Optional[Decimal] = None
  icms_valor: Optional[Decimal] = None
  tributos: List[NFeItemTributo] = Field(default_factory=list)


class NFeNota(BaseModel):
  id: Optional[int] = None
  numero_nf: str
  emitente_cnpj: str
  modelo: str
  data_emissao: date
  natureza_operacao: str

  destinatario_documento: str
  destinatario_nome: str
  destinatario_cidade: str   # ✅ NOME ALINHADO COM KPI
  destinatario_uf: str

  valor_produtos: Decimal
  valor_desconto: Decimal
  valor_frete: Decimal

  valor_icms: Decimal
  valor_ipi: Decimal
  valor_pis: Decimal
  valor_cofins: Decimal

  valor_total_nf: Decimal

  itens: List[NFeItem]


# =========================
# KPIs
# =========================

class NFeKPI(BaseModel):
  id: int
  processamento_id: int
  emitente_cnpj: str | None = None
  total_vendas: Decimal = Decimal("0.00")
  quantidade_notas: int = 0
  ticket_medio: Decimal = Decimal("0.00")
  maior_nota: Decimal = Decimal("0.00")
  menor_nota: Decimal = Decimal("0.00")
  total_icms: Decimal = Decimal("0.00")
  total_ipi: Decimal = Decimal("0.00")
  total_pis: Decimal = Decimal("0.00")
  total_cofins: Decimal = Decimal("0.00")
  top_clientes: List[Dict] = Field(default_factory=list)
  top_produtos: List[Dict] = Field(default_factory=list)
  top_cidades: List[Dict] = Field(default_factory=list)

def _format_decimal_ptbr(value: Decimal) -> str:
  quantized = value.quantize(Decimal("0.01"))
  formatted = f"{quantized:,.2f}"
  return formatted.replace(",", "X").replace(".", ",").replace("X", ".")

def _format_moeda_ptbr(value: Decimal) -> str:
  return f"R$ {_format_decimal_ptbr(value)}"

class KPIsRelatorio(BaseModel):
  # Vendas
  total_vendas: Decimal = Decimal("0.00")
  quantidade_notas: int = 0
  ticket_medio: Decimal = Decimal("0.00")
  maior_nota: Decimal = Decimal("0.00")
  menor_nota: Decimal = Decimal("0.00")

  # Impostos
  total_icms: Decimal = Decimal("0.00")
  total_ipi: Decimal = Decimal("0.00")
  total_pis: Decimal = Decimal("0.00")
  total_cofins: Decimal = Decimal("0.00")

  # Rankings
  top_clientes: List[Dict] = Field(default_factory=list)
  top_produtos: List[Dict] = Field(default_factory=list)
  top_cidades: List[Dict] = Field(default_factory=list)
  
  @field_serializer(
    "total_vendas",
    "ticket_medio",
    "maior_nota",
    "menor_nota",
    "total_icms",
    "total_ipi",
    "total_pis",
    "total_cofins"
  )
  
  def _serializar_moeda(self, value: Decimal) -> str:
    return _format_moeda_ptbr(value)

  @field_serializer("top_clientes", "top_produtos", "top_cidades")
  def _serializar_top(self, value: List[Dict]) -> List[Dict]:
    resultado = []
    for item in value:
      if "valor_total" in item:
        item = {
          **item,
          "valor_total": _format_moeda_ptbr(Decimal(item["valor_total"]))
        }
      resultado.append(item)
    return resultado
  
class NFeKPIConsulta(BaseModel):
  periodo_ano: Optional[int] = None
  periodo_mes: Optional[int] = None
  emitente_cnpj: Optional[str] = None
  kpis: NFeKPI


class ConsultaKPIResponse(BaseModel):
  status: str
  total: int
  resultados: List[NFeKPIConsulta] = Field(default_factory=list)
  
class ConsultaCNPJResponse(BaseModel):
  status: str
  emitente_cnpj: str
  
# =========================
# KPIs Comparativo
# =========================

class KPIComparativoValor(BaseModel):
  atual: Decimal = Decimal("0.00")
  anterior: Decimal = Decimal("0.00")
  variacao_percentual: Optional[Decimal] = None

class KPIComparativoQuantidade(BaseModel):
  atual: int = 0
  anterior: int = 0
  variacao_percentual: Optional[Decimal] = None

class KPIsComparativo(BaseModel):
  total_vendas: KPIComparativoValor
  quantidade_notas: KPIComparativoQuantidade
  ticket_medio: KPIComparativoValor
  maior_nota: KPIComparativoValor
  menor_nota: KPIComparativoValor
  total_icms: KPIComparativoValor
  total_ipi: KPIComparativoValor
  total_pis: KPIComparativoValor
  total_cofins: KPIComparativoValor

class ComparativoKPIMensalResponse(BaseModel):
  status: str
  periodo_atual_ano: int
  periodo_atual_mes: int
  periodo_anterior_ano: int
  periodo_anterior_mes: int
  emitente_cnpj: Optional[str] = None
  kpis: KPIsComparativo

# =========================
# ERROS
# =========================

class ErroProcessamento(BaseModel):
  codigo: str
  mensagem: str
  detalhe: Optional[str] = None

# =========================
# RESPONSE
# =========================

class KPIPorPeriodo(BaseModel):
  ano: int
  mes: int
  kpis: KPIsRelatorio

class ProcessarNFeResponse(BaseModel):
  status: str
  cnpj_emitente: str

  # Período principal (0 se múltiplos)
  periodo_ano: int
  periodo_mes: int

  # Lista de períodos encontrados
  periodos_encontrados: List[Dict[str, int]] = Field(default_factory=list)

  notas_processadas: int
  itens_processados: int
  kpis: List[KPIPorPeriodo]
  erros: List[Dict] = Field(default_factory=list)
  data_processamento: Optional[str] = None

class ImportarCFOPResponse(BaseModel):
  status: str
  total_encontrado: int
  inseridos: int
  ignorados: int
  erros: List[Dict] = Field(default_factory=list)
  
# =========================
# INFRA
# =========================

class ConnSQLResponse(BaseModel):
  sucesso: bool
  detalhes: str
  servidor: Optional[str] = None
  
# =========================
# CONSULTA
# =========================

class ConsultaNFeResponse(BaseModel):
  status: str
  total: int
  notas: List[NFeNota] = Field(default_factory=list)
  
# =========================
# XML
# =========================  
  
class ImportacaoXMLArquivoResultado(BaseModel):
  arquivo: str
  cnpj_emitente: Optional[str] = None
  status: str
  mensagem: str


class ImportacaoXMLResponse(BaseModel):
  status: str
  total_arquivos: int
  importados: int
  duplicados: int
  erros: int
  resultados: List[ImportacaoXMLArquivoResultado] = Field(default_factory=list)
  
class ImportacaoXMLPendenciasResponse(BaseModel):
  status: str
  cnpj_emitente: str
  total_pendentes: int
  possui_pendentes: bool
  
class RankingFornecedorCompra(BaseModel):
  fornecedor: str
  valor_total: Decimal = Decimal("0.00")
  quantidade_documentos: int = 0


class RankingProdutoCompra(BaseModel):
  produto: str
  valor_total: Decimal = Decimal("0.00")
  quantidade_total: Decimal = Decimal("0.00")


class AnaliseComprasResponse(BaseModel):
  status: str
  emitente_cnpj: str
  periodo_ano: int | None = None
  periodo_mes: int | None = None
  total_comprado: Decimal = Decimal("0.00")
  total_impostos_complementares: Decimal = Decimal("0.00")
  total_tributos_reforma: Decimal = Decimal("0.00")
  top_fornecedores_valor: list[RankingFornecedorCompra] = Field(default_factory=list)
  top_fornecedores_quantidade: list[RankingFornecedorCompra] = Field(default_factory=list)
  top_produtos_valor: list[RankingProdutoCompra] = Field(default_factory=list)
  top_produtos_quantidade: list[RankingProdutoCompra] = Field(default_factory=list)
  relatorio_ia: str | None = None

class SerieMensalComprasItem(BaseModel):
  periodo_ano: int
  periodo_mes: int
  total_comprado: Decimal = Decimal("0.00")
  total_impostos_complementares: Decimal = Decimal("0.00")
  total_tributos_reforma: Decimal = Decimal("0.00")

class DashboardComprasResponse(BaseModel):
  status: str
  emitente_cnpj: str
  periodo_ano: int | None = None
  periodo_mes: int | None = None
  anos_disponiveis: list[int] = Field(default_factory=list)
  resumo_atual: AnaliseComprasResponse
  resumo_anterior: AnaliseComprasResponse
  serie_mensal: list[SerieMensalComprasItem] = Field(default_factory=list)
  
class RankingClienteVenda(BaseModel):
  cliente: str
  valor_total: Decimal = Decimal("0.00")
  quantidade_documentos: int = 0


class RankingProdutoVenda(BaseModel):
  produto: str
  valor_total: Decimal = Decimal("0.00")
  quantidade_total: Decimal = Decimal("0.00")


class RankingRegiaoVenda(BaseModel):
  regiao: str
  valor_total: Decimal = Decimal("0.00")
  quantidade_documentos: int = 0


class RankingCidadeVenda(BaseModel):
  cidade: str
  uf: str = ""
  valor_total: Decimal = Decimal("0.00")
  quantidade_documentos: int = 0


class RankingCfopVenda(BaseModel):
  cfop: str
  descricao: str
  valor_total: Decimal = Decimal("0.00")
  participacao_percentual: Decimal = Decimal("0.00")


class RankingNcmFiscal(BaseModel):
  ncm: str
  descricao: str
  valor_total: Decimal = Decimal("0.00")
  participacao_percentual: Decimal = Decimal("0.00")


class RankingCategoriaFiscal(BaseModel):
  categoria: str
  valor_total: Decimal = Decimal("0.00")
  participacao_percentual: Decimal = Decimal("0.00")
  quantidade_documentos: int = 0


class AnaliseFiscalCfopResponse(BaseModel):
  status: str
  emitente_cnpj: str
  periodo_ano: int | None = None
  periodo_mes: int | None = None
  total_movimentado: Decimal = Decimal("0.00")
  total_impostos_complementares: Decimal = Decimal("0.00")
  quantidade_documentos: int = 0
  quantidade_cfops: int = 0
  top_categorias: list[RankingCategoriaFiscal] = Field(default_factory=list)
  top_cfops: list[RankingCfopVenda] = Field(default_factory=list)


class AnaliseFiscalNcmResponse(BaseModel):
  status: str
  emitente_cnpj: str
  periodo_ano: int | None = None
  periodo_mes: int | None = None
  total_movimentado: Decimal = Decimal("0.00")
  total_impostos_complementares: Decimal = Decimal("0.00")
  quantidade_documentos: int = 0
  quantidade_ncms: int = 0
  top_ncms: list[RankingNcmFiscal] = Field(default_factory=list)


class FiscalHierarquiaEstadoItem(BaseModel):
  estado: str
  faturamento: Decimal = Decimal("0.00")
  imposto_valor: Decimal = Decimal("0.00")
  imposto_percentual: Decimal = Decimal("0.00")


class FiscalHierarquiaCidadeItem(BaseModel):
  cidade: str
  uf: str = ""
  faturamento: Decimal = Decimal("0.00")
  imposto_valor: Decimal = Decimal("0.00")
  imposto_percentual: Decimal = Decimal("0.00")


class FiscalHierarquiaNcmItem(BaseModel):
  ncm: str
  descricao: str
  quantidade_produtos: int = 0
  faturamento: Decimal = Decimal("0.00")
  imposto_valor: Decimal = Decimal("0.00")
  imposto_percentual: Decimal = Decimal("0.00")


class FiscalHierarquiaProdutoItem(BaseModel):
  produto_codigo: str
  produto: str
  faturamento: Decimal = Decimal("0.00")
  imposto_valor: Decimal = Decimal("0.00")
  imposto_percentual: Decimal = Decimal("0.00")


class AnaliseFiscalHierarquicaResponse(BaseModel):
  status: str
  emitente_cnpj: str
  periodo_ano: int | None = None
  periodo_mes: int | None = None
  nivel_atual: str = "estado"
  offset: int = 0
  limite: int = 0
  total_registros_nivel: int = 0
  possui_mais_registros: bool = False
  total_faturamento: Decimal = Decimal("0.00")
  total_impostos: Decimal = Decimal("0.00")
  percentual_impostos_sobre_faturamento: Decimal = Decimal("0.00")
  quantidade_documentos: int = 0
  total_estados: int = 0
  total_cidades: int = 0
  total_ncms: int = 0
  total_produtos: int = 0
  hierarquia: list[dict] = Field(default_factory=list)
  itens_nivel_atual: list[dict] = Field(default_factory=list)
  por_estado: list[FiscalHierarquiaEstadoItem] = Field(default_factory=list)
  por_cidade: list[FiscalHierarquiaCidadeItem] = Field(default_factory=list)
  por_ncm: list[FiscalHierarquiaNcmItem] = Field(default_factory=list)
  por_produto: list[FiscalHierarquiaProdutoItem] = Field(default_factory=list)


class AnaliseVendasResponse(BaseModel):
  status: str
  emitente_cnpj: str
  periodo_ano: int | None = None
  periodo_mes: int | None = None
  total_vendido: Decimal = Decimal("0.00")
  top_regioes_valor: list[RankingRegiaoVenda] = Field(default_factory=list)
  top_cidades_valor: list[RankingCidadeVenda] = Field(default_factory=list)
  top_clientes_valor: list[RankingClienteVenda] = Field(default_factory=list)
  top_clientes_quantidade: list[RankingClienteVenda] = Field(default_factory=list)
  top_produtos_valor: list[RankingProdutoVenda] = Field(default_factory=list)
  top_produtos_quantidade: list[RankingProdutoVenda] = Field(default_factory=list)
  top_cfops_valor: list[RankingCfopVenda] = Field(default_factory=list)
  relatorio_ia: str | None = None

class SerieMensalVendasItem(BaseModel):
  periodo_ano: int
  periodo_mes: int
  total_vendido: Decimal = Decimal("0.00")
  quantidade_notas: int = 0
  total_impostos: Decimal = Decimal("0.00")
  total_impostos_complementares: Decimal = Decimal("0.00")
  total_tributos_reforma: Decimal = Decimal("0.00")

class DashboardVendasResumo(BaseModel):
  total_vendido: Decimal = Decimal("0.00")
  quantidade_notas: int = 0
  total_impostos: Decimal = Decimal("0.00")
  total_impostos_complementares: Decimal = Decimal("0.00")
  total_tributos_reforma: Decimal = Decimal("0.00")
  ticket_medio: Decimal = Decimal("0.00")
  top_clientes: list[dict] = Field(default_factory=list)
  top_produtos: list[dict] = Field(default_factory=list)
  top_cidades: list[dict] = Field(default_factory=list)

class DashboardVendasResponse(BaseModel):
  status: str
  emitente_cnpj: str
  periodo_ano: int | None = None
  periodo_mes: int | None = None
  anos_disponiveis: list[int] = Field(default_factory=list)
  resumo_atual: DashboardVendasResumo
  resumo_anterior: DashboardVendasResumo
  serie_mensal: list[SerieMensalVendasItem] = Field(default_factory=list)
  
class RankingClienteAnalise(BaseModel):
  cliente: str
  valor_total: Decimal = Decimal("0.00")
  quantidade_documentos: int = 0
  ticket_medio: Decimal = Decimal("0.00")
  percentual_participacao: Decimal = Decimal("0.00")


class AnaliseClientesResponse(BaseModel):
  status: str
  emitente_cnpj: str
  periodo_ano: int | None = None
  periodo_mes: int | None = None
  total_vendido: Decimal = Decimal("0.00")
  total_clientes: int = 0
  top_clientes_valor: list[RankingClienteAnalise] = Field(default_factory=list)
  top_clientes_quantidade: list[RankingClienteAnalise] = Field(default_factory=list)
  relatorio_ia: str | None = None


class IBPTSyncRequest(BaseModel):
  uf: str = Field(default="SC", min_length=2, max_length=2)
  todas_ufs: bool = False
  ncm: str | None = Field(default=None, min_length=2, max_length=20)


class IBPTSyncUFResultado(BaseModel):
  uf: str
  registros_recebidos: int = 0
  catalogo_sincronizado: int = 0
  tributacao_sincronizada: int = 0


class IBPTSyncResponse(BaseModel):
  status: str
  executado_por: str
  total_ufs: int
  resultados: list[IBPTSyncUFResultado] = Field(default_factory=list)


class NCMTributacaoResponse(BaseModel):
  status: str
  ncm_codigo: str
  descricao: str | None = None
  uf: str
  nacional_federal: Decimal = Decimal("0.00")
  importados_federal: Decimal = Decimal("0.00")
  estadual: Decimal = Decimal("0.00")
  municipal: Decimal = Decimal("0.00")
  vigencia_inicio: date | None = None
  vigencia_fim: date | None = None
  versao: str | None = None
  fonte: str | None = None
  atualizado_em: datetime | None = None
