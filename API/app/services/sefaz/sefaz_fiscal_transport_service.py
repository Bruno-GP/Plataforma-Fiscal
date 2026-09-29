from __future__ import annotations

import logging
from typing import Any

from app.repositories.sefaz.documentos_repository import DocumentosRepository
from app.services.nfe.process_nfe import ProcessarNFeService


logger = logging.getLogger("services.sefaz.fiscal_transport")


def _xml_bytes(valor: Any) -> bytes:
    if hasattr(valor, "tobytes"):
        return valor.tobytes()
    if isinstance(valor, (bytes, bytearray)):
        return bytes(valor)
    return bytes(valor)


class SefazFiscalTransportService:
    """Transporta itens de documentos SEFAZ 'emitida' para as tabelas Fiscal."""

    def __init__(self, documentos_repository: DocumentosRepository | None = None) -> None:
        self.documentos_repository = documentos_repository or DocumentosRepository()

    def transportar_documentos(
        self,
        *,
        empresa_id: int,
        cnpj_empresa: str,
        documentos: list[dict[str, Any]],
    ) -> int:
        elegiveis = [
            documento
            for documento in documentos
            if documento.get("direcao") == "emitida"
            and documento.get("xml_armazenado")
            and not documento.get("processado_fiscal_em")
        ]
        if not elegiveis:
            return 0

        tuplas = [
            (documento["id"], documento["chave_acesso"], _xml_bytes(documento["xml_armazenado"]))
            for documento in elegiveis
        ]

        resposta, ids_processados = ProcessarNFeService().executar_xmls_importados(
            cnpj_emitente=cnpj_empresa,
            xmls_importados=tuplas,
        )

        if resposta.status != "processado":
            logger.warning(
                "sefaz_fiscal_transport_falhou",
                extra={
                    "empresa_id": empresa_id,
                    "cnpj_empresa": cnpj_empresa,
                    "documentos": [documento["id"] for documento in elegiveis],
                    "erros": resposta.erros,
                },
            )
            return 0

        ids_processados_set = set(ids_processados)
        total_marcados = 0
        for documento in elegiveis:
            if documento["id"] in ids_processados_set:
                self.documentos_repository.marcar_processado_fiscal(documento["id"])
                total_marcados += 1

        logger.info(
            "sefaz_fiscal_transport_concluido",
            extra={
                "empresa_id": empresa_id,
                "cnpj_empresa": cnpj_empresa,
                "total_elegiveis": len(elegiveis),
                "total_marcados": total_marcados,
            },
        )
        return total_marcados
