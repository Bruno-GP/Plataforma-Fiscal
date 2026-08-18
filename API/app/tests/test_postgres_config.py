from app.services.sped.postgres_config import carregar_config_postgres_sped
from app.services.nfe.postres_config import carregar_config_postgres


def _limpar_overrides_postgres_sped(monkeypatch):
    for chave in (
        "POSTGRES_SPED_HOST", "POSTGRES_HOST", "PGHOST",
        "POSTGRES_SPED_PORT", "POSTGRES_PORT", "PGPORT",
        "POSTGRES_SPED_DB", "POSTGRES_DB_SPED", "POSTGRES_DB", "PGDATABASE",
        "POSTGRES_SPED_USER", "POSTGRES_USER", "PGUSER",
        "POSTGRES_SPED_PASSWORD", "POSTGRES_PASSWORD", "PGPASSWORD",
        "POSTGRES_SPED_SSLMODE", "POSTGRES_SSLMODE", "PGSSLMODE",
    ):
        monkeypatch.delenv(chave, raising=False)


def test_carregar_config_postgres_sped_preserva_sslmode_do_dsn(monkeypatch):
    _limpar_overrides_postgres_sped(monkeypatch)
    monkeypatch.setenv(
        "POSTGRES_SPED_DSN",
        "postgresql://user:pass@db.example.com:5432/sped?sslmode=require",
    )

    config = carregar_config_postgres_sped()

    assert config["host"] == "db.example.com"
    assert config["database"] == "sped"
    assert config["sslmode"] == "require"


def test_carregar_config_postgres_sped_prioriza_sslmode_explicito(monkeypatch):
    monkeypatch.setenv(
        "POSTGRES_SPED_DSN",
        "postgresql://user:pass@db.example.com:5432/sped?sslmode=require",
    )
    monkeypatch.setenv("POSTGRES_SPED_SSLMODE", "verify-full")

    config = carregar_config_postgres_sped()

    assert config["sslmode"] == "verify-full"

