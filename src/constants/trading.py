"""
Core trading enums and constants.
"""
from enum import Enum, IntEnum


class SignalType(IntEnum):
    """Trading signal: BUY, SELL, or HOLD."""
    SELL = -1
    HOLD = 0
    BUY = 1


SIGNAL_LABELS = {1: "BUY", -1: "SELL", 0: "HOLD"}


class RegimeType(str, Enum):
    """Market regime classification."""
    TRENDING = "trending"
    RANGING = "ranging"
    CHOPPY = "choppy"
    UNKNOWN = "unknown"


class TradeStatus(str, Enum):
    """Trade lifecycle status."""
    OPEN = "open"
    CLOSED = "closed"
    CANCELED = "canceled"


class OrderSide(str, Enum):
    """Order direction."""
    BUY = "BUY"
    SELL = "SELL"


class PositionSizing(str, Enum):
    """Position sizing methods."""
    FIXED_PCT = "fixed_pct"
    KELLY = "kelly"
    FIXED = "fixed"


class MLModelType(str, Enum):
    """Available ML model types."""
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"


class TradeMode(IntEnum):
    """MT5 trade mode."""
    DISABLED = 0
    LONGONLY = 1
    SHORTONLY = 2
    CLOSEONLY = 3
    FULL = 4
