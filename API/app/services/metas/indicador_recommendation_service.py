from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from app.services.cnpj.cnae_classifier_service import CnaeClassifierService


class EmpresaNaoEncontradaError(Exception):
    pass


class IndicadorRecomendacoesRepositoryProtocol(Protocol):
    def obter_empresa_cnae(self, empresa_id: int) -> dict[str, Any] | None:
        ...

    def listar_por_segmento(
        self,
        *,
        empresa_id: int,
        segmento_chave: str,
        perfil: str = "xml",
    ) -> list[dict[str, Any]]:
        ...


@dataclass(frozen=True)
class IndicadorRecomendado:
    indicador_id: int
    chave: str
    nome: str
    unidade: str
    direcao_boa: str
    perfil: str
    prioridade: int
    status: str
    motivo: str | None
    obrigatorio: bool
    score: Decimal


@dataclass(frozen=True)
class IndicadorRecommendationResult:
    empresa_id: int
    cnae_fiscal: str | None
    cnae_fiscal_descricao: str | None
    segmento_sugerido: str | None
    segmento_nome: str | None
    fonte: str | None
    confianca: float
    motivo: str
    indicadores: list[IndicadorRecomendado]


class IndicadorRecommendationService:
    def __init__(
        self,
        repository: IndicadorRecomendacoesRepositoryProtocol | None = None,
        classifier: CnaeClassifierService | None = None,
    ) -> None:
        if repository is None:
            from app.repositories.metas.indicador_recomendacoes_repository import IndicadorRecomendacoesRepository

            repository = IndicadorRecomendacoesRepository()

        self.repository = repository
        self.classifier = classifier or CnaeClassifierService()

    def recomendar_para_empresa(self, empresa_id: int, perfil: str = "xml") -> IndicadorRecommendationResult:
        empresa = self.repository.obter_empresa_cnae(empresa_id)
        if not empresa:
            raise EmpresaNaoEncontradaError(f"Empresa {empresa_id} nao encontrada.")

        cnae_fiscal = empresa.get("cnae_fiscal")
        classificacao = self.classifier.classificar(cnae_fiscal)

        indicadores: list[IndicadorRecomendado] = []
        if classificacao.segmento_chave:
            linhas = self.repository.listar_por_segmento(
                empresa_id=empresa_id,
                segmento_chave=classificacao.segmento_chave,
                perfil=perfil,
            )
            indicadores = [self._build_indicador_recomendado(linha) for linha in linhas]

        return IndicadorRecommendationResult(
            empresa_id=empresa_id,
            cnae_fiscal=classificacao.cnae_codigo or None,
            cnae_fiscal_descricao=empresa.get("cnae_fiscal_descricao"),
            segmento_sugerido=classificacao.segmento_chave,
            segmento_nome=classificacao.segmento_nome,
            fonte="cnae" if classificacao.segmento_chave else None,
            confianca=classificacao.confianca,
            motivo=classificacao.motivo,
            indicadores=indicadores,
        )

    @staticmethod
    def _build_indicador_recomendado(linha: dict[str, Any]) -> IndicadorRecomendado:
        return IndicadorRecomendado(
            indicador_id=int(linha["indicador_id"]),
            chave=str(linha["chave"]),
            nome=str(linha["nome"]),
            unidade=str(linha["unidade"]),
            direcao_boa=str(linha["direcao_boa"]),
            perfil=str(linha["perfil"]),
            prioridade=int(linha["prioridade"]),
            status=str(linha.get("status") or "sugerido"),
            motivo=linha.get("motivo"),
            obrigatorio=bool(linha.get("obrigatorio", False)),
            score=Decimal(str(linha.get("score", 0))),
        )
