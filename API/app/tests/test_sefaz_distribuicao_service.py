from datetime import datetime, timedelta, timezone

import pytest

from app.services.sefaz.distribuicao_dfe_client import (
    DocumentoBruto,
    RespostaDistribuicao,
    ResultadoEvento,
    SefazIndisponivelError,
)


class FakeCertificadoService:
    def __init__(self, credenciais=(b"pfx", "senha")):
        self.credenciais = credenciais

    def obter_credenciais_descriptografadas(self, empresa_id):
        return self.credenciais


class FakeNsuRepository:
    def __init__(self, ultimo_nsu=None, status_ultima_execucao=None, ultima_execucao_em=None):
        self.ultimo_nsu = ultimo_nsu
        self.status_ultima_execucao = status_ultima_execucao
        self.ultima_execucao_em = ultima_execucao_em
        self.execucoes = []

    def obter(self, empresa_id, ambiente):
        if self.ultimo_nsu is None:
            return None
        return {
            "ultimo_nsu": self.ultimo_nsu,
            "status_ultima_execucao": self.status_ultima_execucao,
            "ultima_execucao_em": self.ultima_execucao_em,
        }

    def upsert_execucao(self, empresa_id, ambiente, ultimo_nsu, status_ultima_execucao):
        self.execucoes.append((empresa_id, ambiente, ultimo_nsu, status_ultima_execucao))


class FakeDocumentosRepository:
    def __init__(self):
        self.inseridos: list[dict] = []
        self.chaves_existentes: set[str] = set()

    def inserir_se_novo(self, **kwargs):
        if kwargs["chave_acesso"] in self.chaves_existentes:
            return False
        self.chaves_existentes.add(kwargs["chave_acesso"])
        self.inseridos.append(kwargs)
        return True

    def obter_por_chave(self, empresa_id, chave_acesso):
        for doc in self.inseridos:
            if doc["chave_acesso"] == chave_acesso:
                return {**doc, "id": 1}
        return None

    def listar_pendentes_ciencia(self, empresa_id, limite):
        return [
            {"id": indice + 1, "chave_acesso": doc["chave_acesso"]}
            for indice, doc in enumerate(self.inseridos)
            if doc["direcao"] == "recebida"
            and doc["manifestacao_status"] == "pendente"
            and doc["xml_armazenado"] is None
        ][:limite]

    def atualizar_manifestacao(self, documento_id, manifestacao_status):
        self.manifestacoes = getattr(self, "manifestacoes", [])
        self.manifestacoes.append((documento_id, manifestacao_status))

    def guardar_xml_completo(self, empresa_id, chave_acesso, xml_armazenado):
        self.xmls_completos = getattr(self, "xmls_completos", [])
        self.xmls_completos.append((chave_acesso, xml_armazenado))
        return True


class FakeEventosRepository:
    def __init__(self):
        self.inseridos: list[dict] = []

    def inserir(self, **kwargs):
        self.inseridos.append(kwargs)
        return len(self.inseridos)


class FakeSyncLogRepository:
    def __init__(self):
        self.registros: list[dict] = []

    def registrar(self, **kwargs):
        self.registros.append(kwargs)
        return len(self.registros)


class FakeEmpresasRepository:
    def __init__(self, estado="SC"):
        self.estado = estado

    def obter_estado(self, empresa_id):
        return self.estado


RES_NFE_XML = (
    '<resNFe xmlns="http://www.portalfiscal.inf.br/nfe">'
    "<chNFe>35260812345678000190550010000000011234567890</chNFe>"
    "<CNPJ>98765432000199</CNPJ>"
    "<dhEmi>2026-08-01T10:00:00-03:00</dhEmi>"
    "<vNF>100.00</vNF>"
    "<cSitNFe>1</cSitNFe>"
    "</resNFe>"
).encode("utf-8")


def _servico(client_respostas, ciencia=None, **overrides):
    class FakeClient:
        ciencias_enviadas: list[str] = []

        def __init__(self, *args, **kwargs):
            self._respostas = iter(client_respostas)

        def consultar(self, ultimo_nsu):
            return next(self._respostas)

        def enviar_ciencia_operacao(self, chave_acesso):
            FakeClient.ciencias_enviadas.append(chave_acesso)
            resultado = ciencia if ciencia is not None else ResultadoEvento(cstat=135, protocolo="891")
            if isinstance(resultado, Exception):
                raise resultado
            return resultado

    from app.services.sefaz.sefaz_distribuicao_service import SefazDistribuicaoService

    kwargs = {
        "certificado_service": FakeCertificadoService(),
        "nsu_repository": FakeNsuRepository(),
        "documentos_repository": FakeDocumentosRepository(),
        "eventos_repository": FakeEventosRepository(),
        "sync_log_repository": FakeSyncLogRepository(),
        "empresas_repository": FakeEmpresasRepository(),
        "client_factory": FakeClient,
    }
    kwargs.update(overrides)
    servico = SefazDistribuicaoService(**kwargs)
    servico.ciencias_enviadas = FakeClient.ciencias_enviadas
    FakeClient.ciencias_enviadas.clear()
    return servico


def test_cstat_137_para_sem_documentos_e_registra_sucesso():
    servico = _servico([RespostaDistribuicao(cstat=137, ultimo_nsu="10", max_nsu="10", documentos=[])])

    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert resultado.status == "sucesso"
    assert resultado.documentos_novos == 0
    assert servico.sync_log_repository.registros[0]["status"] == "sucesso"


def test_documento_novo_persistido_e_direcao_calculada():
    doc = DocumentoBruto(schema="resNFe", nsu="1", xml_bytes=RES_NFE_XML)
    servico = _servico(
        [
            RespostaDistribuicao(cstat=137, ultimo_nsu="1", max_nsu="1", documentos=[doc]),
        ]
    )

    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert resultado.documentos_novos == 1
    inserido = servico.documentos_repository.inseridos[0]
    assert inserido["direcao"] == "recebida"
    assert inserido["cnpj_emitente"] == "98765432000199"


def test_pagina_ate_cstat_137_apos_138():
    doc = DocumentoBruto(schema="resNFe", nsu="1", xml_bytes=RES_NFE_XML)
    servico = _servico(
        [
            RespostaDistribuicao(cstat=138, ultimo_nsu="1", max_nsu="10", documentos=[doc]),
            RespostaDistribuicao(cstat=137, ultimo_nsu="1", max_nsu="10", documentos=[]),
        ]
    )

    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert resultado.status == "sucesso"
    assert resultado.documentos_novos == 1


def test_cstat_656_marca_bloqueado_e_para():
    servico = _servico(
        [
            RespostaDistribuicao(
                cstat=656,
                ultimo_nsu="5",
                max_nsu="5",
                documentos=[],
                x_motivo="Rejeicao: Consumo Indevido.",
            )
        ]
    )

    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert resultado.status == "bloqueado"
    assert "656" in resultado.erro_detalhe or "indevido" in resultado.erro_detalhe
    assert "Consumo Indevido" in resultado.erro_detalhe


def test_idempotencia_reprocessar_mesmo_documento_nao_duplica():
    doc = DocumentoBruto(schema="resNFe", nsu="1", xml_bytes=RES_NFE_XML)
    documentos_repo = FakeDocumentosRepository()
    documentos_repo.chaves_existentes.add("35260812345678000190550010000000011234567890")

    servico = _servico(
        [RespostaDistribuicao(cstat=137, ultimo_nsu="1", max_nsu="1", documentos=[doc])],
        documentos_repository=documentos_repo,
    )

    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert resultado.documentos_novos == 0


def test_bloqueio_recente_impede_nova_consulta_sefaz():
    class FakeClientNuncaDeveriaSerChamado:
        def __init__(self, *args, **kwargs):
            pass

        def consultar(self, ultimo_nsu):
            raise AssertionError("nao deveria consultar a SEFAZ dentro da janela de bloqueio")

    nsu_repo = FakeNsuRepository(
        ultimo_nsu="157242",
        status_ultima_execucao="bloqueado",
        ultima_execucao_em=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    servico = _servico([], nsu_repository=nsu_repo, client_factory=FakeClientNuncaDeveriaSerChamado)

    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert resultado.status == "bloqueado"
    assert resultado.documentos_novos == 0
    assert "janela de espera" in resultado.erro_detalhe
    assert servico.sync_log_repository.registros[0]["status"] == "bloqueado"


def test_bloqueio_antigo_permite_nova_consulta_sefaz():
    nsu_repo = FakeNsuRepository(
        ultimo_nsu="157242",
        status_ultima_execucao="bloqueado",
        ultima_execucao_em=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    servico = _servico(
        [RespostaDistribuicao(cstat=137, ultimo_nsu="157242", max_nsu="157242", documentos=[])],
        nsu_repository=nsu_repo,
    )

    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert resultado.status == "sucesso"


def test_certificado_ausente_leva_excecao():
    from app.services.sefaz.sefaz_distribuicao_service import CertificadoAusenteError

    servico = _servico([], certificado_service=FakeCertificadoService(credenciais=None))

    with pytest.raises(CertificadoAusenteError):
        servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")


def test_erro_durante_consulta_marca_sync_log_como_erro_e_propaga():
    class FakeClientComErro:
        def __init__(self, *args, **kwargs):
            pass

        def consultar(self, ultimo_nsu):
            raise ConnectionError("timeout")

    servico = _servico([], client_factory=FakeClientComErro)

    with pytest.raises(ConnectionError):
        servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert servico.sync_log_repository.registros[0]["status"] == "erro"


def test_documento_novo_dispara_evento_celery_por_nome(monkeypatch):
    from app.services.sefaz import sefaz_distribuicao_service as modulo

    chamadas = []
    monkeypatch.setattr(
        modulo.celery_app,
        "send_task",
        lambda name, args, queue: chamadas.append((name, args, queue)),
    )

    doc = DocumentoBruto(schema="resNFe", nsu="1", xml_bytes=RES_NFE_XML)
    servico = _servico([RespostaDistribuicao(cstat=137, ultimo_nsu="1", max_nsu="1", documentos=[doc])])

    servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert chamadas == [
        (
            "sefaz_evento_documento_novo_task",
            [1, "35260812345678000190550010000000011234567890"],
            "sefaz",
        )
    ]


def test_falha_ao_disparar_evento_celery_nao_derruba_sincronizacao(monkeypatch):
    from app.services.sefaz import sefaz_distribuicao_service as modulo

    def _falha(*args, **kwargs):
        raise ConnectionError("broker indisponivel")

    monkeypatch.setattr(modulo.celery_app, "send_task", _falha)

    doc = DocumentoBruto(schema="resNFe", nsu="1", xml_bytes=RES_NFE_XML)
    servico = _servico([RespostaDistribuicao(cstat=137, ultimo_nsu="1", max_nsu="1", documentos=[doc])])

    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert resultado.status == "sucesso"
    assert resultado.documentos_novos == 1


CHAVE_RES_NFE = "35260812345678000190550010000000011234567890"

NFE_PROC_XML = (
    '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
    '<NFe><infNFe Id="NFe35260812345678000190550010000000011234567890">'
    "<ide><dhEmi>2026-08-01T10:00:00-03:00</dhEmi></ide>"
    "<emit><CNPJ>98765432000199</CNPJ></emit>"
    "<dest><CNPJ>12345678000190</CNPJ></dest>"
    "<total><ICMSTot><vNF>100.00</vNF></ICMSTot></total>"
    "</infNFe></NFe>"
    "<protNFe><infProt><chNFe>35260812345678000190550010000000011234567890</chNFe><nProt>1</nProt><cStat>100</cStat><xMotivo>Autorizado</xMotivo></infProt></protNFe>"
    "</nfeProc>"
).encode("utf-8")


def _sync_com_resumo(**kwargs):
    doc = DocumentoBruto(schema="resNFe", nsu="1", xml_bytes=RES_NFE_XML)
    servico = _servico(
        [RespostaDistribuicao(cstat=137, ultimo_nsu="1", max_nsu="1", documentos=[doc])],
        **kwargs,
    )
    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")
    return servico, resultado


def test_ciencia_automatica_enviada_para_recebida_com_resumo():
    servico, resultado = _sync_com_resumo()

    assert resultado.status == "sucesso"
    assert servico.ciencias_enviadas == [CHAVE_RES_NFE]
    assert servico.documentos_repository.manifestacoes == [(1, "ciencia")]
    evento = servico.eventos_repository.inseridos[0]
    assert evento["tipo_evento"] == "ciencia_operacao"
    assert evento["status"] == "registrado"
    assert evento["protocolo"] == "891"


def test_ciencia_duplicada_573_conta_como_registrada():
    servico, _ = _sync_com_resumo(ciencia=ResultadoEvento(cstat=573, x_motivo="Duplicidade de evento"))

    assert servico.documentos_repository.manifestacoes == [(1, "ciencia")]
    assert servico.eventos_repository.inseridos[0]["status"] == "registrado"


def test_ciencia_rejeitada_sai_da_fila_e_nao_derruba_sync():
    servico, resultado = _sync_com_resumo(ciencia=ResultadoEvento(cstat=494, x_motivo="Chave inexistente"))

    assert resultado.status == "sucesso"
    assert servico.documentos_repository.manifestacoes == [(1, "ciencia_rejeitada")]
    assert servico.eventos_repository.inseridos[0]["status"] == "rejeitado"


def test_ciencia_com_sefaz_indisponivel_mantem_pendente_e_sync_segue_sucesso():
    servico, resultado = _sync_com_resumo(ciencia=SefazIndisponivelError("timeout"))

    assert resultado.status == "sucesso"
    assert not hasattr(servico.documentos_repository, "manifestacoes")
    assert servico.eventos_repository.inseridos == []


def test_nfe_proc_de_chave_existente_completa_o_xml():
    doc = DocumentoBruto(schema="nfeProc", nsu="2", xml_bytes=NFE_PROC_XML)
    documentos_repo = FakeDocumentosRepository()
    documentos_repo.chaves_existentes.add(CHAVE_RES_NFE)
    servico = _servico(
        [RespostaDistribuicao(cstat=137, ultimo_nsu="2", max_nsu="2", documentos=[doc])],
        documentos_repository=documentos_repo,
    )

    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert resultado.documentos_novos == 0
    assert documentos_repo.xmls_completos == [(CHAVE_RES_NFE, NFE_PROC_XML)]
