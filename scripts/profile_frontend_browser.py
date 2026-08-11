"""Collect browser navigation/paint metrics through Chrome DevTools Protocol."""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

import websocket

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
ROUTES = ["/", "/chat", "/diet-care", "/health", "/trends", "/mypage"]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class CDP:
    def __init__(self, websocket_url: str) -> None:
        self.socket = websocket.create_connection(websocket_url, timeout=20)
        self.message_id = 0

    def call(self, method: str, params: dict | None = None) -> dict:
        self.message_id += 1
        request_id = self.message_id
        self.socket.send(json.dumps({"id": request_id, "method": method, "params": params or {}}))
        while True:
            message = json.loads(self.socket.recv())
            if message.get("id") == request_id:
                return message

    def close(self) -> None:
        self.socket.close()


def run() -> dict[str, object]:
    if not (FRONTEND / "dist" / "index.html").exists():
        raise RuntimeError("build frontend before browser profiling")
    preview_port = free_port()
    cdp_port = free_port()
    preview = subprocess.Popen(
        ["npm", "run", "preview", "--", "--host", "127.0.0.1", "--port", str(preview_port)],
        cwd=FRONTEND,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    chrome = subprocess.Popen(
        [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--headless=new",
            f"--remote-debugging-port={cdp_port}",
            "--remote-allow-origins=*",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir=/private/tmp/careguide-chrome-{cdp_port}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{preview_port}"
    cdp: CDP | None = None
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                with urlopen(f"{base_url}/", timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError("frontend preview did not become ready")

        deadline = time.monotonic() + 30
        target = None
        while time.monotonic() < deadline:
            try:
                with urlopen(f"http://127.0.0.1:{cdp_port}/json", timeout=2) as response:
                    targets = json.loads(response.read())
                target = next(item for item in targets if item.get("type") == "page")
                break
            except (OSError, StopIteration):
                time.sleep(0.2)
        if target is None:
            raise RuntimeError("Chrome DevTools endpoint did not become ready")

        cdp = CDP(target["webSocketDebuggerUrl"])
        cdp.call("Performance.enable")
        metrics: list[dict[str, object]] = []
        for route in ROUTES:
            cdp.call("Page.enable")
            cdp.call("Page.navigate", {"url": f"{base_url}{route}"})
            time.sleep(1)
            navigation = cdp.call(
                "Runtime.evaluate",
                {
                    "expression": "JSON.stringify(performance.getEntriesByType('navigation')[0])",
                    "returnByValue": True,
                },
            )
            paint = cdp.call(
                "Runtime.evaluate",
                {
                    "expression": "JSON.stringify(performance.getEntriesByType('paint'))",
                    "returnByValue": True,
                },
            )
            result = navigation["result"]["result"].get("value", "{}")
            paint_result = paint["result"]["result"].get("value", "[]")
            navigation_data = json.loads(result)
            paint_data = json.loads(paint_result)
            metrics.append(
                {
                    "route": route,
                    "dom_content_loaded_ms": round(float(navigation_data.get("domContentLoadedEventEnd", 0)), 3),
                    "load_event_ms": round(float(navigation_data.get("loadEventEnd", 0)), 3),
                    "first_contentful_paint_ms": next(
                        (round(float(item["startTime"]), 3) for item in paint_data if item.get("name") == "first-contentful-paint"),
                        None,
                    ),
                }
            )
    finally:
        if cdp is not None:
            cdp.close()
        preview.terminate()
        chrome.terminate()
        for process in (preview, chrome):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    return {
        "benchmark": "canonical_frontend_chrome_cdp",
        "routes": metrics,
        "scope": "headless Chrome navigation and paint metrics; not a full user-interaction trace",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(run(), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
