from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.metas.schemas import MetaCreateRequest, PeriodoTipo, TipoMeta


def test_meta_create_request_aceita_payload_valido():
    meta = MetaCreateRequest(
        indicador_id=1,
        titulo="Crescer faturamento",
        valor_alvo=Decimal("50000.00"),
        tipo_meta=TipoMeta.CRESCIMENTO,
        periodo_tipo=PeriodoTipo.MENSAL,
        periodo_inicio=date(2026, 8, 1),
        periodo_fim=date(2026, 8, 31),
    )
    assert meta.valor_alvo == Decimal("50000.00")


def test_meta_create_request_rejeita_periodo_fim_antes_do_inicio():
    with pytest.raises(ValidationError):
        MetaCreateRequest(
            indicador_id=1,
            titulo="Meta invalida",
            valor_alvo=Decimal("1000.00"),
            tipo_meta=TipoMeta.CRESCIMENTO,
            periodo_tipo=PeriodoTipo.MENSAL,
            periodo_inicio=date(2026, 8, 31),
            periodo_fim=date(2026, 8, 1),
        )


def test_meta_create_request_rejeita_valor_alvo_zero():
    with pytest.raises(ValidationError):
        MetaCreateRequest(
            indicador_id=1,
            titulo="Meta invalida",
            valor_alvo=Decimal("0"),
            tipo_meta=TipoMeta.CRESCIMENTO,
            periodo_tipo=PeriodoTipo.MENSAL,
            periodo_inicio=date(2026, 8, 1),
            periodo_fim=date(2026, 8, 31),
        )
