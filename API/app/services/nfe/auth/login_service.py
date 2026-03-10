import hashlib
import hmac
import os
from dataclasses import dataclass
import logging
from contextlib import contextmanager

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
    empresa_nome: str
    tem_sped: bool

class LoginService:
    def __init__(self) -> None:
        config = carregar_config_postgres()

        self.conn_params = {
            "connect_timeout": 5,
        }
        
        
        if config.get("conninfo"):
            self.conn_params["conninfo"] = config["conninfo"]
        else:
            self.conn_params.update(
                {
                    "host": config["host"],
                    "port": config["port"],
                    "dbname": config["database"],
                    "user": config["user"],
                    "password": config["password"],
                }
            )

        if config.get("sslmode"):
            self.conn_params["sslmode"] = config["sslmode"]

    def _hash_senha(self, senha: str, salt: bytes) -> str:
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode("utf-8"),
            salt,
            120_000,
        )
        return digest.hex()

    def _verificar_senha(self, senha: str, senha_armazenada: str) -> bool:
        if not senha_armazenada:
            return False

        if ":" not in senha_armazenada:
            return hmac.compare_digest(senha_armazenada, senha)

        salt_hex, digest_armazenado = senha_armazenada.split(":", 1)
        
        try:
            salt = bytes.fromhex(salt_hex)
        except ValueError:
            return False
        digest = self._hash_senha(senha, salt)
        return hmac.compare_digest(digest, digest_armazenado)
    
    def _nome_empresa_completo(self, nome: str | None) -> str:
        return nome.strip() if nome else ""

    def _ensure_tem_sped_column(self, cur) -> None:
        cur.execute(
            """
            ALTER TABLE public.empresas
            ADD COLUMN IF NOT EXISTS tem_sped BOOLEAN NOT NULL DEFAULT FALSE;
            """
        )

    def registrar(self, empresa_nome: str, email: str, senha: str, cnpj: str, tem_sped: bool = False) -> LoginResult:
        cnpj_normalizado = normalizar_cnpj(cnpj)
        empresa_nome_normalizado = empresa_nome.strip()
        if len(empresa_nome_normalizado) < 2:
            raise ValueError("Informe um nome de empresa válido.")
        email_normalizado = email.lower()
        logger.debug("Iniciando registro de login para %s", email_normalizado)

        with psycopg.connect(**self.conn_params) as conn:
            with conn.cursor() as cur:
                self._ensure_tem_sped_column(cur)
                cur.execute(
                    """
                    SELECT id, cnpj, nome
                    FROM public.empresas
                    WHERE cnpj = %s;
                    """,
                    (cnpj_normalizado,),
                )
                empresa = cur.fetchone()

                if not empresa:
                    logger.info(
                        "Empresa não encontrada para CNPJ %s. Criando cadastro automaticamente.",
                        cnpj_normalizado,
                    )
                    
                    cur.execute(
                        """
                        INSERT INTO public.empresas (cnpj, nome, tem_sped)
                        VALUES (%s, %s, %s)
                        RETURNING id, cnpj, nome;
                        """,
                        (cnpj_normalizado, empresa_nome_normalizado, tem_sped),
                    )
                    empresa = cur.fetchone()
                else:
                    
                    cur.execute(
                        """
                        UPDATE public.empresas
                        SET nome = %s,
                            tem_sped = %s
                        WHERE id = %s;
                        """,
                        (empresa_nome_normalizado, tem_sped, empresa[0]),
                    )

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
                senha_armazenada = f"{salt.hex()}:{senha_hash}"

                cur.execute(
                    """
                    INSERT INTO public.login (empresa_id, cnpj, email, senha)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        empresa[0],
                        cnpj_normalizado,
                        email_normalizado,
                        senha_armazenada
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
            empresa_nome=self._nome_empresa_completo(empresa[2]),
            tem_sped=tem_sped,
        )

    def autenticar(self, email: str, senha: str) -> LoginResult:
        email_normalizado = email.lower()
        logger.debug("Iniciando autenticação para %s", email_normalizado)
        
        with psycopg.connect(**self.conn_params) as conn:
            with conn.cursor() as cur:
                self._ensure_tem_sped_column(cur)
                cur.execute(
                    """
                    SELECT login.id,
                           login.empresa_id,
                           login.cnpj,
                           login.email,
                           login.senha,
                           empresas.nome,
                           COALESCE(empresas.tem_sped, false)
                    FROM public.login AS login
                    JOIN public.empresas AS empresas ON empresas.id = login.empresa_id
                    WHERE login.email = %s;
                    """,
                    (email_normalizado,),
                )
                login = cur.fetchone()

                if not login:
                    raise ValueError("Credenciais inválidas.")

                (
                    login_id,
                    empresa_id,
                    cnpj,
                    email_db,
                    senha_armazenada,
                    empresa_nome,
                    tem_sped,
                ) = login


                if not self._verificar_senha(senha, senha_armazenada):
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
                empresa_nome=self._nome_empresa_completo(empresa_nome),
                tem_sped=bool(tem_sped),
            )