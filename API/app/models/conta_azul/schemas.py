from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List

from pydantic import BaseModel


class ContaAzulKpiMensal(BaseModel):
  mes: date
  total_pedidos: int
  clientes_ativos: int
  receita_total: Decimal
  ticket_medio: Decimal


class ConsultaContaAzulKpisResponse(BaseModel):
  status: str
  resultados: List[ContaAzulKpiMensal] = []
