import logging


audit_logger = logging.getLogger("security.audit")


def log_security_event(event: str, **fields) -> None:
    payload = {"event": event}
    payload.update({key: value for key, value in fields.items() if value is not None})
    audit_logger.info(event, extra=payload)
