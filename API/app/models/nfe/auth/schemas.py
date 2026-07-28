from pydantic import BaseModel, Field


class LoginCadastroRequest(BaseModel):
    empresa_nome: str = Field(..., min_length=2, description="Nome da empresa")
    email: str = Field(..., description="E-mail do usuario")
    senha: str = Field(..., min_length=12, description="Senha de acesso")
    cnpj: str = Field(..., description="CNPJ vinculado ao cadastro da empresa")
    tem_sped: bool = Field(default=False, description="Define se empresa usa SPED Fiscal")
    tem_conta_azul: bool = Field(default=False, description="Define se empresa usa Conta Azul")
    tem_xml: bool = Field(default=False, description="Define se empresa usa XML/NFe")
    estado: str | None = Field(default=None, description="UF da empresa para fallback de NFCe")
    cidade: str | None = Field(default=None, description="Cidade da empresa para fallback de NFCe")
    municipio_id: str | None = Field(default=None, description="Identificador do municipio no catalogo local")
    codigo_ibge: str | None = Field(default=None, description="Codigo IBGE do municipio no catalogo local")


class LoginCadastroResponse(BaseModel):
    status: str
    login_id: int
    empresa_id: int
    cnpj: str
    email: str
    empresa_nome: str
    tem_sped: bool
    tem_conta_azul: bool
    tem_xml: bool
    tem_xml_importado_valido: bool
    expires_in: int
    access_token: str


class LoginRequest(BaseModel):
    email: str = Field(..., description="E-mail do usuario")
    senha: str = Field(..., description="Senha de acesso")


class LoginResponse(BaseModel):
    status: str
    login_id: int
    empresa_id: int
    cnpj: str
    email: str
    empresa_nome: str
    tem_sped: bool
    tem_conta_azul: bool
    tem_xml: bool
    tem_xml_importado_valido: bool
    expires_in: int
    access_token: str


class SessaoResponse(BaseModel):
    status: str
    login_id: int
    empresa_id: int
    cnpj: str
    email: str
    empresa_nome: str
    tem_sped: bool
    tem_conta_azul: bool
    tem_xml: bool
    tem_xml_importado_valido: bool
    expires_in: int


class CompanyProfileResponse(BaseModel):
    status: str
    login_id: int
    empresa_id: int
    cnpj: str
    empresa_nome: str
    estado: str = ""
    cidade: str = ""
    municipio_id: str = ""
    codigo_ibge: str = ""


class UpdatePasswordRequest(BaseModel):
    nova_senha: str = Field(..., min_length=1, description="Nova senha do usuario logado")


class UpdatePasswordResponse(BaseModel):
    status: str
    message: str
