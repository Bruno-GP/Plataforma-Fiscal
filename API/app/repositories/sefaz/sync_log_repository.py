from __future__ import annotations

from datetime import datetime
from typing import Any

from app.repositories.sefaz._base import SefazRepositoryBase


class SyncLogRepository(SefazRepositoryBase):
    def registrar(
        self,
        *,
        empresa_id: int,
        iniciado_em: datetime,
        finalizado_em: datetime | None,
        documentos_novos: int,
        nsu_inicial: str | None,
        nsu_final: str | None,
        status: str,
        erro_detalhe: str | None,
    ) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sefaz.sync_log (
                        empresa_id, iniciado_em, finalizado_em, documentos_novos,
                        nsu_inicial, nsu_final, status, erro_detalhe
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        empresa_id,
                        iniciado_em,
                        finalizado_em,
                        documentos_novos,
                        nsu_inicial,
                        nsu_final,
                        status,
                        erro_detalhe,
                    ),
                )
                new_id = cur.fetchone()["id"]
            conn.commit()

        return new_id

    def listar(self, empresa_id: int, *, limit: int = 50, offset: int = 0) -> tuple[int, list[dict[str, Any]]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) AS total FROM sefaz.sync_log WHERE empresa_id = %s",
                    (empresa_id,),
                )
                total = int(cur.fetchone()["total"])

                cur.execute(
                    """
                    SELECT *
                    FROM sefaz.sync_log
                    WHERE empresa_id = %s
                    ORDER BY iniciado_em DESC, id DESC
                    LIMIT %s OFFSET %s
                    """,
                    (empresa_id, limit, offset),
                )
                rows = [dict(row) for row in cur.fetchall()]

        return total, rows

    def obter_ultimo_sucesso_com_documentos(self, empresa_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM sefaz.sync_log
                    WHERE empresa_id = %s
                      AND status = 'sucesso'
                      AND documentos_novos > 0
                      AND finalizado_em IS NOT NULL
                    ORDER BY finalizado_em DESC, id DESC
                    LIMIT 1
                    """,
                    (empresa_id,),
                )
                row = cur.fetchone()

        return dict(row) if row else None
