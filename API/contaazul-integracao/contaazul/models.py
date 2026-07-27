"""Schemas normalizados usados para exportar dados da Conta Azul.

Campos confirmados contra o OpenAPI real de cada area (ver aviso em
contaazul/client.py). Todo modelo usa `extra="allow"` e guarda o payload
original em `raw`, entao nenhum dado é perdido mesmo que um campo aqui nao
esteja mapeado explicitamente.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ContaAzulBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    raw: dict = Field(default_factory=dict, repr=False, description="Payload original retornado pela API")


class Cliente(ContaAzulBaseModel):
    id: str
    nome: str
    documento: Optional[str] = None
    tipo_pessoa: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None


class Categoria(ContaAzulBaseModel):
    id: str
    nome: str
    tipo: Optional[str] = None


class CentroCusto(ContaAzulBaseModel):
    id: str
    nome: str
    codigo: Optional[str] = None
    ativo: Optional[bool] = None


class ItemFiscal(ContaAzulBaseModel):
    """Item de linha de uma venda. Vem de um endpoint separado
    (GET /v1/venda/{id_venda}/itens), nao do resultado de busca de vendas."""

    id: Optional[str] = None
    descricao: Optional[str] = None
    quantidade: Optional[float] = None
    valor: Optional[float] = None
    custo: Optional[float] = None


class Venda(ContaAzulBaseModel):
    id: str
    numero: Optional[int] = None
    data: Optional[date] = None
    tipo: Optional[str] = None
    origem: Optional[str] = None
    total: Optional[float] = None
    situacao: Optional[dict] = None
    cliente: Optional[dict] = None


class VendaDetalhada(ContaAzulBaseModel):
    """Resposta de GET /v1/venda/{id} (getVendaById) — venda completa, com
    dados que a busca por filtro (/v1/venda/busca) nao traz."""

    cliente: Optional[dict] = None
    evento_financeiro: Optional[dict] = None
    notificacao: Optional[dict] = None
    natureza_operacao: Optional[dict] = None
    venda: Optional[dict] = None
    vendedor: Optional[dict] = None
    contrato: Optional[dict] = None


class ContaReceber(ContaAzulBaseModel):
    id: str
    descricao: Optional[str] = None
    data_vencimento: Optional[date] = None
    status: Optional[str] = None
    total: Optional[float] = None
    pago: Optional[float] = None
    nao_pago: Optional[float] = None
    cliente: Optional[dict] = None
    categorias: Optional[list] = None
    centros_custo: Optional[list] = None


class ContaPagar(ContaAzulBaseModel):
    id: str
    descricao: Optional[str] = None
    data_vencimento: Optional[date] = None
    status: Optional[str] = None
    total: Optional[float] = None
    pago: Optional[float] = None
    nao_pago: Optional[float] = None
    fornecedor: Optional[dict] = None
    categorias: Optional[list] = None
    centros_custo: Optional[list] = None
