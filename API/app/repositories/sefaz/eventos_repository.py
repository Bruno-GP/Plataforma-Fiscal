from __future__ import annotations

from typing import Any

from app.repositories.sefaz._base import SefazRepositoryBase


class EventosRepository(SefazRepositoryBase):
    def inserir(
        self,
        *,
        documento_id: int,
        empresa_id: int,
        tipo_evento: str,
        protocolo: str | None,
        status: str,
        payload_xml: str | None,
    ) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sefaz.eventos (
                        documento_id, empresa_id, tipo_evento, protocolo, status, payload_xml
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (documento_id, empresa_id, tipo_evento, protocolo, status, payload_xml),
                )
                new_id = cur.fetchone()["id"]
            conn.commit()

        return new_id

    def listar_por_documento(self, documento_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM sefaz.eventos
                    WHERE documento_id = %s
                    ORDER BY criado_em DESC, id DESC
                    """,
                    (documento_id,),
                )
                rows = cur.fetchall()

        return [dict(row) for row in rows]

