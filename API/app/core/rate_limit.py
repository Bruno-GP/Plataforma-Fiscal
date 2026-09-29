from __future__ import annotations

import time
from threading import Lock

from fastapi import HTTPException, status

from app.core.audit import log_security_event


class CooldownLimiter:
    """Impede reexecucao de uma acao antes de um intervalo minimo, por chave."""

    def __init__(self) -> None:
        self._last_call_at: dict[str, float] = {}
        self._lock = Lock()

    def check(self, key: str, *, min_interval_seconds: int, action: str) -> None:
        if min_interval_seconds <= 0:
            return

        now = time.monotonic()
        with self._lock:
            last_call_at = self._last_call_at.get(key)
            if last_call_at is not None and (now - last_call_at) < min_interval_seconds:
                restante = int(min_interval_seconds - (now - last_call_at))
                log_security_event(
                    "rate_limit_rejected",
                    outcome="rejected",
                    reason="cooldown_ativo",
                    action=action,
                    key=key,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Aguarde {restante}s antes de repetir esta operacao.",
                )
            self._last_call_at[key] = now


ibpt_sync_limiter = CooldownLimiter()
