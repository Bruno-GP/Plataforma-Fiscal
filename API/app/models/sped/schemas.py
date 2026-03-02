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