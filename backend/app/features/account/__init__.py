"""Account feature boundary for identity, preferences, and rewards."""

FEATURE_NAME = "account"
ROUTE_PREFIX = "/api/mypage"
DATA_COLLECTIONS = ("users", "user_preferences", "user_points", "points_history")

__all__ = ["DATA_COLLECTIONS", "FEATURE_NAME", "ROUTE_PREFIX"]
