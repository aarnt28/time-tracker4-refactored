from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Mapping

from ..middlewares import principal_ctx_var, request_id_ctx_var


class JsonLogFormatter(logging.Formatter):
    """Render log records as JSON for easier ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_ctx_var.get()
        if request_id:
            payload["request_id"] = request_id
        principal = principal_ctx_var.get()
        if principal:
            payload["principal"] = principal
        extra = getattr(record, "extra_data", None)
        if isinstance(extra, Mapping):
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"))


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    logging.root.handlers = [handler]
    logging.root.setLevel(logging.INFO)
