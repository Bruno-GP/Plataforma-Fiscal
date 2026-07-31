from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken


def _fernet() -> Fernet:
    key = os.environ.get("CONTAAZUL_TOKEN_ENCRYPTION_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "CONTAAZUL_TOKEN_ENCRYPTION_KEY nao configurada. Gere uma com "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"`."
        )
    return Fernet(key.encode("utf-8"))


def encrypt_token(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_token(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Token Conta Azul corrompido ou chave de criptografia invalida.") from exc
