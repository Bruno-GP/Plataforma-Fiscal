from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet


class FakeRepository:
    def __init__(self):
        self.rows = {}

    def get_by_empresa(self, empresa_id):
        return self.rows.get(empresa_id)

    def salvar_tokens(self, empresa_id, access_token_encrypted, refresh_token_encrypted, token_expira_em):
        self.rows[empresa_id] = {
            "access_token_encrypted": access_token_encrypted,
            "refresh_token_encrypted": refresh_token_encrypted,
            "token_expira_em": token_expira_em,
        }

    def marcar_desconectada(self, empresa_id):
        self.rows.pop(empresa_id, None)


def _set_chave(monkeypatch):
    monkeypatch.setenv("CONTAAZUL_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())


def test_load_sem_integracao_retorna_none(monkeypatch):
    _set_chave(monkeypatch)
    from app.services.conta_azul.postgres_token_store import PostgresTokenStore

    store = PostgresTokenStore(empresa_id=1, repository=FakeRepository())
    assert store.load() is None


def test_save_depois_load_faz_roundtrip_cifrado(monkeypatch):
    _set_chave(monkeypatch)
    from contaazul.auth import TokenSet

    from app.services.conta_azul.postgres_token_store import PostgresTokenStore

    repo = FakeRepository()
    store = PostgresTokenStore(empresa_id=1, repository=repo)

    tokens = TokenSet(access_token="access-1", refresh_token="refresh-1", expires_in=3600, obtained_at=datetime.now(timezone.utc).timestamp())
    store.save(tokens)

    assert repo.rows[1]["access_token_encrypted"] != "access-1"

    carregado = store.load()
    assert carregado.access_token == "access-1"
    assert carregado.refresh_token == "refresh-1"
    assert carregado.expires_in > 0


def test_load_token_expirado_retorna_expires_in_zero(monkeypatch):
    _set_chave(monkeypatch)
    from app.services.conta_azul.postgres_token_store import PostgresTokenStore

    repo = FakeRepository()
    store = PostgresTokenStore(empresa_id=1, repository=repo)
    from app.services.conta_azul.crypto_service import encrypt_token

    repo.rows[1] = {
        "access_token_encrypted": encrypt_token("access-velho"),
        "refresh_token_encrypted": encrypt_token("refresh-velho"),
        "token_expira_em": datetime.now(timezone.utc) - timedelta(hours=1),
    }

    carregado = store.load()
    assert carregado.expires_in == 0
    assert carregado.is_expired


def test_clear_remove_integracao(monkeypatch):
    _set_chave(monkeypatch)
    from app.services.conta_azul.postgres_token_store import PostgresTokenStore

    repo = FakeRepository()
    repo.rows[1] = {"access_token_encrypted": "x", "refresh_token_encrypted": "y", "token_expira_em": None}
    store = PostgresTokenStore(empresa_id=1, repository=repo)

    store.clear()

    assert store.load() is None
