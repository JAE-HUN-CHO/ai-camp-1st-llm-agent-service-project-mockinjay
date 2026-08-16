"""Health-record feature boundary and persistence vocabulary."""

FEATURE_NAME = "health"
ROUTE_PREFIX = "/api/health"
HEALTH_RECORDS_ROUTE_PREFIX = "/api/health-records"
DATA_COLLECTIONS = ("health_profiles", "health_records")

__all__ = [
    "DATA_COLLECTIONS",
    "FEATURE_NAME",
    "HEALTH_RECORDS_ROUTE_PREFIX",
    "ROUTE_PREFIX",
]
