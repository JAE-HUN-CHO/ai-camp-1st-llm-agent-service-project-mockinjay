"""Diet feature boundary.

The API router remains in ``app.api.diet`` for compatibility, while diet
specific persistence and upload policies can depend on this boundary without
coupling to chat or nutrition agent internals.
"""

FEATURE_NAME = "diet"
ROUTE_PREFIX = "/diet-care"
DATA_COLLECTIONS = ("diet_goals", "diet_logs")

__all__ = ["DATA_COLLECTIONS", "FEATURE_NAME", "ROUTE_PREFIX"]
