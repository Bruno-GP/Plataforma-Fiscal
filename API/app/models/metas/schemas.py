from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class TipoMeta(StrEnum):
    CRESCIMENTO = "crescimento"
    REDUCAO = "reducao"
    MANUTENCAO = "manutencao"


class PeriodoTipo(StrEnum):
    MENSAL = "mensal"
    TRIMESTRAL = "trimestral"
    ANUAL = "anual"
    CUSTOM = "custom"


class StatusMeta(StrEnum):
    ATIVA = "ativa"
    ATINGIDA = "atingida"
    NAO_ATINGIDA = "nao_atingida"
    CANCELADA = "cancelada"


class UnidadeIndicador(StrEnum):
    MOEDA = "moeda"
    PERCENTUAL = "percentual"
    NUMERO = "numero"
    DIAS = "dias"


class DirecaoBoa(StrEnum):
    MAIOR_MELHOR = "maior_melhor"
    MENOR_MELHOR = "menor_melhor"


class IndicadorPerfil(StrEnum):
    XML = "xml"
    SPED = "sped"


class IndicadorRecomendacaoStatus(StrEnum):
    SUGERIDO = "sugerido"
    ACEITO = "aceito"
    OCULTADO = "ocultado"


class IndicadorResponse(BaseModel):
    id: int
    chave: str
    nome: str
    unidade: UnidadeIndicador
    direcao_boa: DirecaoBoa
    perfil: IndicadorPerfil


class IndicadorListResponse(BaseModel):
    resultados: list[IndicadorResponse]


class IndicadorRecomendadoResponse(BaseModel):
    indicador_id: int
    chave: str
    nome: str
    unidade: UnidadeIndicador
    direcao_boa: DirecaoBoa
    perfil: IndicadorPerfil
    prioridade: int
    status: IndicadorRecomendacaoStatus
    motivo: str | None = None
    obrigatorio: bool
    score: Decimal


class IndicadorRecomendacoesEmpresaResponse(BaseModel):
    empresa_id: int
    cnae_fiscal: str | None = None
    cnae_fiscal_descricao: str | None = None
    segmento_sugerido: str | None = None
    segmento_nome: str | None = None
    fonte: str | None = None
    confianca: float
    motivo: str
    indicadores: list[IndicadorRecomendadoResponse]


class IndicadorHistoricoPontoResponse(BaseModel):
    periodo: date
    valor: Decimal


class IndicadorHistoricoResponse(BaseModel):
    indicador_id: int
    resultados: list[IndicadorHistoricoPontoResponse]


class MetaCreateRequest(BaseModel):
    indicador_id: int
    titulo: str = Field(min_length=1, max_length=200)
    descricao: str | None = None
    valor_alvo: Decimal = Field(gt=0)
    tipo_meta: TipoMeta
    periodo_tipo: PeriodoTipo
    periodo_inicio: date
    periodo_fim: date

    @model_validator(mode="after")
    def validar_periodo(self) -> "MetaCreateRequest":
        if self.periodo_fim < self.periodo_inicio:
            raise ValueError("periodo_fim nao pode ser anterior a periodo_inicio")
        return self


class MetaUpdateRequest(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    descricao: str | None = None
    valor_alvo: Decimal | None = Field(default=None, gt=0)
    status: StatusMeta | None = None


class MetaResponse(BaseModel):
    id: int
    empresa_id: int
    indicador_id: int
    titulo: str
    descricao: str | None = None
    valor_alvo: Decimal
    tipo_meta: TipoMeta
    periodo_tipo: PeriodoTipo
    periodo_inicio: date
    periodo_fim: date
    status: StatusMeta
    criado_em: datetime
    atualizado_em: datetime


class MetaListResponse(BaseModel):
    total: int
    resultados: list[MetaResponse]


class AnaliseMetaResponse(BaseModel):
    meta_id: int
    valor_alvo: Decimal
    valor_realizado_atual: Decimal
    percentual_atingido: Decimal
    tempo_decorrido_pct: Decimal
    status_ritmo: str
    tendencia: str
    media_periodos_anteriores: Decimal
    mediana_periodos_anteriores: Decimal
    desvio_padrao_periodos_anteriores: Decimal
    variacao_vs_media_pct: Decimal | None
    diagnostico: str
    serie_historica: list[IndicadorHistoricoPontoResponse]
    projecao_fim_periodo: Decimal
    comparativo_ano_anterior_pct: Decimal | None = None
