"""Regression tests for the application log redaction boundary."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.logging_config import RedactingFormatter, SensitiveDataFilter


def test_sensitive_fields_are_redacted_before_emission() -> None:
    record = logging.LogRecord(
        name="careguide",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="query=%s user_id=%s email=%s token=%s",
        args=("creatinine 1.8", "user-1", "patient@example.com", "secret-token"),
        exc_info=None,
    )

    assert SensitiveDataFilter().filter(record) is True
    assert "creatinine 1.8" not in record.getMessage()
    assert "patient@example.com" not in record.getMessage()
    assert "secret-token" not in record.getMessage()
    assert record.getMessage().count("<redacted>") == 4


def test_pii_canaries_and_bearer_tokens_are_redacted() -> None:
    record = logging.LogRecord(
        name="careguide",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="health-canary-ckd3 patient@example.com Bearer eyJhbGciOiJIUzI1NiJ9.abc.sig",
        args=(),
        exc_info=None,
    )

    SensitiveDataFilter().filter(record)
    emitted = record.getMessage()
    assert "health-canary" not in emitted
    assert "patient@example.com" not in emitted
    assert "eyJhbGci" not in emitted


def test_traceback_text_is_redacted_by_formatter() -> None:
    try:
        raise RuntimeError(
            "health-canary-ckd3 patient@example.com Bearer secret-token"
        )
    except RuntimeError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="careguide",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="request failed",
        args=(),
        exc_info=exc_info,
    )
    emitted = RedactingFormatter("%(message)s").format(record)
    assert "health-canary" not in emitted
    assert "patient@example.com" not in emitted
    assert "secret-token" not in emitted
