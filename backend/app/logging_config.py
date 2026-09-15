"""Structured JSON logging configuration using stdlib logging.

Provides a JsonFormatter that outputs one JSON object per log line with
fields: timestamp, level, logger, message, request_id. The request_id
is read from a ContextVar set by the request ID middleware.
"""

import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

# ContextVar for request-scoped ID — set by RequestIDMiddleware in main.py
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(None),
        }
        return json.dumps(log_entry)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger with JSON formatting on stdout."""
    root = logging.getLogger()
    root.setLevel(level)

    # Avoid adding duplicate handlers on repeated calls
    if any(isinstance(h, logging.StreamHandler) and isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
