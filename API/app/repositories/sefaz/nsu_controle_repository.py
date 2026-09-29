from __future__ import annotations

from typing import Any

from app.repositories.sefaz._base import SefazRepositoryBase


class NsuControleRepository(SefazRepositoryBase):
    def obter(self, empresa_id: int, ambiente: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM sefaz.nsu_controle WHERE empresa_id = %s AND ambiente = %s",
                    (empresa_id, ambiente),
                )
                row = cur.fetchone()

        return dict(row) if row else None

    def upsert_execucao(
        self,
        empresa_id: int,
        ambiente: int,
        ultimo_nsu: str,
        status_ultima_execucao: str,
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sefaz.nsu_controle (
                        empresa_id, ambiente, ultimo_nsu, ultima_execucao_em, status_ultima_execucao
                    )
                    VALUES (%s, %s, %s, NOW(), %s)
                    ON CONFLICT (empresa_id, ambiente) DO UPDATE
                    SET ultimo_nsu = EXCLUDED.ultimo_nsu,
                        ultima_execucao_em = NOW(),
                        status_ultima_execucao = EXCLUDED.status_ultima_execucao
                    """,
                    (empresa_id, ambiente, ultimo_nsu, status_ultima_execucao),
                )
            conn.commit()

