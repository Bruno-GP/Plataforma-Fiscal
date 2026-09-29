from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row


class IntegracoesRepository:
    def __init__(self, conn_params: dict) -> None:
        self.conn_params = conn_params

    def _connect(self):
        return psycopg.connect(**self.conn_params, row_factory=dict_row)

    def get_by_empresa(self, empresa_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM conta_azul.integracoes WHERE empresa_id = %s",
                    (empresa_id,),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def iniciar_autorizacao(self, empresa_id: int, state: str, expira_em: datetime) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conta_azul.integracoes (empresa_id, status, oauth_state, oauth_state_expira_em)
                    VALUES (%s, 'PENDENTE', %s, %s)
                    ON CONFLICT (empresa_id) DO UPDATE
                    SET status = 'PENDENTE',
                        oauth_state = EXCLUDED.oauth_state,
                        oauth_state_expira_em = EXCLUDED.oauth_state_expira_em,
                        atualizado_em = NOW()
                    """,
                    (empresa_id, state, expira_em),
                )
            conn.commit()

    def validar_state(self, empresa_id: int, state: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM conta_azul.integracoes
                    WHERE empresa_id = %s
                      AND oauth_state = %s
                      AND oauth_state_expira_em > NOW()
                    """,
                    (empresa_id, state),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def salvar_tokens(
        self,
        empresa_id: int,
        access_token_encrypted: str,
        refresh_token_encrypted: str,
        token_expira_em: datetime,
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conta_azul.integracoes (
                        empresa_id, status, access_token_encrypted, refresh_token_encrypted,
                        token_expira_em, oauth_state, oauth_state_expira_em, erro_mensagem
                    )
                    VALUES (%s, 'ATIVA', %s, %s, %s, NULL, NULL, NULL)
                    ON CONFLICT (empresa_id) DO UPDATE
                    SET status = 'ATIVA',
                        access_token_encrypted = EXCLUDED.access_token_encrypted,
                        refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
                        token_expira_em = EXCLUDED.token_expira_em,
                        oauth_state = NULL,
                        oauth_state_expira_em = NULL,
                        erro_mensagem = NULL,
                        atualizado_em = NOW()
                    """,
                    (empresa_id, access_token_encrypted, refresh_token_encrypted, token_expira_em),
                )
            conn.commit()

    def marcar_desconectada(self, empresa_id: int) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE conta_azul.integracoes
                    SET status = 'DESCONECTADA',
                        access_token_encrypted = NULL,
                        refresh_token_encrypted = NULL,
                        token_expira_em = NULL,
                        atualizado_em = NOW()
                    WHERE empresa_id = %s
                    """,
                    (empresa_id,),
                )
            conn.commit()

    def marcar_expirada(self, empresa_id: int) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE conta_azul.integracoes SET status = 'EXPIRADA', atualizado_em = NOW() WHERE empresa_id = %s",
                    (empresa_id,),
                )
            conn.commit()

    def marcar_erro(self, empresa_id: int, erro_mensagem: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE conta_azul.integracoes
                    SET status = 'ERRO', erro_mensagem = %s, atualizado_em = NOW()
                    WHERE empresa_id = %s
                    """,
                    (erro_mensagem, empresa_id),
                )
            conn.commit()
