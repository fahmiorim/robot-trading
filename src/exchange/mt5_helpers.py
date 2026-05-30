"""
MT5 helper utilities — price normalisation, SL/TP validation, volume rounding.

Mixin for ``MT5Exchange``.
"""

from typing import Optional

import MetaTrader5 as mt5

from src.utils.logging import get_logger

logger = get_logger(__name__)


class MT5HelperMixin:
    """Mixin: price/size helpers and validation."""

    def _normalise_price(self, symbol: str, price: float) -> float:
        """Round price to symbol digits to avoid MT5 error 10014."""
        if price is None or price <= 0:
            return 0.0
        info = self.get_symbol_info(symbol)
        digits = info.get('digits', 2)
        return round(price, digits)

    def _validate_sltp_distance(self, symbol: str, entry: float,
                                 sl: Optional[float],
                                 tp: Optional[float]):
        """Enforce broker minimum stops level distance."""
        if sl is None and tp is None:
            return sl, tp
        info = self.get_symbol_info(symbol)
        min_stops = info.get('trade_stops_level', 0)
        point = info.get('point', 0.01)
        if min_stops <= 0 or point <= 0:
            return sl, tp
        min_dist = min_stops * point
        digits = info.get('digits', 2)
        if sl is not None and sl > 0:
            dist = abs(entry - sl)
            if dist < min_dist:
                adjusted = entry - min_dist if sl < entry else entry + min_dist
                sl = round(adjusted, digits)
                logger.warning(f"SL adjusted to {sl} (min dist {min_dist:.{digits}f})")
        if tp is not None and tp > 0:
            dist = abs(entry - tp)
            if dist < min_dist:
                adjusted = entry + min_dist if tp > entry else entry - min_dist
                tp = round(adjusted, digits)
                logger.warning(f"TP adjusted to {tp} (min dist {min_dist:.{digits}f})")
        return sl, tp

    @staticmethod
    def validate_volume(volume: float, volume_min: float = 0.01,
                        volume_max: float = 100.0,
                        volume_step: float = 0.01) -> float:
        """Round volume to step and clamp within broker limits."""
        if volume <= 0:
            return volume_min
        volume = round(volume / volume_step) * volume_step
        return max(volume_min, min(volume, volume_max))

    def _default_sl(self, price: float, side: str) -> float:
        return (
            price * (1 - self.default_sl_pct)
            if side.upper() == "BUY"
            else price * (1 + self.default_sl_pct)
        )

    def _default_tp(self, price: float, side: str) -> float:
        return (
            price * (1 + self.default_tp_pct)
            if side.upper() == "BUY"
            else price * (1 - self.default_tp_pct)
        )
