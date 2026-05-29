"""ROI (Return on Investment) table take-profit manager."""

from datetime import datetime
from typing import Any, Dict, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class ROIManager:
    """Manages ROI-based take-profit using a tiered ROI table."""

    def __init__(self, config: Any):
        self.config = config

    def get_roi_price(
        self, entry_price: float, side: str, position_time_minutes: float
    ) -> Optional[float]:
        """Calculate the ROI target price for a position based on elapsed time."""
        roi_cfg = self.config.get("roi")
        if not isinstance(roi_cfg, dict) or not roi_cfg.get("enabled"):
            return None

        table = roi_cfg["table"]
        if not table:
            return None

        # Ensure table is sorted by minutes ascending
        try:
            sorted_table = sorted(table, key=lambda x: x.get("minutes", 0))
        except Exception:
            sorted_table = table

        roi_pct = 0.0
        for tier in sorted_table:
            if tier.get("minutes", 0) <= position_time_minutes:
                roi_pct = tier.get("roi_pct", 0)
            else:
                break

        if roi_pct <= 0:
            return None

        if side == "BUY":
            return entry_price * (1 + roi_pct / 100.0)
        else:
            return entry_price * (1 - roi_pct / 100.0)

    def check_take_profit(
        self, exchange: Any, symbol: str, paper_trading: bool, close_position_fn,
        positions_override: list = None
    ) -> None:
        """Check open positions and close any that hit ROI target."""
        try:
            positions = positions_override if positions_override is not None else exchange.get_open_positions(symbol)
        except Exception:
            return

        if not positions:
            return

        for pos in positions:
            ticket = pos.get("ticket") or pos.get("id")
            side = pos.get("side", pos.get("type", "BUY")).upper()
            entry = pos.get("entry_price", pos.get("open_price", 0))
            current = pos.get("current_price", 0)
            if entry <= 0 or current <= 0 or ticket is None:
                continue

            position_time = pos.get("entry_time")
            elapsed_min = 0
            if position_time:
                if isinstance(position_time, str):
                    try:
                        position_time = datetime.fromisoformat(position_time)
                    except Exception:
                        position_time = None
                if isinstance(position_time, datetime):
                    now = datetime.now(position_time.tzinfo) if position_time.tzinfo else datetime.now()
                    elapsed_min = (now - position_time).total_seconds() / 60

            roi_price = self.get_roi_price(entry, side, elapsed_min)
            if roi_price is None:
                continue

            if side == "BUY" and current >= roi_price:
                logger.info(f"ROI hit: {ticket} @ {current:.2f} >= {roi_price:.2f}")
                if close_position_fn:
                    close_position_fn(ticket)
            elif side == "SELL" and current <= roi_price:
                logger.info(f"ROI hit: {ticket} @ {current:.2f} <= {roi_price:.2f}")
                if close_position_fn:
                    close_position_fn(ticket)
