"""
Background worker — runs trading cycles on a timer.

Inspired by Freqtrade's Worker class.  Runs in a separate thread so
the dashboard and other services stay responsive.

Usage::

    worker = Worker(bot)
    worker.start()          # starts background thread
    worker.stop()           # stops gracefully
    worker.is_running       # bool

.. versionchanged:: 2.3
   Business logic extracted to ``CycleService``.  ``Worker`` now only
   manages the thread lifecycle.
"""

import threading
from typing import Optional

from src.services.trading.engine import TradingBot
from src.services.cycle_service import CycleService
from src.utils.logging import get_logger

logger = get_logger(__name__)


class Worker:
    """Background worker — thread lifecycle only.

    Delegates cycle business logic to ``CycleService``, keeping the
    thread management (start/stop/join) separate from *what* happens
    each cycle.
    """

    def __init__(self, bot: TradingBot,
                 cycle_service: Optional[CycleService] = None):
        self.bot = bot
        self._cycle_service = cycle_service or CycleService()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_result(self) -> Optional[dict]:
        """Delegated to CycleService."""
        return self._cycle_service.last_result

    @property
    def cycle_results(self) -> list:
        """Delegated to CycleService."""
        return self._cycle_service.cycle_results

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
        """Signal the worker to stop and wait for thread to finish."""
        self._stop_event.set()
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        logger.info("Worker stopped")

    def wait(self, timeout: Optional[float] = None) -> None:
        """Wait for the worker thread to finish."""
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def _run_loop(self) -> None:
        """Main worker loop — delegates business logic to CycleService."""
        logger.info("Worker loop started")

        # Warm the DB connection for this thread (threading.local).
        self._cycle_service.ensure_thread_db()

        while not self._stop_event.is_set():
            cycle_start = time.time()
            try:
                self._cycle_service.execute_cycle(self.bot)
            except Exception as e:
                logger.error(f"Worker cycle error: {e}")

            self._cycle_service.sleep_for_interval(
                self.bot, cycle_start,
                should_stop=lambda: self._stop_event.is_set(),
            )
