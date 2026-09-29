from __future__ import annotations

from datetime import date, datetime, timedelta

from app.repositories.sefaz.documentos_repository import DocumentosRepository


MANIFESTACOES_VALIDAS = {"ciencia", "confirmada", "desconhecida", "nao_realizada"}
PRAZO_MANIFESTACAO_DIAS = 10


class ManifestacaoInvalidaError(ValueError):
    pass


class DocumentoNaoPertenceEmpresaError(ValueError):
    pass


def montar_texto_alerta_prazo(chave_acesso: str, dias_restantes: int) -> str:
    if dias_restantes <= 0:
        return (
            f"Documento {chave_acesso}: prazo de manifestacao do destinatario vencido. "
            "Manifeste-se o quanto antes para nao perder o direito ao credito."
        )

    plural = "dia" if dias_restantes == 1 else "dias"
    return (
        f"Documento {chave_acesso}: faltam {dias_restantes} {plural} para o prazo de "
        "manifestacao do destinatario."
    )


class ManifestacaoDestinatarioService:
    def __init__(self, documentos_repository: DocumentosRepository | None = None) -> None:
        self.documentos_repository = documentos_repository or DocumentosRepository()

    def manifestar(self, empresa_id: int, documento_id: int, tipo_manifestacao: str) -> dict:
        if tipo_manifestacao not in MANIFESTACOES_VALIDAS:
            raise ManifestacaoInvalidaError(
                f"Tipo de manifestacao invalido: {tipo_manifestacao!r}. "
                f"Esperado um de {sorted(MANIFESTACOES_VALIDAS)}."
            )

        documento = self.documentos_repository.obter_por_id(empresa_id, documento_id)
        if documento is None:
            raise DocumentoNaoPertenceEmpresaError(
                f"Documento {documento_id} nao encontrado para a empresa {empresa_id}."
            )

        if documento["direcao"] != "recebida":
            raise ManifestacaoInvalidaError("Manifestacao so se aplica a documentos recebidos.")

        # A integração com a SEFAZ para envio do evento vem na próxima etapa.
        self.documentos_repository.atualizar_manifestacao(documento_id, tipo_manifestacao)

        return {"documento_id": documento_id, "manifestacao_status": tipo_manifestacao}

    def listar_pendentes_proximas_do_prazo(
        self,
        empresa_id: int,
        dias_restantes_max: int = 3,
    ) -> list[dict]:
        _, pendentes = self.documentos_repository.listar(
            empresa_id=empresa_id,
            manifestacao_pendente=True,
            limit=500,
            offset=0,
        )

        hoje = date.today()
        alerta: list[dict] = []
        for documento in pendentes:
            data_emissao = documento.get("data_emissao")
            if not data_emissao:
                continue

            if isinstance(data_emissao, datetime):
                data_emissao = data_emissao.date()
            elif not isinstance(data_emissao, date):
                continue

            prazo_final = data_emissao + timedelta(days=PRAZO_MANIFESTACAO_DIAS)
            dias_restantes = (prazo_final - hoje).days
            if dias_restantes <= dias_restantes_max:
                alerta.append({**documento, "dias_restantes_manifestacao": dias_restantes})

        return alerta
