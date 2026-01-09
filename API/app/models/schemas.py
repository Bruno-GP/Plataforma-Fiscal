from pydantic import BaseModel, Field, field_serializer
from typing import List, Optional, Dict
from datetime import date
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

class NFeItem(BaseModel):
  item_numero: int
  produto_codigo: str
  descricao: str
  ncm: str
  cfop: str

  quantidade: Decimal
  valor_unitario: Decimal
  valor_total: Decimal

  icms_cst_csosn: Optional[str] = None
  icms_base: Optional[Decimal] = None
  icms_aliquota: Optional[Decimal] = None
  icms_valor: Optional[Decimal] = None


class NFeNota(BaseModel):
  numero_nf: str
  emitente_cnpj: str
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
  kpis: NFeKPI


class ConsultaKPIResponse(BaseModel):
  status: str
  total: int
  resultados: List[NFeKPIConsulta] = Field(default_factory=list)

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
  kpis: KPIsRelatorio
  erros: List[Dict] = Field(default_factory=list)
  data_processamento: Optional[str] = None
  
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
