"""Small pure helpers for game logic used by tests.
Keep side-effect free so tests can import this module without initializing pygame.
"""
from typing import Tuple

def has_unsaved_shape_changes(saved_x: str, saved_o: str, preview_x: str, preview_o: str) -> bool:
    """Return True if preview shapes differ from saved shapes."""
    return (saved_x != preview_x) or (saved_o != preview_o)
