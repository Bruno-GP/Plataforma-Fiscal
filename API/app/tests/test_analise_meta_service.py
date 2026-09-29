from datetime import date
from decimal import Decimal

from app.services.metas.analise_meta_service import (
    PontoHistorico,
    StatusRitmo,
    Tendencia,
    analisar_meta,
    calcular_tendencia,
)


def _serie_mensal(valores: list[str], ano: int = 2026, mes_inicial: int = 1) -> list[PontoHistorico]:
    pontos = []
    ano_corrente, mes_corrente = ano, mes_inicial
    for valor in valores:
        pontos.append(PontoHistorico(periodo=date(ano_corrente, mes_corrente, 1), valor=Decimal(valor)))
        mes_corrente += 1
        if mes_corrente > 12:
            mes_corrente = 1
            ano_corrente += 1
    return pontos


def test_tendencia_crescimento_forte():
    serie = [p.valor for p in _serie_mensal(["10000", "11500", "13000", "14500", "16000", "17500"])]
    assert calcular_tendencia(serie) == Tendencia.CRESCIMENTO_FORTE


def test_tendencia_queda_forte():
    serie = [p.valor for p in _serie_mensal(["17500", "16000", "14500", "13000", "11500", "10000"])]
    assert calcular_tendencia(serie) == Tendencia.QUEDA_FORTE


def test_tendencia_estavel():
    serie = [p.valor for p in _serie_mensal(["10000", "10100", "9950", "10050", "9980", "10020"])]
    assert calcular_tendencia(serie) == Tendencia.ESTAVEL


def test_tendencia_serie_curta_nao_quebra():
    assert calcular_tendencia([Decimal("100")]) == Tendencia.ESTAVEL
    assert calcular_tendencia([]) == Tendencia.ESTAVEL


def test_analisar_meta_no_caminho_maior_melhor():
    serie_anterior = _serie_mensal(["30000", "31000", "32000", "33000", "34000", "35000"], mes_inicial=2)
    analise = analisar_meta(
        valor_alvo=Decimal("50000.00"),
        direcao_boa="maior_melhor",
        periodo_inicio=date(2026, 8, 1),
        periodo_fim=date(2026, 8, 31),
        data_referencia=date(2026, 8, 22),
        valor_realizado_atual=Decimal("36000.00"),
        serie_historica=serie_anterior,
    )
    assert analise.tendencia == Tendencia.CRESCIMENTO_FORTE
    assert analise.status_ritmo == StatusRitmo.NO_CAMINHO
    assert analise.projecao_fim_periodo > Decimal("50000.00")


def test_analisar_meta_fora_da_rota_maior_melhor():
    serie_anterior = _serie_mensal(["35000", "34000", "33000", "32000", "31000", "30000"], mes_inicial=2)
    analise = analisar_meta(
        valor_alvo=Decimal("50000.00"),
        direcao_boa="maior_melhor",
        periodo_inicio=date(2026, 8, 1),
        periodo_fim=date(2026, 8, 31),
        data_referencia=date(2026, 8, 22),
        valor_realizado_atual=Decimal("15000.00"),
        serie_historica=serie_anterior,
    )
    assert analise.tendencia == Tendencia.QUEDA_FORTE
    assert analise.status_ritmo == StatusRitmo.FORA_DA_ROTA
    assert "faltam" in analise.diagnostico.lower() or "nao sera" in analise.diagnostico.lower()


def test_analisar_meta_menor_melhor_inverte_ritmo():
    serie_anterior = _serie_mensal(["5000", "5100", "5200", "5300", "5400", "5500"], mes_inicial=2)
    analise = analisar_meta(
        valor_alvo=Decimal("4000.00"),
        direcao_boa="menor_melhor",
        periodo_inicio=date(2026, 8, 1),
        periodo_fim=date(2026, 8, 31),
        data_referencia=date(2026, 8, 22),
        valor_realizado_atual=Decimal("5600.00"),
        serie_historica=serie_anterior,
    )
    assert analise.status_ritmo == StatusRitmo.FORA_DA_ROTA


def test_analisar_meta_sazonalidade_com_doze_meses():
    serie_anterior = _serie_mensal(
        [
            "10000",
            "10200",
            "10400",
            "10600",
            "10800",
            "11000",
            "11200",
            "11400",
            "11600",
            "11800",
            "12000",
            "12200",
        ],
        ano=2025,
        mes_inicial=8,
    )
    analise = analisar_meta(
        valor_alvo=Decimal("15000.00"),
        direcao_boa="maior_melhor",
        periodo_inicio=date(2026, 8, 1),
        periodo_fim=date(2026, 8, 31),
        data_referencia=date(2026, 8, 15),
        valor_realizado_atual=Decimal("12500.00"),
        serie_historica=serie_anterior,
    )
    assert analise.comparativo_ano_anterior_pct is not None


def test_analisar_meta_sem_historico_suficiente_nao_quebra():
    analise = analisar_meta(
        valor_alvo=Decimal("10000.00"),
        direcao_boa="maior_melhor",
        periodo_inicio=date(2026, 8, 1),
        periodo_fim=date(2026, 8, 31),
        data_referencia=date(2026, 8, 5),
        valor_realizado_atual=Decimal("1000.00"),
        serie_historica=[],
    )
    assert analise.tendencia == Tendencia.ESTAVEL
    assert analise.comparativo_ano_anterior_pct is None
    assert analise.variacao_vs_media_pct is None
