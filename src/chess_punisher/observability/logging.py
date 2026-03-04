"""Structured logging helpers with correlation-id support."""

from __future__ import annotations

from contextlib import contextmanager
import contextvars
import json
import logging
from datetime import datetime, timezone
from typing import Generator
import uuid

_CORRELATION_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)
_CONFIGURED = False


class JsonFormatter(logging.Formatter):
    """Render log records as one-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        correlation_id = get_correlation_id()
        if correlation_id:
            payload["correlation_id"] = correlation_id

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key.startswith("_"):
                continue
            if key in _LOG_RECORD_RESERVED:
                continue
            payload[key] = value

        return json.dumps(payload, separators=(",", ":"), default=str)


_LOG_RECORD_RESERVED = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "message",
    "module",
    "msecs",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "taskName",
    "thread",
    "threadName",
}


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logger once for structured logs."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def new_correlation_id() -> str:
    return uuid.uuid4().hex[:12]


def get_correlation_id() -> str | None:
    return _CORRELATION_ID.get()


@contextmanager
def bind_correlation_id(correlation_id: str | None = None) -> Generator[str, None, None]:
    """Bind a correlation id to the current context."""
    cid = correlation_id or new_correlation_id()
    token = _CORRELATION_ID.set(cid)
    try:
        yield cid
    finally:
        _CORRELATION_ID.reset(token)
