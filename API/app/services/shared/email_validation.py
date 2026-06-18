from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass


_EMAIL_FORMAT_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_MX_REGEX = re.compile(r"mail exchanger\s*=\s*(?P<host>\S+)", re.IGNORECASE)
_ADDRESS_REGEX = re.compile(
    r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])|(?:[0-9A-Fa-f]{0,4}:){2,}[0-9A-Fa-f]{0,4}",
)
_DNS_TIMEOUT_SECONDS = 2.5


@dataclass(frozen=True)
class EmailValidacaoResultado:
    email: str
    dominio: str
    tem_mx: bool
    tem_a_ou_aaaa: bool


def normalizar_email(valor: str | None) -> str:
    return (valor or "").strip().lower()


def _validar_formato_email(email: str) -> None:
    if not _EMAIL_FORMAT_REGEX.fullmatch(email):
        raise ValueError("Informe um e-mail válido.")


def _extrair_dominio(email: str) -> str:
    partes = email.rsplit("@", 1)
    if len(partes) != 2:
        raise ValueError("Informe um e-mail válido.")

    dominio = partes[1].strip()
    if not dominio:
        raise ValueError("Informe um e-mail válido.")

    return dominio


def _executar_nslookup(tipo: str, dominio: str) -> str:
    try:
        resultado = subprocess.run(
            ["nslookup", f"-type={tipo}", dominio],
            capture_output=True,
            text=True,
            timeout=_DNS_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Nao foi possivel validar o dominio do e-mail no momento. Tente novamente.") from exc
    except FileNotFoundError as exc:
        raise ValueError("Nao foi possivel validar o dominio do e-mail no momento. Tente novamente.") from exc

    saida = f"{resultado.stdout or ''}\n{resultado.stderr or ''}".strip()
    return saida


def _resultado_tem_mx(saida: str) -> bool:
    return bool(_MX_REGEX.search(saida))


def _resultado_tem_a_ou_aaaa(saida: str) -> bool:
    texto = saida.lower()
    if any(frase in texto for frase in ("non-existent domain", "nxdomain", "server failed", "servfail", "can't find")):
        return False

    return bool(_ADDRESS_REGEX.search(saida)) and "name:" in texto


def validar_email_existe_dns(email: str | None) -> EmailValidacaoResultado:
    email_normalizado = normalizar_email(email)
    if not email_normalizado:
        raise ValueError("Informe um e-mail válido.")

    _validar_formato_email(email_normalizado)
    dominio = _extrair_dominio(email_normalizado)

    saida_mx = _executar_nslookup("mx", dominio)
    if _resultado_tem_mx(saida_mx):
        return EmailValidacaoResultado(
            email=email_normalizado,
            dominio=dominio,
            tem_mx=True,
            tem_a_ou_aaaa=False,
        )

    saida_a = _executar_nslookup("a", dominio)
    saida_aaaa = _executar_nslookup("aaaa", dominio)
    tem_a_ou_aaaa = _resultado_tem_a_ou_aaaa(saida_a) or _resultado_tem_a_ou_aaaa(saida_aaaa)

    if not tem_a_ou_aaaa:
        raise ValueError("O dominio do e-mail nao foi encontrado ou nao possui MX nem A/AAAA.")

    return EmailValidacaoResultado(
        email=email_normalizado,
        dominio=dominio,
        tem_mx=False,
        tem_a_ou_aaaa=True,
    )
