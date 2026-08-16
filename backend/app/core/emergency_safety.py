"""Deterministic emergency short-circuit shared by every chat entrypoint.

The policy deliberately runs without a model, database, or provider.  It is a
high-recall pre-filter, not a diagnosis: false positives are handled by the
emergency guidance while false negatives could send a patient request to a
generative system.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


EMERGENCY_RESPONSE = (
    "🚨 응급 증상이 의심됩니다. 즉시 119에 연락하거나 가까운 응급실로 이동하세요. "
    "온라인 안내만으로 진단하거나 기다리지 마세요."
)


@dataclass(frozen=True, slots=True)
class EmergencyDecision:
    """Result of the provider-independent emergency pre-filter."""

    blocked: bool
    matched_rule: str | None = None
    response: str | None = None


class EmergencySafetyPolicy:
    """Fail-closed emergency policy for Korean and English chat input."""

    _RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "breathing",
            (
                "호흡곤란",
                "숨이안쉬",
                "숨을못쉬",
                "숨쉬기힘",
                "숨을쉬기어려",
                "호흡이곤란",
                "질식",
                "breathingdifficulty",
                "cannotbreathe",
                "can'tbreathe",
                "shortnessofbreath",
            ),
        ),
        (
            "cardiac",
            (
                "흉통",
                "가슴통증",
                "가슴이아파",
                "가슴이조이",
                "심장마비",
                "chestpain",
                "heartattack",
            ),
        ),
        (
            "neurologic",
            (
                "의식저하",
                "의식이없",
                "의식을잃",
                "쓰러졌",
                "쓰러져",
                "반응이없",
                "경련",
                "발작",
                "마비",
                "말이어눌",
                "말이어둔",
                "말이어둘",
                "얼굴이한쪽으로처",
                "한쪽팔에힘이빠",
                "unconscious",
                "seizure",
                "stroke",
            ),
        ),
        (
            "bleeding_or_overdose",
            (
                "대량출혈",
                "피가멈추지",
                "약을너무많이",
                "과다복용",
                "overdose",
                "severebleeding",
            ),
        ),
        (
            "self_harm",
            (
                "죽고싶",
                "자살",
                "극단적선택",
                "내몸을해치",
                "자해",
                "suicide",
                "killmyself",
                "selfharm",
            ),
        ),
    )

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text or "").lower()
        return re.sub(r"[\s\-_.,!?/\\'\"()]+", "", normalized)

    def evaluate(self, text: str) -> EmergencyDecision:
        """Return a deterministic block decision without external calls."""
        normalized = self._normalize(text)
        for rule, phrases in self._RULES:
            if any(self._normalize(phrase) in normalized for phrase in phrases):
                return EmergencyDecision(
                    blocked=True,
                    matched_rule=rule,
                    response=EMERGENCY_RESPONSE,
                )
        return EmergencyDecision(blocked=False)


emergency_safety_policy = EmergencySafetyPolicy()
