from pydantic import BaseModel, Field

class LoginCadastroRequest(BaseModel):
    empresa_nome: str = Field(..., min_length=2, description="Nome da empresa")
    email: str = Field(..., description="E-mail do usuário")
    senha: str = Field(..., min_length=8, description="Senha de acesso")
    cnpj: str = Field(..., description="CNPJ vinculado ao cadastro da empresa")

class LoginCadastroResponse(BaseModel):
    status: str
    login_id: int
    empresa_id: int
    cnpj: str
    email: str
    empresa_nome: str

class LoginRequest(BaseModel):
    email: str = Field(..., description="E-mail do usuário")
    senha: str = Field(..., description="Senha de acesso")

class LoginResponse(BaseModel):
    status: str
    login_id: int
    empresa_id: int
    cnpj: str
    email: str
    empresa_nome: str