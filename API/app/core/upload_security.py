from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, UploadFile, status

from app.core.audit import log_security_event
from app.core.config import (
    get_upload_max_total_bytes,
    get_upload_max_txt_bytes,
    get_upload_max_xml_bytes,
)


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    content: bytes


def _sanitize_filename(filename: str | None) -> str:
    sanitized = (filename or "").strip().replace("\\", "/").split("/")[-1]
    return sanitized[:255]


def _raise_invalid_upload(detail: str, *, filename: str | None, content_type: str | None, size_bytes: int | None) -> None:
    log_security_event(
        "upload_rejected",
        outcome="rejected",
        reason=detail,
        upload_filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
    )
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _looks_like_xml(content: bytes) -> bool:
    prefix = content.lstrip(b"\xef\xbb\xbf\r\n\t ")
    return prefix.startswith(b"<")


def _looks_like_text(content: bytes) -> bool:
    if not content:
        return False
    control_bytes = sum(1 for byte in content if byte < 9 or 13 < byte < 32)
    return control_bytes / max(len(content), 1) < 0.01


async def validate_xml_uploads(arquivos: list[UploadFile]) -> list[ValidatedUpload]:
    total_bytes = 0
    validated: list[ValidatedUpload] = []
    max_file_size = get_upload_max_xml_bytes()
    max_total_size = get_upload_max_total_bytes()

    for arquivo in arquivos:
        filename = _sanitize_filename(arquivo.filename)
        if not filename.lower().endswith(".xml"):
            _raise_invalid_upload(
                "Todos os arquivos enviados devem ter extensão .xml.",
                filename=filename,
                content_type=arquivo.content_type,
                size_bytes=None,
            )

        content = await arquivo.read()
        size_bytes = len(content)
        total_bytes += size_bytes

        if size_bytes == 0:
            _raise_invalid_upload(
                "Arquivo XML vazio não é permitido.",
                filename=filename,
                content_type=arquivo.content_type,
                size_bytes=size_bytes,
            )

        if size_bytes > max_file_size:
            _raise_invalid_upload(
                f"Arquivo XML excede o limite de {max_file_size} bytes.",
                filename=filename,
                content_type=arquivo.content_type,
                size_bytes=size_bytes,
            )

        if total_bytes > max_total_size:
            _raise_invalid_upload(
                "A soma dos arquivos enviados excede o limite permitido para a importação.",
                filename=filename,
                content_type=arquivo.content_type,
                size_bytes=total_bytes,
            )

        if not _looks_like_xml(content):
            _raise_invalid_upload(
                "O conteúdo enviado não corresponde a um XML válido.",
                filename=filename,
                content_type=arquivo.content_type,
                size_bytes=size_bytes,
            )

        validated.append(ValidatedUpload(filename=filename, content=content))

    return validated


async def validate_txt_uploads(arquivos: list[UploadFile]) -> list[ValidatedUpload]:
    total_bytes = 0
    validated: list[ValidatedUpload] = []
    max_file_size = get_upload_max_txt_bytes()
    max_total_size = get_upload_max_total_bytes()

    for arquivo in arquivos:
        filename = _sanitize_filename(arquivo.filename)
        if not filename.lower().endswith(".txt"):
            _raise_invalid_upload(
                "Todos os arquivos enviados devem ter extensão .txt.",
                filename=filename,
                content_type=arquivo.content_type,
                size_bytes=None,
            )

        content = await arquivo.read()
        size_bytes = len(content)
        total_bytes += size_bytes

        if size_bytes == 0:
            _raise_invalid_upload(
                "Arquivo TXT vazio não é permitido.",
                filename=filename,
                content_type=arquivo.content_type,
                size_bytes=size_bytes,
            )

        if size_bytes > max_file_size:
            _raise_invalid_upload(
                f"Arquivo TXT excede o limite de {max_file_size} bytes.",
                filename=filename,
                content_type=arquivo.content_type,
                size_bytes=size_bytes,
            )

        if total_bytes > max_total_size:
            _raise_invalid_upload(
                "A soma dos arquivos enviados excede o limite permitido para a importação.",
                filename=filename,
                content_type=arquivo.content_type,
                size_bytes=total_bytes,
            )

        if not _looks_like_text(content):
            _raise_invalid_upload(
                "O conteúdo enviado não corresponde a um TXT legível.",
                filename=filename,
                content_type=arquivo.content_type,
                size_bytes=size_bytes,
            )

        validated.append(ValidatedUpload(filename=filename, content=content))

    return validated
