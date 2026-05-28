"""
MT5 retcode definitions, trade mode constants, and helpers.
"""

from typing import Dict, Set


# MT5 trade mode constants
TRADE_MODE_DISABLED = 0
TRADE_MODE_LONGONLY = 1
TRADE_MODE_SHORTONLY = 2
TRADE_MODE_CLOSEONLY = 3
TRADE_MODE_FULL = 4

TRADE_MODE_LABELS = {
    TRADE_MODE_DISABLED: "Disabled",
    TRADE_MODE_LONGONLY: "Long Only",
    TRADE_MODE_SHORTONLY: "Short Only",
    TRADE_MODE_CLOSEONLY: "Close Only",
    TRADE_MODE_FULL: "Full Access",
}

MT5_RETCODES: Dict[int, str] = {
    10004: "Requote",
    10006: "Request rejected",
    10007: "Request canceled by trader",
    10008: "Order placed",
    10009: "No trade / HOLD",
    10010: "Only real orders accepted",
    10011: "Order timeout",
    10012: "Invalid request",
    10013: "Invalid volume",
    10014: "Invalid price",
    10015: "Invalid stops",
    10016: "Trade disabled",
    10017: "Not enough money",
    10018: "Order frozen",
    10019: "Broker's limit exceeded",
    10020: "Position already closed",
    10021: "Unexpected position",
    10022: "Market closed",
    10024: "Too many requests",
    10025: "No changes",
    10026: "Auto-trading disabled by server",
    10027: "Auto-trading disabled by client",
    10028: "Position locked",
    10029: "Invalid expiration",
    10030: "Invalid fill mode",
    10031: "Position modified but not yet processed",
    10032: "Margin call / no enough money",
}

RECOVERABLE_RETCODES: Set[int] = {10004, 10011, 10014, 10024, 10030, 10031}


def get_retcode_label(retcode: int) -> str:
    """Return human-readable label for an MT5 retcode."""
    return MT5_RETCODES.get(retcode, f"Unknown ({retcode})")
