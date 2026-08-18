from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.domain.sefaz.cstat_rules import decidir_paginacao
from app.domain.sefaz.doc_parser import (
    DocumentoParseInvalidoError,
    calcular_direcao,
    parse_documento,
)
from app.domain.sefaz.uf_codigos import UfInvalidaError, codigo_ibge_uf
from app.repositories.sefaz.documentos_repository import DocumentosRepository
from app.repositories.sefaz.empresas_repository import SefazEmpresasRepository
from app.repositories.sefaz.eventos_repository import EventosRepository
from app.repositories.sefaz.nsu_controle_repository import NsuControleRepository
from app.repositories.sefaz.sync_log_repository import SyncLogRepository
from app.services.sefaz.certificado_service import CertificadoService
from app.services.sefaz.distribuicao_dfe_client import DistribuicaoDFeClient
from app.workers.celery_app import celery_app


logger = logging.getLogger("services.sefaz")

NSU_INICIAL_PADRAO = "000000000000000"

# SEFAZ nao publica um numero exato de espera apos cStat=656 (consumo indevido); 1h e o
# minimo conservador adotado no projeto (ver docs/mapeamento-busca-xml-sefaz.md). Sem essa
# trava local, qualquer retry manual/automatico antes disso gera nova consulta real e pode
# prolongar o bloqueio -- por isso o service nao chama a SEFAZ de novo dentro da janela.
JANELA_ESPERA_BLOQUEIO = timedelta(hours=1)


class CertificadoAusenteError(ValueError):
    pass


class EmpresaUfAusenteError(ValueError):
    pass


@dataclass(frozen=True)
class ResultadoSincronizacao:
    status: str
    documentos_novos: int
    nsu_inicial: str
    nsu_final: str
    erro_detalhe: str | None = None


class SefazDistribuicaoService:
    def __init__(
        self,
        certificado_service: CertificadoService | None = None,
        nsu_repository: NsuControleRepository | None = None,
        documentos_repository: DocumentosRepository | None = None,
        eventos_repository: EventosRepository | None = None,
        sync_log_repository: SyncLogRepository | None = None,
        empresas_repository: SefazEmpresasRepository | None = None,
        client_factory=DistribuicaoDFeClient,
    ) -> None:
        self.certificado_service = certificado_service or CertificadoService()
        self.nsu_repository = nsu_repository or NsuControleRepository()
        self.documentos_repository = documentos_repository or DocumentosRepository()
        self.eventos_repository = eventos_repository or EventosRepository()
        self.sync_log_repository = sync_log_repository or SyncLogRepository()
        self.empresas_repository = empresas_repository or SefazEmpresasRepository()
        self.client_factory = client_factory

    def sincronizar_empresa(
        self,
        empresa_id: int,
        cnpj_empresa: str,
        ambiente: int = 1,
    ) -> ResultadoSincronizacao:
        iniciado_em = datetime.now(timezone.utc)

        credenciais = self.certificado_service.obter_credenciais_descriptografadas(empresa_id)
        if credenciais is None:
            raise CertificadoAusenteError(f"Empresa {empresa_id} nao possui certificado SEFAZ ativo.")
        certificado_pfx, senha = credenciais

        estado_empresa = self.empresas_repository.obter_estado(empresa_id)
        if not estado_empresa:
            raise EmpresaUfAusenteError(f"Empresa {empresa_id} nao possui UF cadastrada.")
        try:
            uf_autor = codigo_ibge_uf(estado_empresa)
        except UfInvalidaError as exc:
            raise EmpresaUfAusenteError(str(exc)) from exc

        cursor = self.nsu_repository.obter(empresa_id, ambiente)
        nsu_inicial = cursor["ultimo_nsu"] if cursor else NSU_INICIAL_PADRAO
        ultimo_nsu = nsu_inicial

        if cursor and cursor.get("status_ultima_execucao") == "bloqueado":
            ultima_execucao = cursor.get("ultima_execucao_em")
            decorrido = (
                datetime.now(timezone.utc) - ultima_execucao if ultima_execucao else JANELA_ESPERA_BLOQUEIO
            )
            if decorrido < JANELA_ESPERA_BLOQUEIO:
                restante_min = int((JANELA_ESPERA_BLOQUEIO - decorrido).total_seconds() // 60) + 1
                erro_detalhe = (
                    f"Bloqueio anterior da SEFAZ (cStat 656) ainda na janela de espera -- "
                    f"aguardar mais {restante_min} min antes de tentar de novo."
                )
                self.sync_log_repository.registrar(
                    empresa_id=empresa_id,
                    iniciado_em=iniciado_em,
                    finalizado_em=datetime.now(timezone.utc),
                    documentos_novos=0,
                    nsu_inicial=nsu_inicial,
                    nsu_final=nsu_inicial,
                    status="bloqueado",
                    erro_detalhe=erro_detalhe,
                )
                return ResultadoSincronizacao(
                    status="bloqueado",
                    documentos_novos=0,
                    nsu_inicial=nsu_inicial,
                    nsu_final=nsu_inicial,
                    erro_detalhe=erro_detalhe,
                )

        cliente = self.client_factory(certificado_pfx, senha, cnpj_empresa, ambiente, uf_autor=uf_autor)
        documentos_novos = 0
        iteracao = 1
        status_final = "sucesso"
        erro_detalhe: str | None = None

        try:
            while True:
                resposta = cliente.consultar(ultimo_nsu)
                decisao = decidir_paginacao(resposta.cstat, iteracao)

                for documento_bruto in resposta.documentos:
                    documentos_novos += self._persistir_documento(
                        empresa_id=empresa_id,
                        cnpj_empresa=cnpj_empresa,
                        documento_bruto=documento_bruto,
                    )

                ultimo_nsu = resposta.ultimo_nsu

                if decisao.rejeitado:
                    status_final = "erro"
                    erro_detalhe = f"SEFAZ rejeitou distDFeInt (cStat {resposta.cstat}): {resposta.x_motivo or 'sem xMotivo'}"
                    break
                if decisao.bloqueado:
                    status_final = "bloqueado"
                    erro_detalhe = "Consumo indevido (cStat 656) -- aguardando janela de espera."
                    break
                if not decisao.continuar:
                    break
                iteracao += 1
        except Exception as exc:
            status_final = "erro"
            erro_detalhe = str(exc)
            logger.exception("sefaz_sync_falhou", extra={"empresa_id": empresa_id, "iteracao": iteracao})
            self.nsu_repository.upsert_execucao(empresa_id, ambiente, ultimo_nsu, status_final)
            self.sync_log_repository.registrar(
                empresa_id=empresa_id,
                iniciado_em=iniciado_em,
                finalizado_em=datetime.now(timezone.utc),
                documentos_novos=documentos_novos,
                nsu_inicial=nsu_inicial,
                nsu_final=ultimo_nsu,
                status=status_final,
                erro_detalhe=erro_detalhe,
            )
            raise

        self.nsu_repository.upsert_execucao(empresa_id, ambiente, ultimo_nsu, status_final)
        self.sync_log_repository.registrar(
            empresa_id=empresa_id,
            iniciado_em=iniciado_em,
            finalizado_em=datetime.now(timezone.utc),
            documentos_novos=documentos_novos,
            nsu_inicial=nsu_inicial,
            nsu_final=ultimo_nsu,
            status=status_final,
            erro_detalhe=erro_detalhe,
        )

        return ResultadoSincronizacao(
            status=status_final,
            documentos_novos=documentos_novos,
            nsu_inicial=nsu_inicial,
            nsu_final=ultimo_nsu,
            erro_detalhe=erro_detalhe,
        )

    def _persistir_documento(self, empresa_id: int, cnpj_empresa: str, documento_bruto) -> int:
        if documento_bruto.schema == "resEvento":
            self._persistir_evento(empresa_id, documento_bruto)
            return 0

        try:
            parseado = parse_documento(documento_bruto.schema, documento_bruto.xml_bytes)
        except DocumentoParseInvalidoError:
            logger.warning(
                "sefaz_documento_parse_invalido",
                extra={"empresa_id": empresa_id, "schema": documento_bruto.schema, "nsu": documento_bruto.nsu},
            )
            return 0

        direcao = calcular_direcao(parseado.cnpj_emitente, cnpj_empresa)
        inseriu = self.documentos_repository.inserir_se_novo(
            empresa_id=empresa_id,
            chave_acesso=parseado.chave_acesso,
            tipo_documento=parseado.tipo_documento,
            direcao=direcao,
            cnpj_emitente=parseado.cnpj_emitente,
            cnpj_destinatario=parseado.cnpj_destinatario,
            nsu=documento_bruto.nsu,
            data_emissao=parseado.data_emissao,
            valor_total=parseado.valor_total,
            situacao=parseado.situacao,
            xml_armazenado=documento_bruto.xml_bytes if documento_bruto.schema == "nfeProc" else None,
            manifestacao_status="pendente" if direcao == "recebida" else None,
        )
        if inseriu:
            self._publicar_evento_documento_novo(empresa_id, parseado.chave_acesso)
        return 1 if inseriu else 0

    def _publicar_evento_documento_novo(self, empresa_id: int, chave_acesso: str) -> None:
        """Hook desacoplado para o módulo fiscal/NCM reagir a documento novo no futuro."""
        try:
            celery_app.send_task(
                "sefaz_evento_documento_novo_task",
                args=[empresa_id, chave_acesso],
                queue="sefaz",
            )
        except Exception:
            logger.warning(
                "sefaz_publicar_evento_documento_novo_falhou",
                extra={"empresa_id": empresa_id, "chave_acesso": chave_acesso},
            )

    def _persistir_evento(self, empresa_id: int, documento_bruto) -> None:
        try:
            parseado = parse_documento("resEvento", documento_bruto.xml_bytes)
        except DocumentoParseInvalidoError:
            logger.warning(
                "sefaz_evento_parse_invalido",
                extra={"empresa_id": empresa_id, "nsu": documento_bruto.nsu},
            )
            return

        documento = self.documentos_repository.obter_por_chave(empresa_id, parseado.chave_acesso)
        if documento is None:
            logger.info(
                "sefaz_evento_sem_documento_correspondente",
                extra={"empresa_id": empresa_id, "chave_acesso": parseado.chave_acesso},
            )
            return

        self.eventos_repository.inserir(
            documento_id=documento["id"],
            empresa_id=empresa_id,
            tipo_evento=parseado.tipo_evento or "desconhecido",
            protocolo=parseado.protocolo,
            status="recebido",
            payload_xml=documento_bruto.xml_bytes.decode("utf-8", errors="replace"),
        )
