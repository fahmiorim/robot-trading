"""Dollar-Cost Averaging (DCA) manager for scaling into positions."""

import time
from typing import Any, Dict, List, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class DCAManager:
    """Manages DCA opportunity detection and execution."""

    def __init__(self, config: Any):
        self.config = config

    def check_opportunity(
        self,
        paper_positions: List[Dict],
        get_current_price_fn,
        paper_trading: bool = False,
        paper_balance: float = 10000.0,
    ) -> Optional[Dict]:
        """Check if there's a DCA opportunity for any open paper position.

        Returns a DCA info dict or None.
        """
        dca_cfg = self.config.get("dca")
        if not isinstance(dca_cfg, dict) or not dca_cfg.get("enabled", False):
            return None

        max_dca = int(dca_cfg.get("max_dca_orders", 3))
        trigger_pct = float(dca_cfg.get("dca_trigger_pct", -1.0))
        cooldown_min = float(dca_cfg.get("dca_cooldown_minutes", 5))
        increment_factor = float(dca_cfg.get("dca_increment_factor", 1.5))
        position_limit_pct = float(dca_cfg.get("dca_position_limit_pct", 20.0))

        for pos in paper_positions:
            price = get_current_price_fn()
            is_buy = pos["action"] == "BUY"
            current = price["bid"] if is_buy else price["ask"]
            entry = pos["price"]
            pnl_pct = (
                ((current - entry) / entry * 100)
                if is_buy
                else ((entry - current) / entry * 100)
            )

            dca_count = pos.get("_dca_count", 0)
            last_dca = pos.get("_last_dca_time", 0)

            if dca_count >= max_dca or pnl_pct >= 0 or pnl_pct > trigger_pct:
                continue
            if time.time() - last_dca < cooldown_min * 60:
                continue

            dca_vol = pos["volume"] * (increment_factor**dca_count)
            total_cost = (pos["volume"] + dca_vol) * entry
            balance = paper_balance if paper_trading else 10000
            if (total_cost / balance) * 100 > position_limit_pct:
                continue

            pos["_dca_count"] = dca_count + 1
            pos["_last_dca_time"] = time.time()
            logger.info(f"DCA: Adding {dca_vol} to {pos['ticket']}")

            return {
                "ticket": pos["ticket"],
                "symbol": pos["symbol"],
                "side": pos["action"],
                "volume": dca_vol,
                "dca_count": pos["_dca_count"],
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
                price=dca_info.get("entry_price", 0),
                strategy="DCA",
                regime=current_regime,
            )
        return result
