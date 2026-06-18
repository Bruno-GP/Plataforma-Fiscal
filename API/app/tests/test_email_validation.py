import subprocess

import pytest

from app.services.shared.email_validation import normalizar_email, validar_email_existe_dns


def test_normalizar_email_aplica_trim_e_lowercase():
    assert normalizar_email("  Teste@Exemplo.COM  ") == "teste@exemplo.com"


def test_validar_email_rejeita_formato_invalido():
    with pytest.raises(ValueError, match="e-mail válido"):
        validar_email_existe_dns("email-invalido")


def test_validar_email_rejeita_dominio_inexistente(monkeypatch):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="Server: 1.1.1.1\nAddress: 1.1.1.1\n\n** server can't find example.invalid: NXDOMAIN\n",
            stderr="",
        )

    monkeypatch.setattr("app.services.shared.email_validation.subprocess.run", fake_run)

    with pytest.raises(ValueError, match="dominio do e-mail"):
        validar_email_existe_dns("teste@example.invalid")


def test_validar_email_aceita_dominio_com_mx(monkeypatch):
    def fake_run(cmd, capture_output, text, timeout, check):
        if "-type=mx" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=(
                    "Server: 1.1.1.1\n"
                    "Address: 1.1.1.1\n\n"
                    "Non-authoritative answer:\n"
                    "example.com\tMX preference = 10, mail exchanger = mx.example.com\n"
                ),
                stderr="",
            )

        raise AssertionError("MX should be enough and no fallback DNS lookup should happen.")

    monkeypatch.setattr("app.services.shared.email_validation.subprocess.run", fake_run)

    resultado = validar_email_existe_dns("  teste@example.com  ")

    assert resultado.email == "teste@example.com"
    assert resultado.dominio == "example.com"
    assert resultado.tem_mx is True
    assert resultado.tem_a_ou_aaaa is False


def test_validar_email_aceita_dominio_com_a_sem_mx(monkeypatch):
    chamadas = []

    def fake_run(cmd, capture_output, text, timeout, check):
        chamadas.append(cmd)
        if "-type=mx" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="Server: 1.1.1.1\nAddress: 1.1.1.1\n\n*** example.com has no MX record\n",
                stderr="",
            )
        if "-type=a" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=(
                    "Server: 1.1.1.1\n"
                    "Address: 1.1.1.1\n\n"
                    "Name: example.com\n"
                    "Address: 93.184.216.34\n"
                ),
                stderr="",
            )
        if "-type=aaaa" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="Server: 1.1.1.1\nAddress: 1.1.1.1\n\n*** No AAAA record available\n",
                stderr="",
            )

        raise AssertionError(f"Comando inesperado: {cmd}")

    monkeypatch.setattr("app.services.shared.email_validation.subprocess.run", fake_run)

    resultado = validar_email_existe_dns("teste@example.com")

    assert resultado.email == "teste@example.com"
    assert resultado.tem_mx is False
    assert resultado.tem_a_ou_aaaa is True
    assert any("-type=mx" in cmd for cmd in chamadas)
    assert any("-type=a" in cmd for cmd in chamadas)
    assert any("-type=aaaa" in cmd for cmd in chamadas)
