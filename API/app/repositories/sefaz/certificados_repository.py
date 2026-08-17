from __future__ import annotations

from datetime import date
from typing import Any

from app.repositories.sefaz._base import SefazRepositoryBase


class CertificadosRepository(SefazRepositoryBase):
    def get_ativo(self, empresa_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM sefaz.certificados WHERE empresa_id = %s AND ativo = TRUE",
                    (empresa_id,),
                )
                row = cur.fetchone()

        return dict(row) if row else None

    def inserir(
        self,
        *,
        empresa_id: int,
        arquivo_certificado: bytes,
        senha_criptografada: str,
        cnpj_titular: str,
        data_validade: date,
    ) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE sefaz.certificados SET ativo = FALSE WHERE empresa_id = %s AND ativo = TRUE",
                    (empresa_id,),
                )
                cur.execute(
                    """
                    INSERT INTO sefaz.certificados (
                        empresa_id, arquivo_certificado, senha_criptografada,
                        cnpj_titular, data_validade, ativo
                    )
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                    RETURNING id
                    """,
                    (empresa_id, arquivo_certificado, senha_criptografada, cnpj_titular, data_validade),
                )
                new_id = cur.fetchone()["id"]
            conn.commit()

        return new_id

    def listar_ativos_com_validade(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, empresa_id, cnpj_titular, data_validade, ativo
                    FROM sefaz.certificados
                    WHERE ativo = TRUE
                    ORDER BY criado_em DESC, id DESC
                    """
                )
                rows = cur.fetchall()

        return [dict(row) for row in rows]

