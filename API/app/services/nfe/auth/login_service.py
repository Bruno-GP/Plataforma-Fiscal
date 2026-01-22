import hashlib
import hmac
import os
from dataclasses import dataclass

import psycopg

from app.services.nfe.postres_config import carregar_config_postgres
from app.services.nfe.empresa_service import normalizar_cnpj


@dataclass
class LoginResult:
    login_id: int
    empresa_id: int
    cnpj: str
    email: str


class LoginService:
    def __init__(self) -> None:
        config = carregar_config_postgres()

        self.conn_params = {
            "host": config["host"],
            "port": config["port"],
            "dbname": config["database"],
            "user": config["user"],
            "password": config["password"],
            "connect_timeout": 5,
        }

    def _hash_senha(self, senha: str, salt: bytes) -> str:
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode("utf-8"),
            salt,
            120_000,
        )
        return digest.hex()

    def _verificar_senha(self, senha: str, senha_hash: str, senha_salt: str) -> bool:
        salt = bytes.fromhex(senha_salt)
        digest = self._hash_senha(senha, salt)
        return hmac.compare_digest(digest, senha_hash)

    def registrar(self, email: str, senha: str, cnpj: str) -> LoginResult:
        cnpj_normalizado = normalizar_cnpj(cnpj)

        with psycopg.connect(**self.conn_params) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, cnpj
                    FROM public.empresas
                    WHERE cnpj = %s;
                    """,
                    (cnpj_normalizado,),
                )
                empresa = cur.fetchone()

                if not empresa:
                    raise ValueError("CNPJ não encontrado no cadastro de empresas.")

                cur.execute(
                    """
                    SELECT id
                    FROM public.login
                    WHERE email = %s;
                    """,
                    (email.lower(),),
                )
                if cur.fetchone():
                    raise ValueError("E-mail já cadastrado.")

                salt = os.urandom(16)
                senha_hash = self._hash_senha(senha, salt)

                cur.execute(
                    """
                    INSERT INTO public.login (empresa_id, cnpj, email, senha_hash, senha_salt)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        empresa[0],
                        cnpj_normalizado,
                        email.lower(),
                        senha_hash,
                        salt.hex(),
                    ),
                )
                login_id = cur.fetchone()[0]

        return LoginResult(
            login_id=login_id,
            empresa_id=empresa[0],
            cnpj=cnpj_normalizado,
            email=email.lower(),
        )

    def autenticar(self, email: str, senha: str) -> LoginResult:
        with psycopg.connect(**self.conn_params) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, empresa_id, cnpj, email, senha_hash, senha_salt
                    FROM public.login
                    WHERE email = %s;
                    """,
                    (email.lower(),),
                )
                login = cur.fetchone()

        if not login:
            raise ValueError("Credenciais inválidas.")

        login_id, empresa_id, cnpj, email_db, senha_hash, senha_salt = login

        if not self._verificar_senha(senha, senha_hash, senha_salt):
            raise ValueError("Credenciais inválidas.")

        return LoginResult(
            login_id=login_id,
            empresa_id=empresa_id,
            cnpj=cnpj,
            email=email_db,
        )