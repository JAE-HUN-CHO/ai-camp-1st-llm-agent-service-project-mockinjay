"""Community feature boundary for user-owned posts and interactions."""

FEATURE_NAME = "community"
ROUTE_PREFIX = "/api/community"
DATA_COLLECTIONS = ("posts", "comments", "post_likes")

__all__ = ["DATA_COLLECTIONS", "FEATURE_NAME", "ROUTE_PREFIX"]
