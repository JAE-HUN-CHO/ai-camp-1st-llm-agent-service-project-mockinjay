"""Regression coverage for the local Parlant startup generation gate."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

from pydantic import BaseModel
import pytest


SERVER_DIR = Path(__file__).resolve().parents[3] / "backend" / "Agent" / "research_paper" / "server"
sys.path.insert(0, str(SERVER_DIR))

from nlp_service import GenerationInfo, GenerationResult, UsageInfo
from parlant_nlp_adapter import HealthcareSchematicGenerator


class _Schema(BaseModel):
    value: str


class _Service:
    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.generator = SimpleNamespace(model_name="local-test")

    async def generate_text(self, **_kwargs) -> GenerationResult:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        return GenerationResult(
            content='{"value":"ok"}',
            info=GenerationInfo(
                model="ollama/local-test",
                duration=0.01,
                usage=UsageInfo(input_tokens=1, output_tokens=1),
            ),
        )

    def count_tokens(self, text: str) -> int:
        return len(text)


@pytest.mark.asyncio
async def test_generators_share_local_concurrency_gate() -> None:
    service = _Service()
    gate = asyncio.Semaphore(1)
    meter = MagicMock()
    meter.create_duration_histogram.return_value = MagicMock()

    def generator() -> HealthcareSchematicGenerator[_Schema]:
        instance = HealthcareSchematicGenerator(
            healthcare_service=service,
            logger=MagicMock(),
            tracer=MagicMock(),
            meter=meter,
            generation_gate=gate,
        )
        instance.__orig_class__ = HealthcareSchematicGenerator[_Schema]
        return instance

    results = await asyncio.gather(
        generator().do_generate("first"),
        generator().do_generate("second"),
    )

    assert [result.content.value for result in results] == ["ok", "ok"]
    assert service.max_active == 1
