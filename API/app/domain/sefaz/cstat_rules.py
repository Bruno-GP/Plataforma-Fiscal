from __future__ import annotations

from dataclasses import dataclass


CSTAT_NENHUM_DOCUMENTO_NOVO = 137
CSTAT_DOCUMENTO_LOCALIZADO = 138
CSTAT_CONSUMO_INDEVIDO = 656

MAX_ITERACOES_PAGINACAO = 20


@dataclass(frozen=True)
class DecisaoPaginacao:
    continuar: bool
    bloqueado: bool
    motivo: str
    rejeitado: bool = False


def decidir_paginacao(cstat: int, iteracao_atual: int) -> DecisaoPaginacao:
    if cstat == CSTAT_CONSUMO_INDEVIDO:
        return DecisaoPaginacao(continuar=False, bloqueado=True, motivo="consumo_indevido")

    if cstat == CSTAT_NENHUM_DOCUMENTO_NOVO:
        return DecisaoPaginacao(continuar=False, bloqueado=False, motivo="sem_novidade")

    if cstat == CSTAT_DOCUMENTO_LOCALIZADO:
        if iteracao_atual >= MAX_ITERACOES_PAGINACAO:
            return DecisaoPaginacao(continuar=False, bloqueado=False, motivo="teto_iteracoes")

        return DecisaoPaginacao(continuar=True, bloqueado=False, motivo="documentos_localizados")

    # cStat fora de {137, 138, 656} e rejeicao/erro da SEFAZ (ex.: 215 "falha no esquema
    # xml", 239 "versao nao suportada") -- nao deve virar "sucesso" silencioso.
    return DecisaoPaginacao(
        continuar=False,
        bloqueado=False,
        motivo=f"cstat_desconhecido_{cstat}",
        rejeitado=True,
    )
