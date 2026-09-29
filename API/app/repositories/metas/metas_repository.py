from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


class MetasRepository:
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

    def criar(
        self,
        *,
        empresa_id: int,
        indicador_id: int,
        titulo: str,
        descricao: str | None,
        valor_alvo: Decimal,
        tipo_meta: str,
        periodo_tipo: str,
        periodo_inicio: date,
        periodo_fim: date,
        criado_por: int,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO metas (
                        empresa_id, indicador_id, titulo, descricao, valor_alvo,
                        tipo_meta, periodo_tipo, periodo_inicio, periodo_fim, criado_por
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        empresa_id,
                        indicador_id,
                        titulo,
                        descricao,
                        valor_alvo,
                        tipo_meta,
                        periodo_tipo,
                        periodo_inicio,
                        periodo_fim,
                        criado_por,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return dict(row)

    def obter(self, meta_id: int, empresa_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM metas
                    WHERE id = %s AND empresa_id = %s
                    """,
                    (meta_id, empresa_id),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def listar(self, empresa_id: int, status: str | None = None, indicador_id: int | None = None) -> list[dict[str, Any]]:
        filtros = ["empresa_id = %s"]
        params: list[Any] = [empresa_id]

        if status:
            filtros.append("status = %s")
            params.append(status)
        if indicador_id:
            filtros.append("indicador_id = %s")
            params.append(indicador_id)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT *
                    FROM metas
                    WHERE {' AND '.join(filtros)}
                    ORDER BY criado_em DESC
                    """,
                    params,
                )
                return [dict(row) for row in cur.fetchall()]

    def atualizar(self, meta_id: int, empresa_id: int, campos: dict[str, Any]) -> dict[str, Any] | None:
        if not campos:
            return self.obter(meta_id, empresa_id)

        sets = ", ".join(f"{coluna} = %s" for coluna in campos)
        params = [*campos.values(), meta_id, empresa_id]

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE metas
                    SET {sets}, atualizado_em = NOW()
                    WHERE id = %s AND empresa_id = %s
                    RETURNING *
                    """,
                    params,
                )
                row = cur.fetchone()
            conn.commit()
        return dict(row) if row else None

    def cancelar(self, meta_id: int, empresa_id: int) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE metas
                    SET status = 'cancelada', atualizado_em = NOW()
                    WHERE id = %s AND empresa_id = %s
                    """,
                    (meta_id, empresa_id),
                )
                encontrado = cur.rowcount > 0
            conn.commit()
        return encontrado
