from pydantic import BaseModel


class CnpjEnriquecimentoResponse(BaseModel):
    status: str
    cnpj: str
    razao_social: str | None = None
    cnae_fiscal: str | None = None
    cnae_fiscal_descricao: str | None = None
    estado: str | None = None
    cidade: str | None = None
    municipio_id: str | None = None
    codigo_ibge: str | None = None
