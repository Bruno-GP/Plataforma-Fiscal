"""Fluxo OAuth2 (Authorization Code) para a API v2 da Conta Azul.

Endpoints e formato confirmados na documentacao oficial informada pelo usuario
(https://developers.contaazul.com/auth). Os paths de recursos de negocio
ficam em client.py e devem ser conferidos no portal OpenAPI antes do uso.
"""

from __future__ import annotations

import base64
import json
import logging
import secrets
import time
import urllib.parse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Optional

import httpx

logger = logging.getLogger("contaazul.auth")

AUTH_URL = "https://auth.contaazul.com/oauth2/authorize"
TOKEN_URL = "https://auth.contaazul.com/oauth2/token"

DEFAULT_TOKENS_PATH = Path(__file__).resolve().parent.parent / ".tokens.json"

# margem de seguranca antes do vencimento real do access_token
TOKEN_EXPIRY_LEEWAY_SECONDS = 60


class AuthError(Exception):
    """Erro de autenticacao/autorizacao junto a Conta Azul."""


class ReauthorizationRequired(AuthError):
    """refresh_token invalido/expirado: preciso repetir o fluxo `auth`."""


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str
    expires_in: int
    obtained_at: float
    token_type: str = "Bearer"
    scope: Optional[str] = None

    @property
    def expires_at(self) -> float:
        return self.obtained_at + self.expires_in

    @property
    def is_expired(self) -> bool:
        return time.time() >= (self.expires_at - TOKEN_EXPIRY_LEEWAY_SECONDS)

    def to_dict(self) -> dict:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_in": self.expires_in,
            "obtained_at": self.obtained_at,
            "token_type": self.token_type,
            "scope": self.scope,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TokenSet":
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data["expires_in"],
            obtained_at=data["obtained_at"],
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope"),
        )


class TokenStore:
    """Persiste o TokenSet em disco (fora do controle de versao)."""

    def __init__(self, path: Path = DEFAULT_TOKENS_PATH):
        self.path = path

    def load(self) -> Optional[TokenSet]:
        if not self.path.exists():
            return None
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return TokenSet.from_dict(data)

    def save(self, tokens: TokenSet) -> None:
        self.path.write_text(json.dumps(tokens.to_dict(), indent=2), encoding="utf-8")

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()


class _CallbackHandler(BaseHTTPRequestHandler):
    """Handler minimo que captura ?code=...&state=... do redirect_uri."""

    result: dict = {}

    def do_GET(self):  # noqa: N802 (nome exigido pelo BaseHTTPRequestHandler)
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        _CallbackHandler.result = {
            "code": params.get("code", [None])[0],
            "state": params.get("state", [None])[0],
            "error": params.get("error", [None])[0],
        }
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if _CallbackHandler.result.get("error"):
            body = "<h1>Falha na autorizacao</h1><p>Pode fechar esta aba.</p>"
        else:
            body = "<h1>Autorizado com sucesso</h1><p>Pode fechar esta aba e voltar ao terminal.</p>"
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):  # silencia log padrao do http.server
        return


def _wait_for_callback(host: str, port: int, path: str, timeout: int = 300) -> dict:
    """Sobe um servidor HTTP local, espera 1 requisicao no redirect_uri e derruba."""
    _CallbackHandler.result = {}
    server = HTTPServer((host, port), _CallbackHandler)
    server.timeout = timeout

    thread = Thread(target=server.handle_request, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    server.server_close()

    if not _CallbackHandler.result:
        raise AuthError(
            f"Timeout esperando callback OAuth2 em {host}:{port}{path} apos {timeout}s."
        )
    return _CallbackHandler.result


class ContaAzulAuth:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        token_store: Optional[TokenStore] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_store = token_store or TokenStore()
        self._http = http_client or httpx.Client(timeout=30)

    def _basic_auth_header(self) -> str:
        raw = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")

    def build_authorization_url(self, scope: Optional[str] = None) -> tuple[str, str]:
        """Retorna (url, state). Guarde o state para validar o callback."""
        state = secrets.token_urlsafe(24)
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        if scope:
            params["scope"] = scope
        url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
        return url, state

    def run_local_authorization_flow(self, scope: Optional[str] = None, timeout: int = 300) -> TokenSet:
        """Fluxo completo: abre URL de autorizacao, espera o callback local, troca o code."""
        url, expected_state = self.build_authorization_url(scope=scope)
        parsed_redirect = urllib.parse.urlparse(self.redirect_uri)
        host = parsed_redirect.hostname or "localhost"
        port = parsed_redirect.port or 80
        path = parsed_redirect.path or "/"

        logger.info("Acesse esta URL para autorizar: %s", url)
        print(f"Abra no navegador para autorizar:\n{url}\n")

        callback = _wait_for_callback(host, port, path, timeout=timeout)
        if callback.get("error"):
            raise AuthError(f"Autorizacao negada/erro no callback: {callback['error']}")
        if callback.get("state") != expected_state:
            raise AuthError("state retornado no callback nao confere (possivel CSRF).")
        code = callback.get("code")
        if not code:
            raise AuthError("Callback OAuth2 nao retornou 'code'.")

        return self.exchange_code_for_token(code)

    def run_manual_authorization_flow(self, scope: Optional[str] = None) -> TokenSet:
        """Alternativa quando o redirect_uri nao pode ser um endpoint local (ex: a
        conta sandbox obriga um redirect_uri fixo tipo https://contaazul.com).
        Usuario autoriza no navegador e cola o `code` (ou a URL final) de volta.
        """
        url, expected_state = self.build_authorization_url(scope=scope)
        print(f"Abra no navegador para autorizar:\n{url}\n")
        print(
            "Apos autorizar, voce sera redirecionado (pode cair numa pagina de erro/generica "
            "-- normal, o redirect_uri e so um destino fixo do sandbox). Copie da barra de "
            "enderecos a URL inteira ou so o valor do parametro 'code'."
        )
        resposta = input("Cole aqui: ").strip()
        code, state = self._parse_code_from_input(resposta)
        if state is not None and state != expected_state:
            raise AuthError("state retornado nao confere (possivel CSRF).")
        if not code:
            raise AuthError("Nao encontrei 'code' no que foi colado.")
        return self.exchange_code_for_token(code)

    @staticmethod
    def _parse_code_from_input(resposta: str) -> tuple[Optional[str], Optional[str]]:
        if "code=" in resposta:
            parsed = urllib.parse.urlparse(resposta)
            params = urllib.parse.parse_qs(parsed.query)
            return params.get("code", [None])[0], params.get("state", [None])[0]
        return resposta or None, None

    def exchange_code_for_token(self, code: str) -> TokenSet:
        response = self._http.post(
            TOKEN_URL,
            headers={
                "Authorization": self._basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
            },
        )
        return self._handle_token_response(response)

    def refresh_access_token(self, refresh_token: str) -> TokenSet:
        response = self._http.post(
            TOKEN_URL,
            headers={
                "Authorization": self._basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        if response.status_code in (400, 401):
            raise ReauthorizationRequired(
                "refresh_token invalido ou expirado. Rode `python main.py auth` novamente."
            )
        return self._handle_token_response(response)

    def _handle_token_response(self, response: httpx.Response) -> TokenSet:
        if response.status_code >= 400:
            logger.error("Erro ao obter token: status=%s body=%s", response.status_code, response.text)
            raise AuthError(f"Falha ao obter token (status {response.status_code}): {response.text}")
        payload = response.json()
        tokens = TokenSet(
            access_token=payload["access_token"],
            refresh_token=payload["refresh_token"],
            expires_in=payload.get("expires_in", 3600),
            obtained_at=time.time(),
            token_type=payload.get("token_type", "Bearer"),
            scope=payload.get("scope"),
        )
        self.token_store.save(tokens)
        return tokens

    def get_valid_access_token(self) -> str:
        """Retorna um access_token valido, renovando via refresh_token se preciso."""
        tokens = self.token_store.load()
        if tokens is None:
            raise ReauthorizationRequired(
                "Nenhum token salvo. Rode `python main.py auth` primeiro."
            )
        if tokens.is_expired:
            tokens = self.refresh_access_token(tokens.refresh_token)
        return tokens.access_token
