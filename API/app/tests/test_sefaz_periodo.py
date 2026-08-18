from datetime import date

from app.domain.sefaz.periodo import intervalo_do_ano


def test_intervalo_do_ano_retorna_primeiro_e_ultimo_dia():
    inicio, fim = intervalo_do_ano(2026)

    assert inicio == date(2026, 1, 1)
    assert fim == date(2026, 12, 31)


def test_intervalo_do_ano_bissexto():
    inicio, fim = intervalo_do_ano(2028)

    assert inicio == date(2028, 1, 1)
    assert fim == date(2028, 12, 31)
