"""Cycle service — business logic for background trading cycles.

Extracted from the old ``Worker._run_loop()`` so that ``Worker`` only
manages the thread lifecycle while ``CycleService`` owns *what* happens
each cycle.

Usage::

    service = CycleService()
    service.execute_cycle(bot)   # one full iteration
    service.last_result          # dict or None
"""

import time
from typing import Any, Dict, Optional

from src.rpc.websocket import set_shared
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CycleService:
    """Business logic executed each cycle iteration.

    Owns the cycle result buffer and the *how* of running a cycle,
    updating WebSocket shared state, and sending trade alerts.
    """

    def __init__(self):
        self._cycle_results: list = []

    # ── Public API ──────────────────────────────────────────

    @property
    def last_result(self) -> Optional[Dict[str, Any]]:
        return self._cycle_results[-1] if self._cycle_results else None

    @property
    def cycle_results(self) -> list:
        """Read-only view of recent cycle results."""
        return list(self._cycle_results)

    def ensure_thread_db(self) -> None:
        """Establish a DB connection for the current thread.

        ``DatabaseManager`` uses ``threading.local()``, so each thread
        gets its own connection.  Call this once at the start of a
        background thread to warm the connection before the first cycle.
        """
        try:
            from src.persistence.database import get_db
            get_db().connect()
        except Exception:
            pass

    def execute_cycle(self, bot) -> Dict[str, Any]:
        """Run one cycle iteration and update shared state.

        Returns the status dict produced by the cycle.
        """
        # ── 1. Check auto-trade flag ──
        auto = bot.config.get("general", "auto_trade")

        # ── 2. Run the actual trading cycle ──
        if auto:
            logger.debug("Auto-trade enabled, running cycle...")
            result = bot.run_cycle()
            self._track_result(result)

            # Send trade alert for non-HOLD actions
            if result.get("success") and result.get("action") not in ("HOLD", None):
                self._send_trade_alert(bot, result)
        else:
            logger.debug("Auto-trade disabled, sleeping...")
            result = {"success": True, "action": "HOLD (disabled)", "cycle": self._cycle_count(bot)}

        # ── 3. Update WebSocket shared state ──
        self._update_shared_state(bot, auto)

        return result

    def sleep_for_interval(self, bot, cycle_start: float,
                           should_stop=None) -> None:
        """Sleep until the next cycle, respecting the configured interval.

        Args:
            bot: TradingBot instance (for config lookup).
            cycle_start: ``time.time()`` at the start of the current cycle.
            should_stop: Optional zero-arg callable returning ``True`` when
                         the caller wants to abort the sleep (e.g. a
                         ``threading.Event.is_set`` check).

        Returns early if ``should_stop`` returns ``True``.
        """
        interval = bot.config.get("general", "cycle_interval_minutes")
        elapsed = time.time() - cycle_start
        wait_time = max(1, (interval * 60) - elapsed)

        for _ in range(int(wait_time)):
            if should_stop and should_stop():
                return
            time.sleep(1)

    # ── Internal helpers ────────────────────────────────────

    def _track_result(self, result: Dict[str, Any]) -> None:
        self._cycle_results.append(result)
        # Keep only last 100 results to prevent memory leak
        if len(self._cycle_results) > 100:
            self._cycle_results.pop(0)

    def _send_trade_alert(self, bot, result: Dict[str, Any]) -> None:
        """Send a trade alert via RPC when a real action occurred."""
        try:
            bot.rpc.send_trade_alert(
                symbol=bot.symbol,
                action=result.get("action", "?"),
                price=result.get("price", 0),
                strategy=bot.best_strategy_name or "N/A",
                regime=bot.current_regime,
            )
        except Exception as e:
            logger.warning(f"Failed to send trade alert: {e}")

    def _update_shared_state(self, bot, auto: bool) -> None:
        """Push latest bot status to cross-thread shared state for WebSocket."""
        try:
            status = bot.status()
            set_shared("auto_trading", auto)
            set_shared("regime", status.get("current_regime", "unknown"))
            set_shared("best_strategy", status.get("best_strategy", "N/A"))
            set_shared("cycle_count", status.get("cycle_count", 0))
            set_shared("mt5_connected", status.get("connection", False))
        except Exception as e:
            logger.warning(f"Failed to update shared state: {e}")

    @staticmethod
    def _cycle_count(bot) -> int:
        try:
            return bot.system_service.cycle_count
        except Exception:
            return 0
