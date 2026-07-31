"""Adapter que faz ContaAzulAuth (API/integracoes/conta_azul/contaazul/auth.py)
persistir tokens por empresa em conta_azul.integracoes (Postgres, Fernet-cifrado)
em vez do .tokens.json global (contaazul.auth.TokenStore). Implementa a mesma
interface (load/save/clear) esperada pelo parametro `token_store` de ContaAzulAuth.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_CONTA_AZUL_DIR = Path(__file__).resolve().parents[3] / "integracoes" / "conta_azul"
if str(_CONTA_AZUL_DIR) not in sys.path:
    sys.path.insert(0, str(_CONTA_AZUL_DIR))

from contaazul.auth import TokenSet  # noqa: E402

from app.repositories.conta_azul.integracoes_repository import IntegracoesRepository
from app.services.conta_azul.crypto_service import decrypt_token, encrypt_token
from app.services.conta_azul.postgres_config import carregar_config_postgres_conta_azul


def conn_params_conta_azul() -> dict:
    config = carregar_config_postgres_conta_azul()
    return {
        "host": config["host"],
        "port": config["port"],
        "dbname": config["database"],
        "user": config["user"],
        "password": config["password"],
        "connect_timeout": 5,
        **({"sslmode": config["sslmode"]} if config.get("sslmode") else {}),
    }


class PostgresTokenStore:
    def __init__(self, empresa_id: int, repository: Optional[IntegracoesRepository] = None) -> None:
        self.empresa_id = empresa_id
        self.repository = repository or IntegracoesRepository(conn_params_conta_azul())

    def load(self) -> Optional[TokenSet]:
        integracao = self.repository.get_by_empresa(self.empresa_id)
        if not integracao or not integracao.get("access_token_encrypted"):
            return None

        token_expira_em = integracao["token_expira_em"]
        expires_in = 0
        if token_expira_em:
            expires_in = max(int((token_expira_em - datetime.now(timezone.utc)).total_seconds()), 0)

        return TokenSet(
            access_token=decrypt_token(integracao["access_token_encrypted"]),
            refresh_token=decrypt_token(integracao["refresh_token_encrypted"]),
            expires_in=expires_in,
            obtained_at=datetime.now(timezone.utc).timestamp(),
        )

    def save(self, tokens: TokenSet) -> None:
        token_expira_em = datetime.fromtimestamp(tokens.obtained_at + tokens.expires_in, tz=timezone.utc)
        self.repository.salvar_tokens(
            self.empresa_id,
            encrypt_token(tokens.access_token),
            encrypt_token(tokens.refresh_token),
            token_expira_em,
        )

    def clear(self) -> None:
        self.repository.marcar_desconectada(self.empresa_id)
