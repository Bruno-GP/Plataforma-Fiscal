from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
import statistics


class Tendencia(StrEnum):
    CRESCIMENTO_FORTE = "crescimento_forte"
    CRESCIMENTO_LEVE = "crescimento_leve"
    ESTAVEL = "estavel"
    QUEDA_LEVE = "queda_leve"
    QUEDA_FORTE = "queda_forte"


class StatusRitmo(StrEnum):
    NO_CAMINHO = "no_caminho"
    EM_RISCO = "em_risco"
    FORA_DA_ROTA = "fora_da_rota"


MAIOR_MELHOR = "maior_melhor"
MENOR_MELHOR = "menor_melhor"

_LIMIAR_TENDENCIA_FORTE = Decimal("10")
_LIMIAR_TENDENCIA_LEVE = Decimal("3")
_Q2 = Decimal("0.01")


@dataclass(frozen=True)
class PontoHistorico:
    periodo: date
    valor: Decimal


@dataclass(frozen=True)
class AnaliseMeta:
    valor_alvo: Decimal
    valor_realizado_atual: Decimal
    percentual_atingido: Decimal
    tempo_decorrido_pct: Decimal
    status_ritmo: StatusRitmo
    tendencia: Tendencia
    media_periodos_anteriores: Decimal
    mediana_periodos_anteriores: Decimal
    desvio_padrao_periodos_anteriores: Decimal
    variacao_vs_media_pct: Decimal | None
    projecao_fim_periodo: Decimal
    diagnostico: str
    serie_historica: list[PontoHistorico]
    comparativo_ano_anterior_pct: Decimal | None = None


def _q(valor: Decimal | float | int) -> Decimal:
    return Decimal(str(valor)).quantize(_Q2)


def calcular_estatisticas(serie: list[Decimal]) -> tuple[Decimal, Decimal, Decimal]:
    if not serie:
        return Decimal("0.00"), Decimal("0.00"), Decimal("0.00")

    media = _q(statistics.mean(serie))
    mediana = _q(statistics.median(serie))
    desvio = _q(statistics.pstdev(serie) if len(serie) > 1 else Decimal("0"))
    return media, mediana, desvio


def calcular_tendencia(serie: list[Decimal]) -> Tendencia:
    if len(serie) < 2:
        return Tendencia.ESTAVEL

    inicio = serie[0]
    fim = serie[-1]
    if inicio == 0:
        return Tendencia.ESTAVEL

    variacao_pct = ((fim - inicio) / inicio * 100).quantize(_Q2)

    if variacao_pct >= _LIMIAR_TENDENCIA_FORTE:
        return Tendencia.CRESCIMENTO_FORTE
    if variacao_pct >= _LIMIAR_TENDENCIA_LEVE:
        return Tendencia.CRESCIMENTO_LEVE
    if variacao_pct <= -_LIMIAR_TENDENCIA_FORTE:
        return Tendencia.QUEDA_FORTE
    if variacao_pct <= -_LIMIAR_TENDENCIA_LEVE:
        return Tendencia.QUEDA_LEVE
    return Tendencia.ESTAVEL


def calcular_tempo_decorrido_pct(periodo_inicio: date, periodo_fim: date, data_referencia: date) -> Decimal:
    dias_totais = (periodo_fim - periodo_inicio).days + 1
    if dias_totais <= 0:
        return Decimal("100.00")

    dias_decorridos = (min(data_referencia, periodo_fim) - periodo_inicio).days + 1
    dias_decorridos = max(0, dias_decorridos)
    return min(Decimal(dias_decorridos) / Decimal(dias_totais) * 100, Decimal("100.00")).quantize(_Q2)


def calcular_projecao(valor_realizado_atual: Decimal, tempo_decorrido_pct: Decimal) -> Decimal:
    if tempo_decorrido_pct <= 0:
        return _q(valor_realizado_atual)
    return _q(valor_realizado_atual / (tempo_decorrido_pct / 100))


def classificar_ritmo(projecao: Decimal, valor_alvo: Decimal, direcao_boa: str) -> StatusRitmo:
    if valor_alvo <= 0:
        return StatusRitmo.EM_RISCO

    ratio_pct = _q(projecao / valor_alvo * 100)

    if direcao_boa == MENOR_MELHOR:
        if ratio_pct <= Decimal("105"):
            return StatusRitmo.NO_CAMINHO
        if ratio_pct <= Decimal("120"):
            return StatusRitmo.EM_RISCO
        return StatusRitmo.FORA_DA_ROTA

    if ratio_pct >= Decimal("95"):
        return StatusRitmo.NO_CAMINHO
    if ratio_pct >= Decimal("80"):
        return StatusRitmo.EM_RISCO
    return StatusRitmo.FORA_DA_ROTA


def comparar_sazonalidade(
    serie_historica: list[PontoHistorico],
    valor_atual: Decimal,
    mes_referencia: int,
    ano_referencia: int,
) -> Decimal | None:
    if len(serie_historica) < 12:
        return None

    ponto_ano_anterior = next(
        (p for p in serie_historica if p.periodo.year == ano_referencia - 1 and p.periodo.month == mes_referencia),
        None,
    )
    if ponto_ano_anterior is None or ponto_ano_anterior.valor == 0:
        return None

    return _q((valor_atual - ponto_ano_anterior.valor) / ponto_ano_anterior.valor * 100)


def gerar_diagnostico(
    *,
    tendencia: Tendencia,
    status_ritmo: StatusRitmo,
    direcao_boa: str,
    variacao_vs_media_pct: Decimal | None,
    valor_alvo: Decimal,
    valor_realizado_atual: Decimal,
) -> str:
    diferenca = valor_alvo - valor_realizado_atual if direcao_boa == MAIOR_MELHOR else valor_realizado_atual - valor_alvo
    diferenca = abs(_q(diferenca))

    if variacao_vs_media_pct is None:
        base = "Ainda nao ha historico suficiente para comparar com a media dos periodos anteriores."
    elif variacao_vs_media_pct >= 0:
        base = f"Voce esta {abs(_q(variacao_vs_media_pct))}% acima da media dos periodos anteriores."
    else:
        base = f"Voce esta {abs(_q(variacao_vs_media_pct))}% abaixo da media dos periodos anteriores."

    if status_ritmo == StatusRitmo.NO_CAMINHO:
        conclusao = "No ritmo atual, a meta deve ser batida ate o fim do periodo."
    elif status_ritmo == StatusRitmo.EM_RISCO:
        conclusao = f"No ritmo atual, a meta esta em risco - faltam {diferenca} para chegar ao alvo."
    else:
        tendencia_texto = "caindo" if tendencia in (Tendencia.QUEDA_LEVE, Tendencia.QUEDA_FORTE) else "sem crescer o suficiente"
        conclusao = f"O indicador esta {tendencia_texto}. Nesse ritmo, a meta nao sera atingida - faltam {diferenca} para chegar ao alvo."

    return f"{base} {conclusao}"


def analisar_meta(
    *,
    valor_alvo: Decimal,
    direcao_boa: str,
    periodo_inicio: date,
    periodo_fim: date,
    data_referencia: date,
    valor_realizado_atual: Decimal,
    serie_historica: list[PontoHistorico],
    n_periodos_referencia: int = 6,
) -> AnaliseMeta:
    periodos_base = serie_historica[-n_periodos_referencia:] if serie_historica else []
    valores_base = [p.valor for p in periodos_base]

    media, mediana, desvio = calcular_estatisticas(valores_base)
    tendencia = calcular_tendencia(valores_base)

    variacao_vs_media_pct: Decimal | None = None
    if media != 0:
        variacao_vs_media_pct = _q((valor_realizado_atual - media) / media * 100)

    tempo_decorrido_pct = calcular_tempo_decorrido_pct(periodo_inicio, periodo_fim, data_referencia)
    projecao = calcular_projecao(valor_realizado_atual, tempo_decorrido_pct)
    status_ritmo = classificar_ritmo(projecao, valor_alvo, direcao_boa)

    percentual_atingido = Decimal("0.00")
    if valor_alvo != 0:
        percentual_atingido = _q(valor_realizado_atual / valor_alvo * 100)

    comparativo_ano_anterior_pct = comparar_sazonalidade(
        serie_historica,
        valor_realizado_atual,
        periodo_inicio.month,
        periodo_inicio.year,
    )

    diagnostico = gerar_diagnostico(
        tendencia=tendencia,
        status_ritmo=status_ritmo,
        direcao_boa=direcao_boa,
        variacao_vs_media_pct=variacao_vs_media_pct,
        valor_alvo=valor_alvo,
        valor_realizado_atual=valor_realizado_atual,
    )

    return AnaliseMeta(
        valor_alvo=_q(valor_alvo),
        valor_realizado_atual=_q(valor_realizado_atual),
        percentual_atingido=percentual_atingido,
        tempo_decorrido_pct=tempo_decorrido_pct,
        status_ritmo=status_ritmo,
        tendencia=tendencia,
        media_periodos_anteriores=media,
        mediana_periodos_anteriores=mediana,
        desvio_padrao_periodos_anteriores=desvio,
        variacao_vs_media_pct=variacao_vs_media_pct,
        projecao_fim_periodo=projecao,
        diagnostico=diagnostico,
        serie_historica=serie_historica,
        comparativo_ano_anterior_pct=comparativo_ano_anterior_pct,
    )
