"""
Timeframe definitions and filling mode helpers.
"""
from typing import Dict, List, Optional

# ── Timeframe Constants ───────────────────────────────────────
# TIMEFRAME_MAP: MT5 API constants (passed directly to mt5.copy_rates_from_pos)
# For M1-D1, these happen to equal minutes. For W1/MN, they are MT5 enum values.
TIMEFRAME_MAP: Dict[str, int] = {
    "TIMEFRAME_M1": 1,
    "TIMEFRAME_M5": 5,
    "TIMEFRAME_M15": 15,
    "TIMEFRAME_M30": 30,
    "TIMEFRAME_H1": 60,
    "TIMEFRAME_H4": 240,
    "TIMEFRAME_D1": 1440,
    "TIMEFRAME_W1": 16385,
    "TIMEFRAME_MN": 49153,
}

# ── Minutes equivalent (for cycle interval, cache timing, etc.) ──
TIMEFRAME_MINUTES: Dict[str, int] = {
    "TIMEFRAME_M1": 1,
    "TIMEFRAME_M5": 5,
    "TIMEFRAME_M15": 15,
    "TIMEFRAME_M30": 30,
    "TIMEFRAME_H1": 60,
    "TIMEFRAME_H4": 240,
    "TIMEFRAME_D1": 1440,
    "TIMEFRAME_W1": 10080,   # 7 days
    "TIMEFRAME_MN": 43200,   # 30 days
}

# ── Trading Category for each timeframe ───────────────────────
TIMEFRAME_CATEGORIES: Dict[str, str] = {
    "TIMEFRAME_M1":  "⚡ Scalping (Menit/Detik)",
    "TIMEFRAME_M5":  "⚡ Scalping (Menit/Detik)",
    "TIMEFRAME_M15": "📊 Day Trading (Intraday/Harian)",
    "TIMEFRAME_M30": "📊 Day Trading (Intraday/Harian)",
    "TIMEFRAME_H1":  "📊 Day Trading (Intraday/Harian)",
    "TIMEFRAME_H4":  "📈 Swing Trading (Hari/Minggu)",
    "TIMEFRAME_D1":  "📈 Swing Trading (Hari/Minggu)",
    "TIMEFRAME_W1":  "🎯 Position Trading (Bulan/Tahun)",
    "TIMEFRAME_MN":  "🎯 Position Trading (Bulan/Tahun)",
}

# ── Display labels for UI dropdown ────────────────────────────
TIMEFRAME_DISPLAY: Dict[str, str] = {
    "TIMEFRAME_M1":  "⚡ Scalping › M1 (1 Menit)",
    "TIMEFRAME_M5":  "⚡ Scalping › M5 (5 Menit)",
    "TIMEFRAME_M15": "📊 Day Trading › M15 (15 Menit)",
    "TIMEFRAME_M30": "📊 Day Trading › M30 (30 Menit)",
    "TIMEFRAME_H1":  "📊 Day Trading › H1 (1 Jam)",
    "TIMEFRAME_H4":  "📈 Swing Trading › H4 (4 Jam)",
    "TIMEFRAME_D1":  "📈 Swing Trading › D1 (Harian)",
    "TIMEFRAME_W1":  "🎯 Position Trading › W1 (Mingguan)",
    "TIMEFRAME_MN":  "🎯 Position Trading › MN (Bulanan)",
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
