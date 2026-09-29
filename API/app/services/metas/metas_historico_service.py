from __future__ import annotations

from app.repositories.metas.indicadores_repository import IndicadoresRepository
from app.repositories.metas.metas_historico_repository import MetasHistoricoRepository
from app.services.nfe.empresa_service import normalizar_cnpj


class MetasHistoricoService:
    """Materializa indicador_historico a partir de notas_kpis ja persistido."""

    def __init__(
        self,
        indicadores_repository: IndicadoresRepository | None = None,
        historico_repository: MetasHistoricoRepository | None = None,
    ) -> None:
        self.indicadores_repository = indicadores_repository or IndicadoresRepository()
        self.historico_repository = historico_repository or MetasHistoricoRepository()

    def materializar_empresa(self, empresa_id: int, cnpj: str) -> int:
        indicadores = self.indicadores_repository.listar(perfil="xml")
        indicador_id_por_chave = {i["chave"]: i["id"] for i in indicadores}

        linhas = self.historico_repository.agregar_por_empresa(normalizar_cnpj(cnpj))
        if not linhas:
            return 0

        return self.historico_repository.upsert_historico(empresa_id, indicador_id_por_chave, linhas)
