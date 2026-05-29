"""Dollar-Cost Averaging (DCA) manager for scaling into positions."""

import time
from typing import Any, Dict, List, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class DCAManager:
    """Manages DCA opportunity detection and execution."""

    def __init__(self, config: Any):
        self.config = config
        self._dca_counts: Dict[int, int] = {} # ticket -> count
        self._dca_timestamps: Dict[int, float] = {} # ticket -> last_time

    def check_opportunity(
        self,
        paper_positions: List[Dict],
        get_current_price_fn,
        paper_trading: bool,
        paper_balance: float,
    ) -> Optional[Dict]:
        """Check if there's a DCA opportunity for any open position.

        Returns a DCA info dict or None.
        """
        dca_cfg = self.config.get("dca")
        if not isinstance(dca_cfg, dict) or not dca_cfg["enabled"]:
            return None

        max_dca = int(dca_cfg["max_dca_orders"])
        trigger_pct = float(dca_cfg["dca_trigger_pct"])
        cooldown_min = float(dca_cfg["dca_cooldown_minutes"])
        increment_factor = float(dca_cfg["dca_increment_factor"])
        position_limit_pct = float(dca_cfg["dca_position_limit_pct"])

        for pos in paper_positions:
            ticket = pos.get("ticket")
            if not ticket:
                continue

            sym = pos.get("symbol")
            try:
                # We need the price for the specific symbol of the position
                price = get_current_price_fn(sym) if sym else get_current_price_fn()
            except Exception as e:
                logger.error(f"DCA: Failed to fetch price for {sym}: {e}")
                continue

            if not price:
                continue
            
            is_buy = pos["action"] == "BUY" if "action" in pos else (pos["type"] == "BUY")
            current = price["bid"] if is_buy else price["ask"]
            entry = float(pos["price"]) if "price" in pos else float(pos.get("open_price", 0))
            if entry <= 0: continue

            pnl_pct = (
                ((current - entry) / entry * 100)
                if is_buy
                else ((entry - current) / entry * 100)
            )

            # Use persistent tracking instead of modifying the dict
            dca_count = self._dca_counts.get(ticket, 0)
            last_dca = self._dca_timestamps.get(ticket, 0.0)

            if dca_count >= max_dca or pnl_pct >= 0 or pnl_pct > trigger_pct:
                continue
            if time.time() - last_dca < cooldown_min * 60:
                continue

            dca_vol = float(pos["volume"]) * (increment_factor**dca_count)
            total_cost = (float(pos["volume"]) + dca_vol) * entry
            balance = paper_balance
            if (total_cost / balance) * 100 > position_limit_pct:
                continue

            self._dca_counts[ticket] = dca_count + 1
            self._dca_timestamps[ticket] = time.time()
            logger.info(f"DCA: Adding {dca_vol} to {ticket}")

            return {
                "ticket": ticket,
                "symbol": sym,
                "side": "BUY" if is_buy else "SELL",
                "volume": dca_vol,
                "dca_count": self._dca_counts[ticket],
                "entry_price": entry,
            }

        return None

    def execute_dca(
        self,
        dca_info: Dict,
        execute_trade_fn,
        rpc_send_trade_alert_fn,
        current_regime: str,
    ) -> Dict:
        """Execute a DCA order and send alert."""
        signal = 1 if dca_info["side"] == "BUY" else -1
        result = execute_trade_fn(signal, volume=dca_info["volume"])
        if result.get("success"):
            rpc_send_trade_alert_fn(
                symbol=dca_info["symbol"],
                action=f"DCA {dca_info['side']}",
                price=result.get("price", dca_info.get("entry_price", 0)),
                strategy="DCA",
                regime=current_regime,
            )
        return result
