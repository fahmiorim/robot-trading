"""
Exchange helper utilities — price normalisation, volume validation, SL/TP distance.

Consolidated from the old ``src/util/mt5_helpers.py`` and deduplicated from
individual exchange implementations. Exchange classes delegate to these helpers
instead of reimplementing the logic.
"""
from typing import Any, Dict, List, Optional, Tuple

from src.utils.logging import get_logger

logger = get_logger(__name__)

# ── MT5 Account / Trade Helpers ────

def get_account_info() -> Dict[str, float]:
    """Get MT5 account balance info as dict."""
    try:
        import MetaTrader5 as mt5
        account = mt5.account_info()
        if account is None:
            return {'balance': 0, 'equity': 0, 'free_margin': 0, 'margin_level': 0, 'profit': 0}
        return {
            'balance': float(account.balance),
            'equity': float(account.equity),
            'free_margin': float(account.margin_free),
            'margin_level': float(account.margin_level or 0),
            'profit': float(account.profit or 0),
        }
    except ImportError:
        logger.warning("MetaTrader5 not available")
        return {'balance': 0, 'equity': 0, 'free_margin': 0, 'margin_level': 0, 'profit': 0}


def get_symbol_trade_info(symbol: str) -> Dict[str, Any]:
    """Get MT5 symbol trade info (trade mode, volume limits, digits)."""
    try:
        import MetaTrader5 as mt5
        info = mt5.symbol_info(symbol)
        if info is None:
            mt5.symbol_select(symbol, True)
            info = mt5.symbol_info(symbol)
        if info is None:
            return {'trade_mode': None, 'volume_min': 0.01,
                    'volume_step': 0.01, 'digits': 2}
        return {
            'trade_mode': int(info.trade_mode) if info.trade_mode is not None else None,
            'volume_min': float(getattr(info, 'volume_min', 0.01)),
            'volume_step': float(getattr(info, 'volume_step', 0.01)),
            'volume_max': float(getattr(info, 'volume_max', 100.0)),
            'digits': int(getattr(info, 'digits', 2)),
        }
    except ImportError:
        logger.warning("MetaTrader5 not available")
        return {'trade_mode': None, 'volume_min': 0.01, 'volume_step': 0.01, 'digits': 2}


def get_trade_history(days: int, limit: int) -> List[Dict[str, Any]]:
    """Get MT5 historical closed trades as list of dicts."""
    try:
        import MetaTrader5 as mt5
        from datetime import datetime, timedelta
        from_time = int((datetime.now() - timedelta(days=days)).timestamp())
        to_time = int(datetime.now().timestamp())
        deals = mt5.history_deals_get(from_time, to_time)
        if deals is None or len(deals) == 0:
            return []
        result = []
        for d in sorted(deals, key=lambda x: x.time, reverse=True)[:limit]:
            result.append({
                'symbol': d.symbol,
                'type': d.type,
                'volume': d.volume,
                'price_open': d.price,
                'price_close': getattr(d, 'price_close', d.price),
                'profit': d.profit,
                'time': d.time,
                'comment': d.comment,
            })
        return result
    except ImportError:
        logger.warning("MetaTrader5 not available")
        return []


def validate_volume(volume: float,
                    volume_min: float,
                    volume_max: float,
                    volume_step: float) -> float:
    """Round *volume* to nearest *volume_step* and clamp to broker limits."""
    if volume <= 0:
        return volume_min
    if volume_step > 0:
        volume = round(volume / volume_step) * volume_step
    return max(volume_min, min(volume, volume_max))


def normalise_price(price: float, digits: int) -> float:
    """Round price to the given number of decimal places."""
    return round(price, digits)


def validate_sltp_distance(entry: float,
                           sl: Optional[float],
                           tp: Optional[float],
                           min_stops: int,
                           point: float,
                           digits: int) -> Tuple[Optional[float], Optional[float]]:
    """Enforce broker minimum stops level distance for SL/TP."""
    if min_stops <= 0 or point <= 0:
        return sl, tp

    min_dist = min_stops * point

    if sl is not None:
        dist = abs(entry - sl)
        if dist < min_dist:
            adjusted = entry - min_dist if sl < entry else entry + min_dist
            sl = round(adjusted, digits)
            logger.warning(f"SL adjusted to {sl} (min dist {min_dist:.{digits}f})")

    if tp is not None:
        dist = abs(entry - tp)
        if dist < min_dist:
            adjusted = entry + min_dist if tp > entry else entry - min_dist
            tp = round(adjusted, digits)
            logger.warning(f"TP adjusted to {tp} (min dist {min_dist:.{digits}f})")

    return sl, tp


def default_sl(price: float, side: str, pct: float) -> float:
    """Default stop-loss 1.5% away from entry."""
    return price * (1 - pct) if side.upper() == "BUY" else price * (1 + pct)


def default_tp(price: float, side: str, pct: float) -> float:
    """Default take-profit 3% away from entry."""
    return price * (1 + pct) if side.upper() == "BUY" else price * (1 - pct)
