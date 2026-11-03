"""Structured logging to stderr.

With the stdio transport, stdout *is* the protocol channel. A stray print() or a
log handler pointed at stdout will corrupt the JSON-RPC stream and the client
will drop the connection. So everything here goes to stderr, always.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any, Literal

# Attributes every LogRecord has. Anything else was passed via `extra=` and
# gets included in the JSON output as a structured field.
_STANDARD_ATTRS = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys() | {"message", "asctime"}
)


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with any `extra=` fields merged in."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", fmt: Literal["json", "text"] = "json") -> None:
    """Send all logs to stderr. Call this before building the server.

    The SDK calls `logging.basicConfig()` when a server is constructed, which is a
    no-op once the root logger has a handler. Configuring first means our format wins.
    """
    handler = logging.StreamHandler(sys.stderr)
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
