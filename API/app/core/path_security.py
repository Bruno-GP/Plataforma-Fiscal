from __future__ import annotations

import os

from fastapi import HTTPException, status

from app.core.audit import log_security_event


def resolve_safe_batch_path(root_dir: str | None, caminho_relativo: str, *, tipo: str) -> str:
    if not root_dir:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Processamento batch de {tipo} esta desabilitado neste ambiente (PROCESSAMENTO_BATCH_ROOT_DIR nao configurado).",
        )

    raiz_resolvida = os.path.realpath(root_dir)
    caminho_resolvido = os.path.realpath(os.path.join(raiz_resolvida, caminho_relativo))

    if os.path.commonpath([raiz_resolvida, caminho_resolvido]) != raiz_resolvida:
        log_security_event(
            "path_traversal_rejected",
            outcome="rejected",
            reason="caminho_fora_do_diretorio_permitido",
            tipo=tipo,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Caminho informado esta fora do diretorio permitido.",
        )

    return caminho_resolvido
