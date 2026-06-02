import pytest

from app.core.config import validate_production_config
from app.main import ensure_database_schema


def test_validate_production_config_ignora_desenvolvimento(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_SECRET_KEY", "change-me")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "*")

    validate_production_config()


def test_validate_production_config_rejeita_segredo_padrao(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET_KEY", "change-me")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://painel.example.com")
    monkeypatch.setenv("CORS_ALLOW_ORIGIN_REGEX", "")

    with pytest.raises(RuntimeError, match="AUTH_SECRET_KEY"):
        validate_production_config()


def test_validate_production_config_rejeita_cookie_inseguro(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://painel.example.com")
    monkeypatch.setenv("CORS_ALLOW_ORIGIN_REGEX", "")

    with pytest.raises(RuntimeError, match="AUTH_COOKIE_SECURE"):
        validate_production_config()


def test_validate_production_config_rejeita_cors_wildcard(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "*")
    monkeypatch.setenv("CORS_ALLOW_ORIGIN_REGEX", "")

    with pytest.raises(RuntimeError, match="wildcard"):
        validate_production_config()


def test_validate_production_config_aceita_producao_segura(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://painel.example.com")
    monkeypatch.setenv("CORS_ALLOW_ORIGIN_REGEX", "")

    validate_production_config()


def test_startup_schema_ensure_flag_falha_com_orientacao_alembic(monkeypatch):
    monkeypatch.setenv("ENABLE_STARTUP_SCHEMA_ENSURE", "true")

    with pytest.raises(RuntimeError, match="migrations Alembic"):
        ensure_database_schema()
