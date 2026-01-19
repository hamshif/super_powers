
"""
Global state management for Super Power Sage.
Stores singleton references to resources like Ray Actors to avoid import cycles.
"""
from typing import Optional, Any

# Ray Actor reference
# Type is Any to avoid importing the implementation here
hero_generator: Optional[Any] = None

# Side-channel data queue for SSE streaming
# List of dicts: [{"type": "...", "data": ...}]
data_queue: list[dict[str, Any]] = []
