"""Measure canonical Vite preview delivery latency without a browser driver."""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
ROUTES = ["/", "/chat", "/diet-care", "/health", "/trends", "/mypage"]


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    rank = max(1, int(len(ordered) * fraction + 0.999999))
    return ordered[rank - 1]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run(iterations: int) -> dict[str, object]:
    if not (FRONTEND / "dist" / "index.html").exists():
        raise RuntimeError("build frontend before running this benchmark")
    port = free_port()
    process = subprocess.Popen(
        ["npm", "run", "preview", "--", "--host", "127.0.0.1", "--port", str(port)],
        cwd=FRONTEND,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                with urlopen(f"{base_url}/", timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError("frontend preview did not become ready")

        latencies: list[float] = []
        for _ in range(iterations):
            for route in ROUTES:
                started = time.perf_counter()
                with urlopen(f"{base_url}{route}", timeout=5) as response:
                    body = response.read()
                    if response.status != 200 or b'<div id="root"></div>' not in body:
                        raise RuntimeError(f"route delivery failed: {route}")
                latencies.append((time.perf_counter() - started) * 1000)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    return {
        "benchmark": "canonical_frontend_preview_delivery",
        "iterations": iterations,
        "routes": ROUTES,
        "requests": len(latencies),
        "unit": "milliseconds",
        "p50": round(percentile(latencies, 0.50), 3),
        "p95": round(percentile(latencies, 0.95), 3),
        "scope": "Vite preview HTTP delivery; excludes browser render and rerender cost",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(run(args.iterations), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
