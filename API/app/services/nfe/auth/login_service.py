import hashlib
import hmac
import logging
import os
import re
import time
from threading import Lock
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import psycopg

from app.core.audit import log_security_event
from app.core.config import (
    get_login_lockout_minutes,
    get_login_max_failed_attempts,
    get_login_success_cache_ttl_seconds,
    get_password_min_length,
)
from app.services.nfe.empresa_service import normalizar_cnpj
from app.services.nfe.postres_config import carregar_config_postgres

logger = logging.getLogger("LoginService")
logger.setLevel(logging.INFO)


def _normalizar_localidade(valor: str | None) -> str | None:
    texto = (valor or "").strip()
    return texto or None


@dataclass
class LoginResult:
    login_id: int
    empresa_id: int
    cnpj: str
    email: str
    empresa_nome: str
    tem_sped: bool


class LoginService:
    _schema_lock = Lock()
    _schema_ensured = False
    _required_columns_by_table = {
        "empresas": {"id", "cnpj", "nome", "tem_sped", "estado", "cidade", "municipio_id", "codigo_ibge"},
        "login": {
            "id",
            "empresa_id",
            "cnpj",
            "email",
            "senha",
            "criado_em",
            "tentativas_falhas",
            "bloqueado_ate",
            "ultimo_login_em",
        },
    }
    _auth_cache_lock = Lock()
    _auth_refresh_lock = Lock()
    _auth_cache: dict[str, tuple[float, LoginResult]] = {}
    _auth_cache_maxsize = 128

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

        self._ensure_base_schema_once()

    def _ensure_base_schema_once(self) -> None:
        if LoginService._schema_ensured:
            return

        with LoginService._schema_lock:
            if LoginService._schema_ensured:
                return
            with psycopg.connect(**self.conn_params) as conn:
                self._validate_base_schema(conn)
            LoginService._schema_ensured = True

    def _validate_base_schema(self, conn: psycopg.Connection) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = ANY(%s)
                """,
                (list(self._required_columns_by_table),),
            )
            existing_columns: dict[str, set[str]] = {
                table_name: set()
                for table_name in self._required_columns_by_table
            }
            for table_name, column_name in cur.fetchall():
                existing_columns[str(table_name)].add(str(column_name))

        missing_parts = []
        for table_name, required_columns in self._required_columns_by_table.items():
            missing_columns = sorted(required_columns - existing_columns[table_name])
            if missing_columns:
                missing_parts.append(f"{table_name}: {', '.join(missing_columns)}")

        if missing_parts:
            raise RuntimeError(
                "Schema de autenticacao incompleto. Execute as migrations Alembic. "
                f"Colunas ausentes em public: {'; '.join(missing_parts)}."
            )

    def _validar_forca_senha(self, senha: str) -> None:
        min_length = get_password_min_length()
        if len(senha) < min_length:
            raise ValueError(f"A senha deve ter no mínimo {min_length} caracteres.")
        if not re.search(r"[A-Z]", senha):
            raise ValueError("A senha deve conter pelo menos uma letra maiúscula.")
        if not re.search(r"[a-z]", senha):
            raise ValueError("A senha deve conter pelo menos uma letra minúscula.")
        if not re.search(r"\d", senha):
            raise ValueError("A senha deve conter pelo menos um número.")
        if not re.search(r"[^A-Za-z0-9]", senha):
            raise ValueError("A senha deve conter pelo menos um caractere especial.")

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

    def _auth_cache_key(self, email: str, senha: str) -> str:
        return hashlib.sha256(f"{email}\0{senha}".encode("utf-8")).hexdigest()

    def _get_cached_auth(self, email: str, senha: str) -> LoginResult | None:
        ttl_seconds = get_login_success_cache_ttl_seconds()
        if ttl_seconds <= 0:
            return None

        key = self._auth_cache_key(email, senha)
        now = time.monotonic()

        with LoginService._auth_cache_lock:
            cached = LoginService._auth_cache.get(key)
            if not cached:
                return None

            expires_at, result = cached
            if expires_at <= now:
                LoginService._auth_cache.pop(key, None)
                return None

            return result

    def _set_cached_auth(self, email: str, senha: str, result: LoginResult) -> None:
        ttl_seconds = get_login_success_cache_ttl_seconds()
        if ttl_seconds <= 0:
            return

        key = self._auth_cache_key(email, senha)
        with LoginService._auth_cache_lock:
            LoginService._auth_cache[key] = (time.monotonic() + ttl_seconds, result)
            if len(LoginService._auth_cache) > LoginService._auth_cache_maxsize:
                oldest_key = next(iter(LoginService._auth_cache))
                LoginService._auth_cache.pop(oldest_key, None)

    def _nome_empresa_completo(self, nome: str | None) -> str:
        return nome.strip() if nome else ""

    def _registrar_falha_login(self, conn: psycopg.Connection, login_id: int, email: str) -> None:
        max_attempts = get_login_max_failed_attempts()
        lockout_minutes = get_login_lockout_minutes()

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.login
                SET tentativas_falhas = COALESCE(tentativas_falhas, 0) + 1,
                    bloqueado_ate = CASE
                        WHEN COALESCE(tentativas_falhas, 0) + 1 >= %s
                            THEN NOW() + (%s * INTERVAL '1 minute')
                        ELSE bloqueado_ate
                    END
                WHERE id = %s
                RETURNING tentativas_falhas, bloqueado_ate
                """,
                (max_attempts, lockout_minutes, login_id),
            )
            row = cur.fetchone()
        conn.commit()

        log_security_event(
            "login_failed",
            outcome="rejected",
            email=email,
            login_id=login_id,
            reason="invalid_credentials",
        )

        if row and row[0] >= max_attempts and row[1]:
            blocked_until = row[1].astimezone(timezone.utc).isoformat()
            raise ValueError(
                f"Muitas tentativas inválidas. Tente novamente após {blocked_until}."
            )

        raise ValueError("Credenciais inválidas.")

    def _resetar_falhas_login(
        self,
        conn: psycopg.Connection,
        login_id: int,
        tentativas_falhas: int,
        ultimo_login_em: datetime | None,
    ) -> None:
        if ultimo_login_em is not None and ultimo_login_em.tzinfo is None:
            ultimo_login_em = ultimo_login_em.replace(tzinfo=timezone.utc)

        atualizacao_recente = (
            ultimo_login_em is not None
            and ultimo_login_em > datetime.now(timezone.utc) - timedelta(minutes=1)
        )
        if tentativas_falhas == 0 and atualizacao_recente:
            return

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.login
                SET tentativas_falhas = 0,
                    bloqueado_ate = NULL,
                    ultimo_login_em = NOW()
                WHERE id = %s
                """,
                (login_id,),
            )
        conn.commit()

    def registrar(
        self,
        empresa_nome: str,
        email: str,
        senha: str,
        cnpj: str,
        tem_sped: bool = False,
        estado: str | None = None,
        cidade: str | None = None,
    ) -> LoginResult:
        cnpj_normalizado = normalizar_cnpj(cnpj)
        empresa_nome_normalizado = empresa_nome.strip()
        estado_normalizado = _normalizar_localidade(estado)
        cidade_normalizada = _normalizar_localidade(cidade)
        if len(empresa_nome_normalizado) < 2:
            raise ValueError("Informe um nome de empresa válido.")
        self._validar_forca_senha(senha)
        email_normalizado = email.lower().strip()
        logger.debug("Iniciando registro de login para %s", email_normalizado)

        with psycopg.connect(**self.conn_params) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, cnpj, nome, estado, cidade
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
                        INSERT INTO public.empresas (cnpj, nome, tem_sped, estado, cidade)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id, cnpj, nome, estado, cidade;
                        """,
                        (
                            cnpj_normalizado,
                            empresa_nome_normalizado,
                            tem_sped,
                            estado_normalizado,
                            cidade_normalizada,
                        ),
                    )
                    empresa = cur.fetchone()
                else:
                    cur.execute(
                        """
                        UPDATE public.empresas
                        SET nome = %s,
                            tem_sped = %s,
                            estado = COALESCE(%s, estado),
                            cidade = COALESCE(%s, cidade)
                        WHERE id = %s;
                        """,
                        (
                            empresa_nome_normalizado,
                            tem_sped,
                            estado_normalizado,
                            cidade_normalizada,
                            empresa[0],
                        ),
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
                        senha_armazenada,
                    ),
                )
                login_id = cur.fetchone()[0]
            conn.commit()

        log_security_event(
            "user_registered",
            outcome="success",
            email=email_normalizado,
            empresa_id=empresa[0],
            cnpj=cnpj_normalizado,
            login_id=login_id,
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
        email_normalizado = email.lower().strip()
        logger.debug("Iniciando autenticação para %s", email_normalizado)

        cached = self._get_cached_auth(email_normalizado, senha)
        if cached:
            return cached

        with LoginService._auth_refresh_lock:
            cached = self._get_cached_auth(email_normalizado, senha)
            if cached:
                return cached

            return self._autenticar_sem_cache(email_normalizado, senha)

    def _autenticar_sem_cache(self, email_normalizado: str, senha: str) -> LoginResult:
        with psycopg.connect(**self.conn_params) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT login.id,
                           login.empresa_id,
                           login.cnpj,
                           login.email,
                           login.senha,
                           login.bloqueado_ate,
                           login.tentativas_falhas,
                           login.ultimo_login_em,
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
                    log_security_event(
                        "login_failed",
                        outcome="rejected",
                        email=email_normalizado,
                        reason="user_not_found",
                    )
                    raise ValueError("Credenciais inválidas.")

                (
                    login_id,
                    empresa_id,
                    cnpj,
                    email_db,
                    senha_armazenada,
                    bloqueado_ate,
                    tentativas_falhas,
                    ultimo_login_em,
                    empresa_nome,
                    tem_sped,
                ) = login

                if bloqueado_ate and bloqueado_ate > datetime.now(timezone.utc):
                    blocked_until = bloqueado_ate.astimezone(timezone.utc).isoformat()
                    log_security_event(
                        "login_blocked",
                        outcome="rejected",
                        email=email_db,
                        login_id=login_id,
                        empresa_id=empresa_id,
                        cnpj=cnpj,
                        reason="temporary_lockout",
                    )
                    raise ValueError(
                        f"Muitas tentativas inválidas. Tente novamente após {blocked_until}."
                    )

                if not self._verificar_senha(senha, senha_armazenada):
                    self._registrar_falha_login(conn, login_id, email_db)

            self._resetar_falhas_login(conn, login_id, tentativas_falhas or 0, ultimo_login_em)
            log_security_event(
                "login_succeeded",
                outcome="success",
                email=email_db,
                login_id=login_id,
                empresa_id=empresa_id,
                cnpj=cnpj,
            )

            result = LoginResult(
                login_id=login_id,
                empresa_id=empresa_id,
                cnpj=cnpj,
                email=email_db,
                empresa_nome=self._nome_empresa_completo(empresa_nome),
                tem_sped=bool(tem_sped),
            )
            self._set_cached_auth(email_normalizado, senha, result)
            return result
