from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CertificadoStatusResponse(BaseModel):
    ativo: bool
    cnpj_titular: str | None = None
    data_validade: date | None = None
    dias_restantes: int | None = None


class SefazSyncResponse(BaseModel):
    status: str
    message: str
    empresa_id: int


class SefazSyncStatusResponse(BaseModel):
    disponivel: bool
    bloqueado_ate: datetime | None = None
    segundos_restantes: int = 0
    ultima_sincronizacao_com_notas_em: datetime | None = None
    documentos_novos_ultima_sync: int = 0


class SefazDocumentoResponse(BaseModel):
    id: int
    chave_acesso: str
    tipo_documento: str
    direcao: str
    cnpj_emitente: str
    cnpj_destinatario: str | None = None
    nsu: str
    data_emissao: date | None = None
    valor_total: Decimal | None = None
    situacao: str | None = None
    manifestacao_status: str | None = None
    criado_em: datetime | None = None
    atualizado_em: datetime | None = None
    processado_fiscal_em: datetime | None = None


class SefazDocumentoDetalheResponse(SefazDocumentoResponse):
    xml_armazenado_base64: str | None = None


class SefazDocumentoListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    resultados: list[SefazDocumentoResponse] = Field(default_factory=list)


class ManifestacaoRequest(BaseModel):
    tipo_manifestacao: str


class ManifestacaoResponse(BaseModel):
    documento_id: int
    manifestacao_status: str


class SefazSyncLogResponse(BaseModel):
    id: int
    empresa_id: int
    iniciado_em: datetime
    finalizado_em: datetime | None = None
    documentos_novos: int
    nsu_inicial: str | None = None
    nsu_final: str | None = None
    status: str
    erro_detalhe: str | None = None


class SefazSyncLogListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    resultados: list[SefazSyncLogResponse] = Field(default_factory=list)
