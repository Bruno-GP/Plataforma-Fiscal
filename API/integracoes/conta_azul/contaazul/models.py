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


class Produto(ContaAzulBaseModel):
    """GET /v1/produto/busca. Sem campo fiscal (NCM/CEST/origem) — a API real
    nao expoe isso. Sem GET /v1/produto/{id} tambem — so ha listagem por filtro."""

    id: str
    id_legado: Optional[int] = None
    nome: str
    codigo_sku: Optional[str] = None
    codigo_ean: Optional[str] = None
    tipo: Optional[str] = None
    status: Optional[str] = None
    estoque: Optional[float] = None
    valor_venda: Optional[float] = None
    custo_medio: Optional[float] = None
    filhos: Optional[list[dict]] = None


class Vendedor(ContaAzulBaseModel):
    """GET /v1/venda/vendedores. Resposta e array bruto, sem paginacao."""

    id: str
    nome: str
    id_legado: Optional[int] = None


class ItemVenda(ContaAzulBaseModel):
    """Item de GET /v1/venda/{id_venda}/itens."""

    id: Optional[str] = None
    id_item: Optional[str] = None
    nome: Optional[str] = None
    descricao: Optional[str] = None
    tipo: Optional[str] = None
    quantidade: Optional[float] = None
    valor: Optional[float] = None
    custo: Optional[float] = None


class TotaisItensVenda(ContaAzulBaseModel):
    """Campo `totais` de GET /v1/venda/{id_venda}/itens."""

    quantidade_produtos: Optional[int] = None
    quantidade_servicos: Optional[int] = None
    quantidade_nao_conciliados: Optional[int] = None
