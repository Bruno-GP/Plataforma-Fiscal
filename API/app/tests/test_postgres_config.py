from app.services.sped.postgres_config import carregar_config_postgres_sped


def test_carregar_config_postgres_sped_preserva_sslmode_do_dsn(monkeypatch):
    monkeypatch.setenv(
        "POSTGRES_SPED_DSN",
        "postgresql://user:pass@db.example.com:5432/sped?sslmode=require",
    )
    monkeypatch.delenv("POSTGRES_SPED_SSLMODE", raising=False)
    monkeypatch.delenv("POSTGRES_SSLMODE", raising=False)
    monkeypatch.delenv("PGSSLMODE", raising=False)

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
