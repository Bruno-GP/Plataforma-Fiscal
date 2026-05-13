from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class ExternalServiceError(Exception):
    service: str
    message: str
    status_code: int | None = None

    def __str__(self) -> str:
        if self.status_code is None:
            return f"{self.service}: {self.message}"
        return f"{self.service}: {self.message} (HTTP {self.status_code})"


def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout_seconds: float = 30.0,
    service_name: str,
) -> Any:
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException as exc:
        raise ExternalServiceError(
            service=service_name,
            message="tempo limite excedido ao consultar servico externo",
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise ExternalServiceError(
            service=service_name,
            message="servico externo retornou erro",
            status_code=exc.response.status_code,
        ) from exc
    except httpx.RequestError as exc:
        raise ExternalServiceError(
            service=service_name,
            message="falha de conexao ao consultar servico externo",
        ) from exc
    except ValueError as exc:
        raise ExternalServiceError(
            service=service_name,
            message="resposta JSON invalida do servico externo",
        ) from exc
