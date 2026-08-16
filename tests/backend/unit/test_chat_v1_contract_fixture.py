"""Machine-readable frozen v1 REST/SSE contract guard."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "frontend/src/services/__fixtures__/chat-v1-contract.json"


def test_chat_v1_fixture_freezes_routes_media_types_and_all_observed_statuses() -> None:
    contract = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert contract["endpoints"]["/api/chat/message"] == [
        "application/json",
        "text/event-stream",
    ]
    assert contract["endpoints"]["/api/chat/stream"] == ["text/event-stream"]
    assert set(contract["status_semantics"]) == {
        "streaming",
        "processing",
        "partial",
        "synthesizing",
        "complete",
        "new_message",
        "success",
        "error",
        "cancelled",
    }
    assert contract["transport_done"] == "[DONE]"


def test_error_done_and_done_without_terminal_are_not_success_scenarios() -> None:
    contract = json.loads(FIXTURE.read_text(encoding="utf-8"))
    scenarios = {item["name"]: item for item in contract["scenarios"]}

    assert scenarios["error_then_done"]["expected_outcome"] == "error"
    assert scenarios["done_without_terminal"]["expected_outcome"] == "protocol_error"
    assert scenarios["eof_without_done"]["expected_outcome"] == "protocol_error"
