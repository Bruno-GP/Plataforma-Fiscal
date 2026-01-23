import hashlib
import hmac
import os
from dataclasses import dataclass
import logging

import psycopg

from app.services.nfe.postres_config import carregar_config_postgres
from app.services.nfe.empresa_service import normalizar_cnpj

logger = logging.getLogger("LoginService")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
handler.setFormatter(formatter)
logger.addHandler(handler)


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
        try:
            salt = bytes.fromhex(senha_salt)
        except ValueError:
            return False
        digest = self._hash_senha(senha, salt)
        return hmac.compare_digest(digest, senha_hash)

    def registrar(self, email: str, senha: str, cnpj: str) -> LoginResult:
        cnpj_normalizado = normalizar_cnpj(cnpj)
        email_normalizado = email.lower()
        logger.debug("Iniciando registro de login para %s", email_normalizado)

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
                    logger.warning(
                        "Empresa não encontrada para CNPJ %s durante cadastro",
                        cnpj_normalizado,
                    )
                    
                    raise ValueError("CNPJ não encontrado no cadastro de empresas.")

                cur.execute(
                    """
                    SELECT id
                    FROM public.login
                    WHERE email = %s;
                    """,
                    (email_normalizado,),
                )
                if cur.fetchone():
                    logger.warning(
                        "Tentativa de cadastro com e-mail já existente: %s",
                        email_normalizado,
                    )
                    
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
                        email_normalizado,
                        senha_hash,
                        salt.hex(),
                    ),
                )
                login_id = cur.fetchone()[0]
                
        logger.info(
            "Login cadastrado com sucesso para %s (empresa_id=%s)",
            email_normalizado,
            empresa[0],
        )

        return LoginResult(
            login_id=login_id,
            empresa_id=empresa[0],
            cnpj=cnpj_normalizado,
            email=email_normalizado,
        )

    def autenticar(self, email: str, senha: str) -> LoginResult:
        email_normalizado = email.lower()
        logger.debug("Iniciando autenticação para %s", email_normalizado)
        
        with psycopg.connect(**self.conn_params) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, empresa_id, cnpj, email, senha_hash, senha_salt
                    FROM public.login
                    WHERE email = %s;
                    """,
                    (email_normalizado,),
                )
                login = cur.fetchone()

        if not login:
            logger.warning(
                "Falha de autenticação: e-mail não encontrado (%s)",
                email_normalizado,
            )
            
            raise ValueError("Credenciais inválidas.")

        login_id, empresa_id, cnpj, email_db, senha_hash, senha_salt = login

        if not self._verificar_senha(senha, senha_hash, senha_salt):
            logger.warning(
                "Falha de autenticação: senha inválida para %s",
                email_normalizado,
            )
            
            raise ValueError("Credenciais inválidas.")
        
        logger.info(
            "Autenticação concluída para %s (empresa_id=%s)",
            email_db,
            empresa_id,
        )

        return LoginResult(
            login_id=login_id,
            empresa_id=empresa_id,
            cnpj=cnpj,
            email=email_db,
        )