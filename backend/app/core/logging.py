"""
Structured Logging Configuration
"""

import logging
import sys
from typing import Any, Dict
import json
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """
    Format log records as structured JSON for production log collectors.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        return json.dumps(log_obj)


def setup_logging(log_level: str = "INFO", json_logs: bool = False) -> None:
    """
    Configure application-wide structured logging.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if json_logs:
        handler.setFormatter(JSONFormatter())
    else:
        standard_format = "%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d | %(message)s"
        handler.setFormatter(logging.Formatter(standard_format, datefmt="%Y-%m-%d %H:%M:%S"))

    root_logger.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


logger = logging.getLogger("healcloud")

