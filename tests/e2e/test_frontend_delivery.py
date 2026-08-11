"""HTTP-level end-to-end smoke tests for the canonical frontend artifact.

The test intentionally uses the Vite preview server instead of a browser
driver.  It verifies the deployed artifact and SPA fallback without adding a
new browser dependency to the local-first test environment.
"""

from __future__ import annotations

import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pytest

pytestmark = pytest.mark.integration


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _get(url: str) -> tuple[int, str]:
    try:
        with urlopen(url, timeout=5) as response:
            return response.status, response.read().decode("utf-8")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


@pytest.fixture(scope="module")
def preview_server() -> Iterator[str]:
    if not (FRONTEND / "dist" / "index.html").exists():
        pytest.skip("run `npm run build` in frontend before e2e smoke tests")

    port = _free_port()
    process = subprocess.Popen(
        ["npm", "run", "preview", "--", "--host", "127.0.0.1", "--port", str(port)],
        cwd=FRONTEND,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"frontend preview exited early: {output}")
        try:
            status, _ = _get(f"{base_url}/")
            if status == 200:
                break
        except (URLError, TimeoutError):
            time.sleep(0.2)
    else:
        process.terminate()
        raise RuntimeError("frontend preview did not become ready")

    try:
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@pytest.mark.parametrize("path", ["/", "/chat", "/diet-care", "/health", "/trends", "/mypage"])
def test_canonical_frontend_spa_routes_are_delivered(preview_server: str, path: str) -> None:
    status, body = _get(f"{preview_server}{path}")

    assert status == 200
    assert '<div id="root"></div>' in body
    assert "/assets/" in body
