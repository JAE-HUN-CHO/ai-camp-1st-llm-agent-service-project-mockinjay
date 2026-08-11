"""Golden cases for the pre-classification emergency filter."""

import pytest

from backend.Agent.router.prompts import is_emergency_query


@pytest.mark.parametrize(
    "query",
    ["흉통이 심해요", "호흡곤란", "의식저하가 있어요", "경련이 발생했습니다", "chest pain"],
)
def test_emergency_keywords_bypass_normal_intent_classification(query: str) -> None:
    assert is_emergency_query(query) is True


@pytest.mark.parametrize("query", ["저염식 식단 알려줘", "오늘 기분이 좋아요", "eGFR 수치 의미"])
def test_non_emergency_queries_are_not_escalated(query: str) -> None:
    assert is_emergency_query(query) is False
