"""Quiz feature boundary for questions, attempts, and point events."""

FEATURE_NAME = "quiz"
ROUTE_PREFIX = "/api/quiz"
DATA_COLLECTIONS = ("quizzes", "quiz_attempts", "points_history")

__all__ = ["DATA_COLLECTIONS", "FEATURE_NAME", "ROUTE_PREFIX"]
