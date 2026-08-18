from datetime import datetime, timedelta, timezone

import pytest

from app.services.sefaz.distribuicao_dfe_client import DocumentoBruto, RespostaDistribuicao


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


def _servico(client_respostas, **overrides):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            self._respostas = iter(client_respostas)

        def consultar(self, ultimo_nsu):
            return next(self._respostas)

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
    return SefazDistribuicaoService(**kwargs)


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
    servico = _servico([RespostaDistribuicao(cstat=656, ultimo_nsu="5", max_nsu="5", documentos=[])])

    resultado = servico.sincronizar_empresa(empresa_id=1, cnpj_empresa="12345678000190")

    assert resultado.status == "bloqueado"
    assert "656" in resultado.erro_detalhe or "indevido" in resultado.erro_detalhe


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
