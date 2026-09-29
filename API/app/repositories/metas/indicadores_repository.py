from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


class IndicadoresRepository:
    def __init__(self) -> None:
        self.config = carregar_config_postgres()

    def _connect(self):
        last_error: Exception | None = None
        for options in opcoes_conexao_postgres(self.config):
            try:
                return psycopg.connect(**options, row_factory=dict_row)
            except psycopg.Error as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("Configuracao PostgreSQL invalida.")

    def listar(self, perfil: str = "xml") -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, chave, nome, unidade, direcao_boa, perfil
                    FROM indicadores
                    WHERE perfil = %s AND ativo = TRUE
                    ORDER BY nome
                    """,
                    (perfil,),
                )
                return [dict(row) for row in cur.fetchall()]

    def obter_por_id(self, indicador_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, chave, nome, unidade, direcao_boa, perfil, ativo
                    FROM indicadores
                    WHERE id = %s
                    """,
                    (indicador_id,),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def historico(self, empresa_id: int, indicador_id: int, meses: int = 12) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT periodo_referencia AS periodo, valor
                    FROM indicador_historico
                    WHERE empresa_id = %s AND indicador_id = %s
                    ORDER BY periodo_referencia DESC
                    LIMIT %s
                    """,
                    (empresa_id, indicador_id, meses),
                )
                rows = [dict(row) for row in cur.fetchall()]
        return list(reversed(rows))
