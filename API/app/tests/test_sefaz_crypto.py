import pytest
from cryptography.fernet import Fernet


def test_encrypt_decrypt_bytes_roundtrip(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", Fernet.generate_key().decode())

    from app.services.sefaz.crypto_service import decrypt_bytes, encrypt_bytes

    original = b"conteudo binario do certificado .pfx"
    ciphertext = encrypt_bytes(original)
    assert ciphertext != original
    assert decrypt_bytes(ciphertext) == original


def test_encrypt_decrypt_text_roundtrip(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", Fernet.generate_key().decode())

    from app.services.sefaz.crypto_service import decrypt_text, encrypt_text

    ciphertext = encrypt_text("senha-do-certificado")
    assert ciphertext != "senha-do-certificado"
    assert decrypt_text(ciphertext) == "senha-do-certificado"


def test_encrypt_sem_chave_configurada_falha(monkeypatch):
    monkeypatch.delenv("SEFAZ_CERT_ENCRYPTION_KEY", raising=False)

    from app.services.sefaz.crypto_service import encrypt_text

    with pytest.raises(RuntimeError, match="SEFAZ_CERT_ENCRYPTION_KEY"):
        encrypt_text("qualquer-coisa")


def test_decrypt_bytes_corrompido_falha(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", Fernet.generate_key().decode())

    from app.services.sefaz.crypto_service import decrypt_bytes

    with pytest.raises(ValueError, match="corrompido"):
        decrypt_bytes(b"nao-e-um-token-fernet-valido")


def test_decrypt_text_corrompido_falha(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", Fernet.generate_key().decode())

    from app.services.sefaz.crypto_service import decrypt_text

    with pytest.raises(ValueError, match="corrompida"):
        decrypt_text("nao-e-um-token-fernet-valido")
