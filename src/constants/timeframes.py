"""
Timeframe definitions and filling mode helpers.
"""
from typing import Dict, List, Optional

TIMEFRAME_MAP: Dict[str, int] = {
    "TIMEFRAME_M1": 1,
    "TIMEFRAME_M5": 5,
    "TIMEFRAME_M15": 15,
    "TIMEFRAME_M30": 30,
    "TIMEFRAME_H1": 60,
    "TIMEFRAME_H4": 240,
    "TIMEFRAME_D1": 1440,
}

FILLING_MODES: List = [
    ("None (omit)", None),
    ("ORDER_FILLING_RETURN", 2),
    ("ORDER_FILLING_IOC", 1),
    ("ORDER_FILLING_FOK", 0),
]


def get_best_filling_mode() -> Optional[int]:
    """Return the best filling mode (try None = broker default)."""
    return None


def get_next_filling_mode(current_label: str) -> Optional[int]:
    """Try the next filling mode when the current one fails (rotate)."""
    labels = [lbl for lbl, _ in FILLING_MODES]
    try:
        idx = labels.index(current_label)
    except ValueError:
        idx = -1
    
    # Rotate to next index, or back to 0 if at the end
    next_idx = (idx + 1) % len(labels)
    
    next_label, next_val = FILLING_MODES[next_idx]
    # If we rotated back to None (omit), and we just came from something else,
    # maybe skip it or return it. Let's just return what's at the index.
    return next_val
