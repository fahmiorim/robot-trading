"""
Background worker — runs trading cycles on a timer.

Inspired by Freqtrade's Worker class.  Runs in a separate thread so
the dashboard and other services stay responsive.

Usage::

    worker = Worker(bot)
    worker.start()          # starts background thread
    worker.stop()           # stops gracefully
    worker.is_running       # bool
"""

import threading
import time
from typing import Optional

from src.services.trading.engine import TradingBot
from src.utils.logging import get_logger
from src.rpc.websocket import set_shared

logger = get_logger(__name__)


class Worker:
    """Background worker that runs trading cycles periodically.

    The worker checks auto_trade flag in config each cycle.
    When auto_trade is True, it runs a full trading cycle.
    """

    def __init__(self, bot: TradingBot):
        self.bot = bot
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self._cycle_results: list = []

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start the worker thread."""
        if self._running:
            return
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True,
                                        name="worker")
        self._thread.start()
        logger.info("Worker started")

    def stop(self) -> None:
        """Signal the worker to stop."""
        self._stop_event.set()
        self._running = False
        logger.info("Worker stopping...")

    def wait(self, timeout: Optional[float] = None) -> None:
        """Wait for the worker thread to finish."""
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    @property
    def last_result(self) -> Optional[dict]:
        return self._cycle_results[-1] if self._cycle_results else None

    def _run_loop(self) -> None:
        """Main worker loop."""
        logger.info("Worker loop started")

        while not self._stop_event.is_set():
            try:
                # Check if auto_trade is enabled
                auto = self.bot.config.get("general", "auto_trade")
                if auto:
                    logger.debug("Auto-trade enabled, running cycle...")
                    result = self.bot.run_cycle()
                    self._cycle_results.append(result)
                    # Log trade alerts
                    if result.get("success") and result.get("action") not in ("HOLD", None):
                        self.bot.rpc.send_trade_alert(
                            symbol=self.bot.symbol,
                            action=result.get("action", "?"),
                            price=result.get("price", 0),
                            strategy=self.bot.best_strategy_name or "N/A",
                            regime=self.bot.current_regime,
                        )
                else:
                    logger.debug("Auto-trade disabled, sleeping...")

                # Update shared state for WebSocket dashboard
                status = self.bot.status()
                set_shared("auto_trading", auto)
                set_shared("regime", status.get("current_regime", "unknown"))
                set_shared("best_strategy", status.get("best_strategy", "N/A"))
                set_shared("cycle_count", status.get("cycle_count", 0))
                set_shared("mt5_connected", status.get("connection", False))

            except Exception as e:
                logger.error(f"Worker cycle error: {e}")

            # Sleep for cycle interval
            interval = self.bot.config.get("general", "cycle_interval_minutes")
            for _ in range(int(interval * 60)):
                if self._stop_event.is_set():
                    break
                time.sleep(1)



