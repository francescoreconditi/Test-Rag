"""Centralized logging configuration."""

import logging
import logging.config
from pathlib import Path
from typing import Any, Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    log_format: Optional[str] = None,
    enable_console: bool = True
) -> None:
    """Setup centralized logging configuration."""

    if not log_format:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"

    # Ensure log directory exists if log_file is specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

    # Base configuration
    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": log_format,
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {},
        "loggers": {},
        "root": {
            "level": log_level,
            "handlers": []
        }
    }

    # Console handler
    if enable_console:
        config["handlers"]["console"] = {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        }
        config["root"]["handlers"].append("console")

    # File handler
    if log_file:
        config["handlers"]["file"] = {
            "class": "logging.FileHandler",
            "level": log_level,
            "formatter": "detailed",
            "filename": str(log_file),
            "mode": "a",
            "encoding": "utf-8"
        }
        config["root"]["handlers"].append("file")

        # Add rotating file handler for production
        config["handlers"]["rotating_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "detailed",
            "filename": str(log_file.with_suffix(".log")),
            "mode": "a",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8"
        }

    # Configure specific loggers
    config["loggers"].update({
        "src": {
            "level": log_level,
            "handlers": config["root"]["handlers"],
            "propagate": False
        },
        "streamlit": {
            "level": "WARNING",
            "handlers": config["root"]["handlers"],
            "propagate": False
        },
        "urllib3": {
            "level": "WARNING",
            "handlers": config["root"]["handlers"],
            "propagate": False
        },
        "requests": {
            "level": "WARNING",
            "handlers": config["root"]["handlers"],
            "propagate": False
        },
        "openai": {
            "level": "INFO",
            "handlers": config["root"]["handlers"],
            "propagate": False
        },
        "qdrant_client": {
            "level": "WARNING",
            "handlers": config["root"]["handlers"],
            "propagate": False
        },
        "llama_index": {
            "level": "INFO",
            "handlers": config["root"]["handlers"],
            "propagate": False
        }
    })

    # Apply configuration
    logging.config.dictConfig(config)

    # Get root logger and log initialization
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")
    if log_file:
        logger.info(f"Logs will be written to: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


class ContextFilter(logging.Filter):
    """Custom filter to add context information to log records."""

    def __init__(self, context: dict[str, Any]):
        super().__init__()
        self.context = context

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to the log record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


class SensitiveDataFilter(logging.Filter):
    """Filter to remove sensitive data from logs."""

    SENSITIVE_PATTERNS = [
        "api_key",
        "password",
        "token",
        "secret",
        "authorization",
        "bearer"
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out sensitive data from log messages."""
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            message = record.msg.lower()

            for pattern in self.SENSITIVE_PATTERNS:
                if pattern in message:
                    # Replace sensitive values
                    record.msg = record.msg.replace(
                        record.msg,
                        f"[REDACTED - contains {pattern}]"
                    )
                    break

        return True


def setup_structured_logging(
    service_name: str,
    version: str,
    environment: str = "development",
    log_level: str = "INFO"
) -> None:
    """Setup structured logging with JSON format."""

    import json

    class JSONFormatter(logging.Formatter):
        """Custom JSON formatter for structured logging."""

        def format(self, record: logging.LogRecord) -> str:
            """Format log record as JSON."""
            log_entry = {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "service": service_name,
                "version": version,
                "environment": environment,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno
            }

            # Add exception info if present
            if record.exc_info:
                log_entry["exception"] = self.formatException(record.exc_info)

            # Add extra fields
            for key, value in record.__dict__.items():
                if key not in ["name", "msg", "args", "levelname", "levelno",
                              "pathname", "filename", "module", "lineno",
                              "funcName", "created", "msecs", "relativeCreated",
                              "thread", "threadName", "processName", "process",
                              "exc_info", "exc_text", "stack_info"]:
                    log_entry[key] = value

            return json.dumps(log_entry, ensure_ascii=False)

    # Configure handler with JSON formatter
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    handler.addFilter(sensitive_filter)
