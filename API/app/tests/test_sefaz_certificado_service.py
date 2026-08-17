from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID


def _gerar_pfx(cn: str, dias_validade: int = 365) -> tuple[bytes, str]:
    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    agora = datetime.now(timezone.utc)
    if dias_validade < 0:
        not_valid_before = agora + timedelta(days=dias_validade - 2)
        not_valid_after = agora + timedelta(days=dias_validade)
    else:
        not_valid_before = agora - timedelta(days=1)
        not_valid_after = agora + timedelta(days=dias_validade)

    certificado = (
        x509.CertificateBuilder()
        .subject_name(nome)
        .issuer_name(nome)
        .public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_valid_before)
        .not_valid_after(not_valid_after)
        .sign(chave, hashes.SHA256())
    )
    senha = "senha-teste-123"
    pfx_bytes = pkcs12.serialize_key_and_certificates(
        name=b"certificado-teste",
        key=chave,
        cert=certificado,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(senha.encode("utf-8")),
    )
    return pfx_bytes, senha


class FakeCertificadosRepository:
    def __init__(self):
        self.inserido = None
        self.ativo = None

    def inserir(self, **kwargs):
        self.inserido = kwargs
        self.ativo = {**kwargs, "ativo": True}
        return 1

    def get_ativo(self, empresa_id):
        return self.ativo


def test_cadastrar_certificado_valido(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", "kAcqlvvVAAvv1pIbFOfR1CH8Aq2KgV1zqvvz4XjPz6c=")
    from app.services.sefaz.certificado_service import CertificadoService

    pfx_bytes, senha = _gerar_pfx("EMPRESA TESTE LTDA:12345678000190")
    repo = FakeCertificadosRepository()
    servico = CertificadoService(repository=repo)

    resultado = servico.cadastrar(
        empresa_id=1,
        arquivo_pfx=pfx_bytes,
        senha=senha,
        cnpj_esperado="12345678000190",
    )

    assert resultado.ativo is True
    assert resultado.cnpj_titular == "12345678000190"
    assert repo.inserido["cnpj_titular"] == "12345678000190"
    assert repo.inserido["arquivo_certificado"] != pfx_bytes
    assert repo.inserido["senha_criptografada"] != senha


def test_cadastrar_senha_incorreta_falha(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", "kAcqlvvVAAvv1pIbFOfR1CH8Aq2KgV1zqvvz4XjPz6c=")
    from app.services.sefaz.certificado_service import CertificadoInvalidoError, CertificadoService

    pfx_bytes, _ = _gerar_pfx("EMPRESA TESTE LTDA:12345678000190")
    servico = CertificadoService(repository=FakeCertificadosRepository())

    with pytest.raises(CertificadoInvalidoError, match="senha incorreta"):
        servico.cadastrar(
            empresa_id=1,
            arquivo_pfx=pfx_bytes,
            senha="senha-errada",
            cnpj_esperado="12345678000190",
        )


def test_cadastrar_certificado_vencido_falha(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", "kAcqlvvVAAvv1pIbFOfR1CH8Aq2KgV1zqvvz4XjPz6c=")
    from app.services.sefaz.certificado_service import CertificadoInvalidoError, CertificadoService

    pfx_bytes, senha = _gerar_pfx("EMPRESA TESTE LTDA:12345678000190", dias_validade=-10)
    servico = CertificadoService(repository=FakeCertificadosRepository())

    with pytest.raises(CertificadoInvalidoError, match="vencido"):
        servico.cadastrar(
            empresa_id=1,
            arquivo_pfx=pfx_bytes,
            senha=senha,
            cnpj_esperado="12345678000190",
        )


def test_cadastrar_cnpj_do_certificado_diferente_da_empresa_falha(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", "kAcqlvvVAAvv1pIbFOfR1CH8Aq2KgV1zqvvz4XjPz6c=")
    from app.services.sefaz.certificado_service import CertificadoInvalidoError, CertificadoService

    pfx_bytes, senha = _gerar_pfx("EMPRESA TESTE LTDA:12345678000190")
    servico = CertificadoService(repository=FakeCertificadosRepository())

    with pytest.raises(CertificadoInvalidoError, match="CNPJ"):
        servico.cadastrar(
            empresa_id=1,
            arquivo_pfx=pfx_bytes,
            senha=senha,
            cnpj_esperado="98765432000199",
        )


def test_status_sem_certificado_retorna_inativo():
    from app.services.sefaz.certificado_service import CertificadoService

    servico = CertificadoService(repository=FakeCertificadosRepository())
    resultado = servico.status(empresa_id=1)

    assert resultado.ativo is False
    assert resultado.cnpj_titular is None


def test_obter_credenciais_descriptografadas_roundtrip(monkeypatch):
    monkeypatch.setenv("SEFAZ_CERT_ENCRYPTION_KEY", "kAcqlvvVAAvv1pIbFOfR1CH8Aq2KgV1zqvvz4XjPz6c=")
    from app.services.sefaz.certificado_service import CertificadoService

    pfx_bytes, senha = _gerar_pfx("EMPRESA TESTE LTDA:12345678000190")
    repo = FakeCertificadosRepository()
    servico = CertificadoService(repository=repo)
    servico.cadastrar(
        empresa_id=1,
        arquivo_pfx=pfx_bytes,
        senha=senha,
        cnpj_esperado="12345678000190",
    )

    credenciais = servico.obter_credenciais_descriptografadas(empresa_id=1)
    assert credenciais == (pfx_bytes, senha)


def test_obter_credenciais_sem_certificado_retorna_none():
    from app.services.sefaz.certificado_service import CertificadoService

    servico = CertificadoService(repository=FakeCertificadosRepository())
    assert servico.obter_credenciais_descriptografadas(empresa_id=1) is None
