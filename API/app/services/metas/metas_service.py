from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.repositories.metas.indicadores_repository import IndicadoresRepository
from app.repositories.metas.metas_repository import MetasRepository
from app.services.metas.analise_meta_service import AnaliseMeta, PontoHistorico, analisar_meta


class MetaNaoEncontradaError(Exception):
    pass


class IndicadorInvalidoError(Exception):
    pass


class MetasService:
    def __init__(
        self,
        metas_repository: MetasRepository | None = None,
        indicadores_repository: IndicadoresRepository | None = None,
    ) -> None:
        self.metas_repository = metas_repository or MetasRepository()
        self.indicadores_repository = indicadores_repository or IndicadoresRepository()

    def _validar_indicador(self, indicador_id: int) -> dict[str, Any]:
        indicador = self.indicadores_repository.obter_por_id(indicador_id)
        if not indicador or not indicador.get("ativo", True) or indicador.get("perfil") != "xml":
            raise IndicadorInvalidoError(f"Indicador {indicador_id} nao existe ou esta inativo.")
        return indicador

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
        self._validar_indicador(indicador_id)
        return self.metas_repository.criar(
            empresa_id=empresa_id,
            indicador_id=indicador_id,
            titulo=titulo,
            descricao=descricao,
            valor_alvo=valor_alvo,
            tipo_meta=tipo_meta,
            periodo_tipo=periodo_tipo,
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            criado_por=criado_por,
        )

    def obter(self, meta_id: int, empresa_id: int) -> dict[str, Any]:
        meta = self.metas_repository.obter(meta_id, empresa_id)
        if not meta:
            raise MetaNaoEncontradaError(f"Meta {meta_id} nao encontrada.")
        return meta

    def listar(self, empresa_id: int, status: str | None = None, indicador_id: int | None = None) -> list[dict[str, Any]]:
        return self.metas_repository.listar(empresa_id, status=status, indicador_id=indicador_id)

    def atualizar(self, meta_id: int, empresa_id: int, campos: dict[str, Any]) -> dict[str, Any]:
        self.obter(meta_id, empresa_id)
        meta = self.metas_repository.atualizar(meta_id, empresa_id, campos)
        if not meta:
            raise MetaNaoEncontradaError(f"Meta {meta_id} nao encontrada.")
        return meta

    def cancelar(self, meta_id: int, empresa_id: int) -> None:
        self.obter(meta_id, empresa_id)
        if not self.metas_repository.cancelar(meta_id, empresa_id):
            raise MetaNaoEncontradaError(f"Meta {meta_id} nao encontrada.")

    def analisar(
        self,
        meta_id: int,
        empresa_id: int,
        *,
        valor_realizado_atual: Decimal,
        data_referencia: date | None = None,
    ) -> AnaliseMeta:
        meta = self.obter(meta_id, empresa_id)
        indicador = self._validar_indicador(meta["indicador_id"])

        n_periodos = 4 if meta["periodo_tipo"] == "trimestral" else 6 if meta["periodo_tipo"] == "mensal" else 12
        historico_bruto = self.indicadores_repository.historico(
            empresa_id=empresa_id,
            indicador_id=meta["indicador_id"],
            meses=max(n_periodos, 12),
        )
        serie_historica = [PontoHistorico(periodo=p["periodo"], valor=Decimal(str(p["valor"]))) for p in historico_bruto]

        return analisar_meta(
            valor_alvo=Decimal(str(meta["valor_alvo"])),
            direcao_boa=indicador["direcao_boa"],
            periodo_inicio=meta["periodo_inicio"],
            periodo_fim=meta["periodo_fim"],
            data_referencia=data_referencia or date.today(),
            valor_realizado_atual=valor_realizado_atual,
            serie_historica=serie_historica,
            n_periodos_referencia=n_periodos,
        )
