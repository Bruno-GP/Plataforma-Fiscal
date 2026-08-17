from __future__ import annotations

from datetime import date
from typing import Any

from app.repositories.sefaz._base import SefazRepositoryBase


class DocumentosRepository(SefazRepositoryBase):
    def inserir_se_novo(
        self,
        *,
        empresa_id: int,
        chave_acesso: str,
        tipo_documento: str,
        direcao: str,
        cnpj_emitente: str,
        cnpj_destinatario: str | None,
        nsu: str,
        data_emissao,
        valor_total: str | None,
        situacao: str | None,
        xml_armazenado: bytes | None,
        manifestacao_status: str | None,
    ) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sefaz.documentos (
                        empresa_id, chave_acesso, tipo_documento, direcao, cnpj_emitente,
                        cnpj_destinatario, nsu, data_emissao, valor_total, situacao,
                        xml_armazenado, manifestacao_status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (empresa_id, chave_acesso) DO NOTHING
                    """,
                    (
                        empresa_id,
                        chave_acesso,
                        tipo_documento,
                        direcao,
                        cnpj_emitente,
                        cnpj_destinatario,
                        nsu,
                        data_emissao,
                        valor_total,
                        situacao,
                        xml_armazenado,
                        manifestacao_status,
                    ),
                )
                inseriu = cur.rowcount == 1
            conn.commit()

        return inseriu

    def obter_por_chave(self, empresa_id: int, chave_acesso: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM sefaz.documentos
                    WHERE empresa_id = %s AND chave_acesso = %s
                    """,
                    (empresa_id, chave_acesso),
                )
                row = cur.fetchone()

        return dict(row) if row else None

    def obter_por_id(self, empresa_id: int, documento_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM sefaz.documentos
                    WHERE empresa_id = %s AND id = %s
                    """,
                    (empresa_id, documento_id),
                )
                row = cur.fetchone()

        return dict(row) if row else None

    def atualizar_manifestacao(self, documento_id: int, manifestacao_status: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE sefaz.documentos
                    SET manifestacao_status = %s,
                        atualizado_em = NOW()
                    WHERE id = %s
                    """,
                    (manifestacao_status, documento_id),
                )
            conn.commit()

    def listar(
        self,
        *,
        empresa_id: int,
        direcao: str | None = None,
        situacao: str | None = None,
        manifestacao_pendente: bool | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[dict[str, Any]]]:
        filtros: list[str] = ["empresa_id = %s"]
        params: list[Any] = [empresa_id]

        if direcao:
            filtros.append("direcao = %s")
            params.append(direcao)
        if situacao:
            filtros.append("situacao = %s")
            params.append(situacao)
        if manifestacao_pendente is True:
            filtros.append("manifestacao_status = 'pendente'")
        if data_inicio:
            filtros.append("data_emissao >= %s")
            params.append(data_inicio)
        if data_fim:
            filtros.append("data_emissao < (%s::date + INTERVAL '1 day')")
            params.append(data_fim)

        where_clause = f"WHERE {' AND '.join(filtros)}"

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT COUNT(*) AS total FROM sefaz.documentos {where_clause}",
                    params,
                )
                total = int(cur.fetchone()["total"])

                cur.execute(
                    f"""
                    SELECT *
                    FROM sefaz.documentos
                    {where_clause}
                    ORDER BY data_emissao DESC NULLS LAST, id DESC
                    LIMIT %s OFFSET %s
                    """,
                    params + [limit, offset],
                )
                rows = [dict(row) for row in cur.fetchall()]

        return total, rows

