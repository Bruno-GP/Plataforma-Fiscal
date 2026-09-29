from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from app.repositories.sefaz.certificados_repository import CertificadosRepository
from app.services.nfe.empresa_service import normalizar_cnpj
from app.services.sefaz.crypto_service import decrypt_bytes, decrypt_text, encrypt_bytes, encrypt_text


class CertificadoInvalidoError(ValueError):
    pass


@dataclass(frozen=True)
class CertificadoStatus:
    ativo: bool
    cnpj_titular: str | None
    data_validade: date | None
    dias_restantes: int | None


class CertificadoService:
    def __init__(self, repository: CertificadosRepository | None = None) -> None:
        self.repository = repository or CertificadosRepository()

    def _extrair_data_validade(self, certificado: x509.Certificate) -> date:
        if hasattr(certificado, "not_valid_after_utc"):
            validade = certificado.not_valid_after_utc
        else:
            validade = certificado.not_valid_after

        if isinstance(validade, datetime):
            if validade.tzinfo is None:
                validade = validade.replace(tzinfo=timezone.utc)
            return validade.date()

        return validade

    def _extrair_cnpj_titular(self, certificado: x509.Certificate) -> str:
        atributos = certificado.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if not atributos:
            raise CertificadoInvalidoError("Certificado sem Common Name (CN) no titular.")

        cn = atributos[0].value.strip()
        partes = cn.rsplit(":", 1)
        if len(partes) != 2 or not partes[1].strip():
            raise CertificadoInvalidoError(
                "Certificado nao segue o padrao ICP-Brasil (CN esperado 'NOME:CNPJ')."
            )

        cnpj_titular = normalizar_cnpj(partes[1].strip())
        if not cnpj_titular:
            raise CertificadoInvalidoError("CNPJ do titular nao foi encontrado no certificado.")

        return cnpj_titular

    def _carregar_pfx(self, arquivo_pfx: bytes, senha: str) -> tuple[Any, x509.Certificate, list[x509.Certificate] | None]:
        try:
            chave, certificado, cadeias = pkcs12.load_key_and_certificates(
                arquivo_pfx,
                senha.encode("utf-8"),
            )
        except ValueError as exc:
            raise CertificadoInvalidoError(
                "Nao foi possivel abrir o certificado: senha incorreta ou arquivo .pfx/.p12 invalido."
            ) from exc

        if chave is None or certificado is None:
            raise CertificadoInvalidoError("Certificado .pfx/.p12 sem chave privada ou sem certificado.")

        return chave, certificado, cadeias

    def cadastrar(
        self,
        empresa_id: int,
        arquivo_pfx: bytes,
        senha: str,
        cnpj_esperado: str,
    ) -> CertificadoStatus:
        _, certificado, _ = self._carregar_pfx(arquivo_pfx, senha)

        data_validade = self._extrair_data_validade(certificado)
        if data_validade < datetime.now(timezone.utc).date():
            raise CertificadoInvalidoError(f"Certificado vencido em {data_validade.isoformat()}.")

        cnpj_titular = self._extrair_cnpj_titular(certificado)
        cnpj_esperado_normalizado = normalizar_cnpj(cnpj_esperado)
        if cnpj_titular != cnpj_esperado_normalizado:
            raise CertificadoInvalidoError(
                f"Certificado pertence ao CNPJ {cnpj_titular}, diferente da empresa logada."
            )

        self.repository.inserir(
            empresa_id=empresa_id,
            arquivo_certificado=encrypt_bytes(arquivo_pfx),
            senha_criptografada=encrypt_text(senha),
            cnpj_titular=cnpj_titular,
            data_validade=data_validade,
        )

        dias_restantes = (data_validade - datetime.now(timezone.utc).date()).days
        if dias_restantes < 0:
            dias_restantes = 0

        return CertificadoStatus(
            ativo=True,
            cnpj_titular=cnpj_titular,
            data_validade=data_validade,
            dias_restantes=dias_restantes,
        )

    def status(self, empresa_id: int) -> CertificadoStatus:
        registro = self.repository.get_ativo(empresa_id)
        if not registro:
            return CertificadoStatus(
                ativo=False,
                cnpj_titular=None,
                data_validade=None,
                dias_restantes=None,
            )

        data_validade = registro["data_validade"]
        dias_restantes = (data_validade - datetime.now(timezone.utc).date()).days
        if dias_restantes < 0:
            dias_restantes = 0

        return CertificadoStatus(
            ativo=True,
            cnpj_titular=registro.get("cnpj_titular"),
            data_validade=data_validade,
            dias_restantes=dias_restantes,
        )

    def obter_credenciais_descriptografadas(self, empresa_id: int) -> tuple[bytes, str] | None:
        registro = self.repository.get_ativo(empresa_id)
        if not registro:
            return None

        arquivo_certificado = registro["arquivo_certificado"]
        if hasattr(arquivo_certificado, "tobytes"):
            arquivo_certificado = arquivo_certificado.tobytes()
        elif not isinstance(arquivo_certificado, (bytes, bytearray)):
            arquivo_certificado = bytes(arquivo_certificado)

        return (
            decrypt_bytes(bytes(arquivo_certificado)),
            decrypt_text(registro["senha_criptografada"]),
        )
