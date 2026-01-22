from pydantic import BaseModel, Field


class LoginCadastroRequest(BaseModel):
    email: str = Field(..., description="E-mail do usuário")
    senha: str = Field(..., min_length=8, description="Senha de acesso")
    cnpj: str = Field(..., description="CNPJ vinculado ao cadastro da empresa")


class LoginCadastroResponse(BaseModel):
    status: str
    login_id: int
    empresa_id: int
    cnpj: str
    email: str


class LoginRequest(BaseModel):
    email: str = Field(..., description="E-mail do usuário")
    senha: str = Field(..., description="Senha de acesso")


class LoginResponse(BaseModel):
    status: str
    login_id: int
    empresa_id: int
    cnpj: str
    email: str