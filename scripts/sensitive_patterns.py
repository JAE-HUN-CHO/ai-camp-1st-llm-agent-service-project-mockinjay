"""Canonical credential and PII canary patterns for verification tooling."""

from __future__ import annotations

import re


SENSITIVE_PATTERN = re.compile(
    r"(?i)(?:"
    r"bearer\s+[a-z0-9._~+/=-]+|"
    r"eyJ[a-z0-9_-]+\.[a-z0-9_-]+\.[a-z0-9_-]+|"
    r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}|"
    r"(?:pii|health|token)[_-]?canary(?:[-_][a-z0-9.]+)*"
    r")"
)
