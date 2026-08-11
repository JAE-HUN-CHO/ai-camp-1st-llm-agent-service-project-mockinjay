import pytest

from backend.app.adapters.ollama.embedding import expand_vector_losslessly


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    return dot / (left_norm * right_norm)


def test_lossless_width_expansion_preserves_cosine_similarity() -> None:
    left = [1.0, 2.0, -3.0]
    right = [3.0, -1.0, 2.0]

    expanded_left = expand_vector_losslessly(left, 6)
    expanded_right = expand_vector_losslessly(right, 6)

    assert len(expanded_left) == 6
    assert cosine(left, right) == pytest.approx(cosine(expanded_left, expanded_right))


def test_width_adapter_fails_closed_for_non_doubling_dimensions() -> None:
    with pytest.raises(ValueError, match="Cannot adapt Ollama embedding"):
        expand_vector_losslessly([0.0] * 768, 1024)
