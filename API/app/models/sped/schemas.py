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
