"""Regression tests for the application log redaction boundary."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.logging_config import SensitiveDataFilter


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
