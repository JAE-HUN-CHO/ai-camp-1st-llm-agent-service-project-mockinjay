"""Opt-in Ollama response-shape smoke test.

This module intentionally performs no network I/O during pytest collection.
Run it with ``pytest -m integration`` after starting the configured provider.
"""

import os

import httpx
import pytest
from dotenv import load_dotenv

load_dotenv()

pytestmark = pytest.mark.integration


def test_ollama_response_shape() -> None:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    response = httpx.post(
        f"{base_url}/api/chat",
        json={
            "model": os.getenv("OLLAMA_MODEL", "qwen3.6:27b-mlx"),
            "messages": [{"role": "user", "content": "Respond with exactly LOCAL_OK."}],
            "stream": False,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    assert payload["message"]["content"]
