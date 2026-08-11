"""Compatibility import for the chat feature runtime.

New code should import from ``app.features.chat.runtime``. This module remains
for existing API/test imports during the migration and deliberately exposes
the same symbols without owning process state.
"""

from app.features.chat.runtime import StreamRegistry, get_stream_registry

__all__ = ["StreamRegistry", "get_stream_registry"]
