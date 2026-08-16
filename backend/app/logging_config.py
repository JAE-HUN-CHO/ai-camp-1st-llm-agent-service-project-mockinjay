"""
Logging Configuration
Structured logging with rotating file handlers
"""
import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.config import settings


class SensitiveDataFilter(logging.Filter):
    """Redact common health, credential, and user-data fields from messages."""

    _field_names = (
        r"password|token|api[_-]?key|email|user[_-]?id|userid|query|content|response|filename"
    )
    _pattern = re.compile(
        rf"(?i)({_field_names})\s*[:=]\s*(.*?)(?=\s+(?:{_field_names})\s*[:=]|[,}}\n]|$)"
    )
    _email_pattern = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
    _bearer_pattern = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
    _jwt_pattern = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
    _canary_pattern = re.compile(r"(?i)\b(?:pii|health|token)[_-]?canary[-_A-Za-z0-9.]*\b")

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        message = self._pattern.sub(r"\1=<redacted>", message)
        message = self._email_pattern.sub("<redacted-email>", message)
        message = self._bearer_pattern.sub("Bearer <redacted>", message)
        message = self._jwt_pattern.sub("<redacted-token>", message)
        record.msg = self._canary_pattern.sub("<redacted-canary>", message)
        record.args = ()
        return True


class RedactingFormatter(logging.Formatter):
    """Apply the same PII policy to messages and formatted tracebacks."""

    def formatException(self, exc_info) -> str:  # noqa: N802 - logging API
        rendered = super().formatException(exc_info)
        record = logging.LogRecord(
            name="traceback",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg=rendered,
            args=(),
            exc_info=None,
        )
        SensitiveDataFilter().filter(record)
        return record.getMessage()


def setup_logging():
    """
    Configure application logging with structured format and rotating file handlers
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Log format
    log_format = RedactingFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.is_development else logging.INFO)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.is_development else logging.INFO)
    console_handler.setFormatter(log_format)
    console_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(console_handler)

    # File Handler - All logs
    all_logs_handler = RotatingFileHandler(
        filename=log_dir / "careguide.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    all_logs_handler.setLevel(logging.DEBUG)
    all_logs_handler.setFormatter(log_format)
    all_logs_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(all_logs_handler)

    # File Handler - Error logs only
    error_logs_handler = RotatingFileHandler(
        filename=log_dir / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_logs_handler.setLevel(logging.ERROR)
    error_logs_handler.setFormatter(log_format)
    error_logs_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(error_logs_handler)

    # Configure specific loggers
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    # MongoDB driver logging
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)

    # HTTP client logging
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Application logger
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.DEBUG if settings.is_development else logging.INFO)

    return app_logger


# Global application logger
logger = setup_logging()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module

    Args:
        name: Name of the logger (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
