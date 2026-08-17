from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken


def _fernet() -> Fernet:
    key = os.environ.get("SEFAZ_CERT_ENCRYPTION_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "SEFAZ_CERT_ENCRYPTION_KEY nao configurada. Gere uma com "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"`."
        )

    return Fernet(key.encode("utf-8"))


def encrypt_bytes(value: bytes) -> bytes:
    return _fernet().encrypt(value)


def decrypt_bytes(value: bytes) -> bytes:
    try:
        return _fernet().decrypt(value)
    except InvalidToken as exc:
        raise ValueError(
            "Certificado SEFAZ corrompido ou chave de criptografia invalida."
        ) from exc


def encrypt_text(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError(
            "Senha do certificado SEFAZ corrompida ou chave de criptografia invalida."
        ) from exc
