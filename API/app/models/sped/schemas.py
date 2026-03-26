from pydantic import BaseModel, Field
from decimal import Decimal

class ProcessarSpedFiscalRequest(BaseModel):
  arquivo_sped: str = Field(..., description="Caminho do arquivo .txt do SPED Fiscal")

class RegistroSpedResumo(BaseModel):
  registro: str
  quantidade: int

class ProcessarSpedFiscalResponse(BaseModel):
  status: str
  arquivo_sped: str
  total_linhas: int
  total_registros_identificados: int
  resumo_registros: list[RegistroSpedResumo]
  banco_sped: str
  
class ImportacaoSpedArquivoResultado(BaseModel):
  arquivo: str
  cnpj_emitente: str | None
  status: str
  mensagem: str

class ImportacaoSpedResponse(BaseModel):
  status: str
  total_arquivos: int
  importados: int
  duplicados: int
  erros: int
  resultados: list[ImportacaoSpedArquivoResultado]

class ImportacaoSpedPendenciasResponse(BaseModel):
  status: str
  cnpj_emitente: str
  total_pendentes: int
  possui_pendentes: bool

class ProcessarSpedImportadosResponse(BaseModel):
  status: str
  cnpj_emitente: str
  total_linhas: int
  total_registros_identificados: int
  total_arquivos_processados: int
  resumo_registros: list[RegistroSpedResumo]
  banco_sped: str
  
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
  top_fornecedores_valor: list[RankingFornecedorCompra] = Field(default_factory=list)
  top_fornecedores_quantidade: list[RankingFornecedorCompra] = Field(default_factory=list)
  top_produtos_valor: list[RankingProdutoCompra] = Field(default_factory=list)
  top_produtos_quantidade: list[RankingProdutoCompra] = Field(default_factory=list)
  relatorio_ia: str | None = None

class SerieMensalComprasItem(BaseModel):
  periodo_ano: int
  periodo_mes: int
  total_comprado: Decimal = Decimal("0.00")

class DashboardComprasResponse(BaseModel):
  status: str
  emitente_cnpj: str
  periodo_ano: int | None = None
  periodo_mes: int | None = None
  anos_disponiveis: list[int] = Field(default_factory=list)
  resumo_atual: AnaliseComprasResponse
  resumo_anterior: AnaliseComprasResponse
  serie_mensal: list[SerieMensalComprasItem] = Field(default_factory=list)
  
class RankingClienteSped(BaseModel):
  cliente: str
  valor_total: Decimal = Decimal("0.00")
  percentual: Decimal = Decimal("0.00")

class ConsultaClientesSpedResponse(BaseModel):
  status: str
  emitente_cnpj: str
  periodo_ano: int | None = None
  periodo_mes: int | None = None
  total_clientes: int = 0
  total_vendas: Decimal = Decimal("0.00")
  ticket_medio: Decimal = Decimal("0.00")
  resultados: list[RankingClienteSped] = Field(default_factory=list)
  
class RankingClienteVenda(BaseModel):
  cliente: str
  valor_total: Decimal = Decimal("0.00")
  quantidade_documentos: int = 0

class RankingProdutoVenda(BaseModel):
  produto: str
  valor_total: Decimal = Decimal("0.00")
  quantidade_total: Decimal = Decimal("0.00")

class AnaliseVendasResponse(BaseModel):
  status: str
  emitente_cnpj: str
  periodo_ano: int | None = None
  periodo_mes: int | None = None
  total_vendido: Decimal = Decimal("0.00")
  top_clientes_valor: list[RankingClienteVenda] = Field(default_factory=list)
  top_clientes_quantidade: list[RankingClienteVenda] = Field(default_factory=list)
  top_produtos_valor: list[RankingProdutoVenda] = Field(default_factory=list)
  top_produtos_quantidade: list[RankingProdutoVenda] = Field(default_factory=list)
  relatorio_ia: str | None = None

class SerieMensalVendasItem(BaseModel):
  periodo_ano: int
  periodo_mes: int
  total_vendido: Decimal = Decimal("0.00")
  quantidade_notas: int = 0
  total_impostos: Decimal = Decimal("0.00")

class DashboardVendasResumo(BaseModel):
  total_vendido: Decimal = Decimal("0.00")
  quantidade_notas: int = 0
  total_impostos: Decimal = Decimal("0.00")
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
