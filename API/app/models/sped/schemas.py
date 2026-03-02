from pydantic import BaseModel, Field

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