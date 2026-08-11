"""Health-record feature boundary and persistence vocabulary."""

FEATURE_NAME = "health"
ROUTE_PREFIX = "/api/health"
DATA_COLLECTIONS = ("health_profiles", "health_records")

__all__ = ["DATA_COLLECTIONS", "FEATURE_NAME", "ROUTE_PREFIX"]
