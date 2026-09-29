import pytest
from cryptography.fernet import Fernet


def test_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setenv("CONTAAZUL_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())

    from app.services.conta_azul.crypto_service import decrypt_token, encrypt_token

    ciphertext = encrypt_token("meu-token-secreto")
    assert ciphertext != "meu-token-secreto"
    assert decrypt_token(ciphertext) == "meu-token-secreto"


def test_encrypt_sem_chave_configurada_falha(monkeypatch):
    monkeypatch.delenv("CONTAAZUL_TOKEN_ENCRYPTION_KEY", raising=False)

    from app.services.conta_azul.crypto_service import encrypt_token

    with pytest.raises(RuntimeError, match="CONTAAZUL_TOKEN_ENCRYPTION_KEY"):
        encrypt_token("qualquer-coisa")


def test_decrypt_token_corrompido_falha(monkeypatch):
    monkeypatch.setenv("CONTAAZUL_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())

    from app.services.conta_azul.crypto_service import decrypt_token

    with pytest.raises(ValueError, match="corrompido"):
        decrypt_token("nao-e-um-token-fernet-valido")
