from __future__ import annotations

from typing import Any

from app.repositories.sefaz._base import SefazRepositoryBase


class IndicadorRecomendacoesRepository(SefazRepositoryBase):
    def obter_empresa_cnae(self, empresa_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, cnpj, cnae_fiscal, cnae_fiscal_descricao
                    FROM public.empresas
                    WHERE id = %s
                    LIMIT 1
                    """,
                    (empresa_id,),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def listar_por_segmento(
        self,
        *,
        empresa_id: int,
        segmento_chave: str,
        perfil: str = "xml",
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        i.id AS indicador_id,
                        i.chave,
                        i.nome,
                        i.unidade,
                        i.direcao_boa,
                        i.perfil,
                        r.prioridade,
                        r.motivo,
                        r.obrigatorio,
                        COALESCE(eir.status, 'sugerido') AS status,
                        COALESCE(eir.score, CASE WHEN r.obrigatorio THEN 90 ELSE 70 END) AS score
                    FROM public.indicador_segmento_recomendacao r
                    JOIN public.indicadores i ON i.id = r.indicador_id
                    LEFT JOIN public.empresa_indicador_recomendado eir
                        ON eir.empresa_id = %s
                       AND eir.indicador_id = i.id
                    WHERE r.segmento_chave = %s
                      AND r.ativo = TRUE
                      AND i.ativo = TRUE
                      AND r.perfil IN (%s, 'ambos')
                      AND i.perfil = %s
                    ORDER BY r.prioridade, i.nome
                    """,
                    (empresa_id, segmento_chave, perfil, perfil),
                )
                return [dict(row) for row in cur.fetchall()]
