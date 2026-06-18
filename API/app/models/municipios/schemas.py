from pydantic import BaseModel, Field


class UFCatalogoItem(BaseModel):
    uf: str = Field(..., description="Sigla da UF")
    label: str = Field(..., description="Rotulo exibido no autocomplete")
    quantidade_municipios: int = Field(default=0, description="Quantidade de municipios cadastrados na UF")


class MunicipioCatalogoItem(BaseModel):
    municipio_id: str = Field(..., description="Identificador do municipio no catalogo")
    codigo_ibge: str = Field(..., description="Codigo IBGE do municipio")
    nome: str = Field(..., description="Nome do municipio")
    uf: str = Field(..., description="Sigla da UF")
