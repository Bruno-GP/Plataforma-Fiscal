from __future__ import annotations

from app.repositories.sefaz._base import SefazRepositoryBase


class SefazEmpresasRepository(SefazRepositoryBase):
    def obter_estado(self, empresa_id: int) -> str | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT estado FROM empresas WHERE id = %s", (empresa_id,))
                row = cur.fetchone()

        return row["estado"] if row else None
