"""Cliente HTTP para a API v2 da Conta Azul.

Paths, parametros e nomes de campo abaixo foram confirmados diretamente contra
o OpenAPI real de cada area (baixado via
https://developers.contaazul.com/_bundle/docs/<pagina>.json?download):
sales-apis-openapi, financial-apis-openapi, open-api-person.
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .auth import ContaAzulAuth, AuthError
from .models import (
    Categoria,
    CentroCusto,
    Cliente,
    ContaPagar,
    ContaReceber,
    Venda,
    VendaDetalhada,
)

logger = logging.getLogger("contaazul.client")

BASE_URL = "https://api-v2.contaazul.com"

ENDPOINTS = {
    "vendas": "/v1/venda/busca",
    "pessoas": "/v1/pessoas",
    "categorias": "/v1/categorias",
    "centros_custo": "/v1/centro-de-custo",
    "contas_receber": "/v1/financeiro/eventos-financeiros/contas-a-receber/buscar",
    "contas_pagar": "/v1/financeiro/eventos-financeiros/contas-a-pagar/buscar",
}

PAGE_PARAM = "pagina"
PAGE_SIZE_PARAM = "tamanho_pagina"
DEFAULT_PAGE_SIZE = 100

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class ApiError(Exception):
    """Erro retornado pela API da Conta Azul (status >= 400 nao retentavel)."""

    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"Conta Azul API respondeu {status_code}: {payload}")


class _RetryableApiError(Exception):
    """Erro transitorio (429/5xx) — sinaliza ao tenacity para tentar de novo."""

    def __init__(self, response: httpx.Response):
        self.response = response
        super().__init__(f"status {response.status_code}")


def _extract_items(payload) -> list[dict]:
    """Normaliza a lista de itens da pagina. A maioria dos endpoints usa
    'itens', mas /v1/pessoas e /v1/centro-de-custo usam 'items' (em ingles)."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("itens", "items", "dados", "data", "content", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    raise ApiError(200, f"Formato de resposta paginada inesperado: {payload!r}")


class ContaAzulClient:
    def __init__(
        self,
        auth: ContaAzulAuth,
        base_url: str = BASE_URL,
        http_client: Optional[httpx.Client] = None,
    ):
        self.auth = auth
        self.base_url = base_url
        self._http = http_client or httpx.Client(timeout=30)

    def close(self) -> None:
        self._http.close()

    @retry(
        retry=retry_if_exception_type(_RetryableApiError),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _do_request(self, method: str, url: str, params: dict, access_token: str) -> httpx.Response:
        started = time.monotonic()
        response = self._http.request(
            method,
            url,
            params=params,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        elapsed_ms = (time.monotonic() - started) * 1000
        logger.info(
            "conta_azul_request endpoint=%s status=%s elapsed_ms=%.1f",
            url,
            response.status_code,
            elapsed_ms,
        )
        if response.status_code in RETRYABLE_STATUS:
            raise _RetryableApiError(response)
        return response

    def _request_json(self, path: str, params: dict) -> dict:
        url = f"{self.base_url}{path}"
        access_token = self.auth.get_valid_access_token()

        try:
            response = self._do_request("GET", url, params, access_token)
        except _RetryableApiError as exc:
            logger.error(
                "conta_azul_request_failed endpoint=%s status=%s body=%s",
                url,
                exc.response.status_code,
                exc.response.text,
            )
            raise ApiError(exc.response.status_code, exc.response.text) from exc

        if response.status_code == 401:
            raise AuthError(f"Token rejeitado (401) em {url}. Access token invalido ou revogado.")
        if response.status_code == 404:
            logger.error("conta_azul_endpoint_not_found endpoint=%s body=%s", url, response.text)
            raise ApiError(404, response.text)
        if response.status_code >= 400:
            logger.error(
                "conta_azul_request_error endpoint=%s status=%s body=%s",
                url,
                response.status_code,
                response.text,
            )
            raise ApiError(response.status_code, response.text)

        return response.json()

    def _get(self, resource_key: str, params: dict) -> list[dict]:
        return _extract_items(self._request_json(ENDPOINTS[resource_key], params))

    def obter_venda_por_id(self, id: str) -> VendaDetalhada:
        """GET /v1/venda/{id} — venda completa (cliente, vendedor, natureza de
        operacao, contrato, evento financeiro). `id` aceita legacy id ou uuid."""
        payload = self._request_json(f"/v1/venda/{id}", {})
        return VendaDetalhada(**payload, raw=payload)

    def listar_vendas(self, data_inicio: date, data_fim: date, pagina: int = 1) -> list[Venda]:
        items = self._get(
            "vendas",
            {
                "data_inicio": data_inicio.isoformat(),
                "data_fim": data_fim.isoformat(),
                PAGE_PARAM: pagina,
                PAGE_SIZE_PARAM: DEFAULT_PAGE_SIZE,
            },
        )
        return [Venda(**item, raw=item) for item in items]

    def listar_pessoas(self, pagina: int = 1) -> list[Cliente]:
        items = self._get("pessoas", {PAGE_PARAM: pagina, PAGE_SIZE_PARAM: DEFAULT_PAGE_SIZE})
        return [Cliente(**item, raw=item) for item in items]

    def listar_categorias(self, pagina: int = 1) -> list[Categoria]:
        items = self._get(
            "categorias",
            {
                PAGE_PARAM: pagina,
                PAGE_SIZE_PARAM: DEFAULT_PAGE_SIZE,
                "permite_apenas_filhos": False,
            },
        )
        return [Categoria(**item, raw=item) for item in items]

    def listar_centro_de_custo(self, pagina: int = 1) -> list[CentroCusto]:
        items = self._get("centros_custo", {PAGE_PARAM: pagina, PAGE_SIZE_PARAM: DEFAULT_PAGE_SIZE})
        return [CentroCusto(**item, raw=item) for item in items]

    def listar_contas_a_receber(self, data_inicio: date, data_fim: date, pagina: int = 1) -> list[ContaReceber]:
        items = self._get(
            "contas_receber",
            {
                "data_vencimento_de": data_inicio.isoformat(),
                "data_vencimento_ate": data_fim.isoformat(),
                PAGE_PARAM: pagina,
                PAGE_SIZE_PARAM: DEFAULT_PAGE_SIZE,
            },
        )
        return [ContaReceber(**item, raw=item) for item in items]

    def listar_contas_a_pagar(self, data_inicio: date, data_fim: date, pagina: int = 1) -> list[ContaPagar]:
        items = self._get(
            "contas_pagar",
            {
                "data_vencimento_de": data_inicio.isoformat(),
                "data_vencimento_ate": data_fim.isoformat(),
                PAGE_PARAM: pagina,
                PAGE_SIZE_PARAM: DEFAULT_PAGE_SIZE,
            },
        )
        return [ContaPagar(**item, raw=item) for item in items]
