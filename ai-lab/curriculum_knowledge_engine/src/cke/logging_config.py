"""Structured logging setup.

Plain text in development (readable in a terminal), single-line JSON in
production (`log_json=True`) so log aggregators can parse it without a
regex. Configured once at process startup via `configure_logging()`.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any

_RESERVED_LOG_RECORD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Any extra=... fields passed to the log call ride along as-is.
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_RECORD_ATTRS and key not in payload:
                payload[key] = value

        return json.dumps(payload, default=str)


def configure_logging(*, level: str = "INFO", as_json: bool = False) -> None:
    root = logging.getLogger()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    if as_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )

    root.handlers.clear()
    root.addHandler(handler)

    # Quiet down noisy third-party libraries unless we're at DEBUG.
    if level != "DEBUG":
        for noisy in ("httpx2", "httpx", "chromadb", "urllib3"):
            logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
