import json
import logging
import re
import time
import uuid
from contextvars import ContextVar

from fastapi import Request

from app.core.config import get_api_request_logs_enabled, get_log_level


request_id_context: ContextVar[str] = ContextVar("request_id", default="-")

_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_CNPJ_PATTERN = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
_OPENAI_KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]+")
_TOKEN_PATTERN = re.compile(
    r"(?i)\b(token|authorization|password|senha|secret|api[_-]?key)\b\s*[:=]\s*['\"]?[^'\"\s,}]+"
)


def _sanitize(value: object) -> object:
    if not isinstance(value, str):
        return value

    sanitized = _EMAIL_PATTERN.sub("[redacted-email]", value)
    sanitized = _CNPJ_PATTERN.sub("[redacted-cnpj]", sanitized)
    sanitized = _OPENAI_KEY_PATTERN.sub("[redacted-api-key]", sanitized)
    sanitized = _TOKEN_PATTERN.sub(lambda match: f"{match.group(1)}=[redacted]", sanitized)
    return sanitized


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": _sanitize(record.getMessage()),
            "request_id": getattr(record, "request_id", request_id_context.get()),
        }

        for field in (
            "method",
            "path",
            "status_code",
            "duration_ms",
            "event",
            "empresa_id",
            "login_id",
            "reason",
            "outcome",
            "auth_source",
            "content_type",
            "size_bytes",
            "job_id",
            "tipo_job",
            "cnpj_emitente",
            "etapa",
            "status",
            "duracao_ms",
            "total_itens",
            "itens_processados",
            "erro_tipo",
            "erro",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = _sanitize(value)

        if record.exc_info and logging.getLogger().isEnabledFor(logging.DEBUG):
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    if getattr(root_logger, "_plataforma_fiscal_configured", False):
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, get_log_level(), logging.WARNING))
    root_logger._plataforma_fiscal_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)


async def log_request_cycle(request: Request, call_next):
    if not get_api_request_logs_enabled():
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        return response

    logger = get_logger("api.request")
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_context.set(request_id)
    started_at = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.exception(
            "request_failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
                "client": request.client.host if request.client else None,
            },
        )
        request_id_context.reset(token)
        raise

    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client": request.client.host if request.client else None,
        },
    )
    request_id_context.reset(token)
    return response
