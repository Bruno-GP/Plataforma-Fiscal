from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class TributoResponse(BaseModel):
  id: int
  codigo: str
  nome: str
  esfera: str
  tipo: str
  descricao: str | None = None
  ativo: bool = True


class ConsultaTributosResponse(BaseModel):
  status: str
  total: int = 0
  resultados: list[TributoResponse] = Field(default_factory=list)


class ApuracaoTributariaItem(BaseModel):
  id: int
  empresa_cnpj: str
  periodo_ano: int
  periodo_mes: int
  tributo_codigo: str
  tributo_nome: str
  total_debitos: Decimal = Decimal("0.00")
  total_creditos: Decimal = Decimal("0.00")
  ajustes_debito: Decimal = Decimal("0.00")
  ajustes_credito: Decimal = Decimal("0.00")
  estornos_debito: Decimal = Decimal("0.00")
  estornos_credito: Decimal = Decimal("0.00")
  compensacoes: Decimal = Decimal("0.00")
  saldo_apurado: Decimal = Decimal("0.00")
  saldo_periodo_anterior: Decimal = Decimal("0.00")
  saldo_a_recolher: Decimal = Decimal("0.00")
  status: str
  data_fechamento: datetime | None = None


class ConsultaApuracaoTributariaResponse(BaseModel):
  status: str
  emitente_cnpj: str
  periodo_ano: int | None = None
  periodo_mes: int | None = None
  total: int = 0
  resultados: list[ApuracaoTributariaItem] = Field(default_factory=list)


class DocumentoFiscalTributoItem(BaseModel):
  id: int
  nota_id: int | None = None
  sped_documento_id: int | None = None
  tributo_codigo: str
  tributo_nome: str
  empresa_cnpj: str
  periodo_ano: int | None = None
  periodo_mes: int | None = None
  modelo_documento: str | None = None
  chave_acesso: str | None = None
  tipo_operacao: str | None = None
  data_emissao: date | None = None
  base_calculo: Decimal = Decimal("0.00")
  valor_debito: Decimal = Decimal("0.00")
  valor_credito: Decimal = Decimal("0.00")
  valor_tributo: Decimal = Decimal("0.00")
  valor_isento: Decimal = Decimal("0.00")
  valor_outros: Decimal = Decimal("0.00")
  valor_reducao_base: Decimal = Decimal("0.00")
  valor_diferido: Decimal = Decimal("0.00")
  natureza: str
  origem: str
  status: str


class ConsultaDocumentoFiscalTributosResponse(BaseModel):
  status: str
  origem_documento: str
  documento_id: int
  total: int = 0
  resultados: list[DocumentoFiscalTributoItem] = Field(default_factory=list)


class ItemDocumentoFiscalTributoItem(BaseModel):
  id: int
  documento_tributo_id: int | None = None
  nota_item_id: int | None = None
  sped_item_id: int | None = None
  tributo_codigo: str
  tributo_nome: str
  empresa_cnpj: str
  periodo_ano: int | None = None
  periodo_mes: int | None = None
  numero_item: int | None = None
  produto_codigo: str | None = None
  ncm_codigo: str | None = None
  cfop: str | None = None
  cst_codigo: str | None = None
  classificacao_tributaria: str | None = None
  base_calculo: Decimal = Decimal("0.00")
  aliquota: Decimal | None = None
  aliquota_federal: Decimal | None = None
  aliquota_estadual: Decimal | None = None
  aliquota_municipal: Decimal | None = None
  percentual_reducao_base: Decimal | None = None
  percentual_diferimento: Decimal | None = None
  valor_debito: Decimal = Decimal("0.00")
  valor_credito: Decimal = Decimal("0.00")
  valor_tributo: Decimal = Decimal("0.00")
  valor_isento: Decimal = Decimal("0.00")
  valor_outros: Decimal = Decimal("0.00")
  valor_reducao_base: Decimal = Decimal("0.00")
  valor_diferido: Decimal = Decimal("0.00")
  valor_credito_presumido: Decimal = Decimal("0.00")
  natureza: str
  origem: str
  status: str


class ConsultaItemDocumentoFiscalTributosResponse(BaseModel):
  status: str
  origem_item: str
  item_id: int
  total: int = 0
  resultados: list[ItemDocumentoFiscalTributoItem] = Field(default_factory=list)


class MemoriaCalculoTributariaItem(BaseModel):
  id: int
  documento_tributo_id: int | None = None
  item_tributo_id: int | None = None
  credito_tributario_id: int | None = None
  debito_tributario_id: int | None = None
  tributo_codigo: str
  tributo_nome: str
  empresa_cnpj: str
  periodo_ano: int | None = None
  periodo_mes: int | None = None
  etapa_calculo: str
  base_origem: Decimal | None = None
  base_calculo: Decimal | None = None
  aliquota_aplicada: Decimal | None = None
  percentual_reducao_base: Decimal | None = None
  percentual_diferimento: Decimal | None = None
  valor_calculado: Decimal | None = None
  formula_calculo: str | None = None
  parametros_calculo: dict = Field(default_factory=dict)
  resultado_calculo: dict = Field(default_factory=dict)
  fonte_dados: str
  hash_calculo: str | None = None
  criado_em: datetime


class ConsultaMemoriaCalculoTributariaResponse(BaseModel):
  status: str
  emitente_cnpj: str
  periodo_ano: int | None = None
  periodo_mes: int | None = None
  total: int = 0
  limite: int
  offset: int
  resultados: list[MemoriaCalculoTributariaItem] = Field(default_factory=list)
