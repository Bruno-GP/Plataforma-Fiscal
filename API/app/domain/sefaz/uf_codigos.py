from __future__ import annotations

CODIGO_IBGE_POR_UF = {
    "RO": "11",
    "AC": "12",
    "AM": "13",
    "RR": "14",
    "PA": "15",
    "AP": "16",
    "TO": "17",
    "MA": "21",
    "PI": "22",
    "CE": "23",
    "RN": "24",
    "PB": "25",
    "PE": "26",
    "AL": "27",
    "SE": "28",
    "BA": "29",
    "MG": "31",
    "ES": "32",
    "RJ": "33",
    "SP": "35",
    "PR": "41",
    "SC": "42",
    "RS": "43",
    "MS": "50",
    "MT": "51",
    "GO": "52",
    "DF": "53",
}


class UfInvalidaError(ValueError):
    pass


def codigo_ibge_uf(sigla_uf: str) -> str:
    """cUFAutor do distDFeInt exige o codigo IBGE da UF do autor da consulta --
    a SEFAZ rejeita (cStat=215, falha no esquema xml) qualquer valor fora da
    lista de UFs reais (ex.: "91", codigo generico de Ambiente Nacional usado
    em outros webservices de NFe, nao e aceito aqui).
    """
    codigo = CODIGO_IBGE_POR_UF.get((sigla_uf or "").strip().upper())
    if codigo is None:
        raise UfInvalidaError(f"UF invalida para consulta distDFeInt: {sigla_uf!r}.")
    return codigo
