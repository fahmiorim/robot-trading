"""
Trading engine — backward-compatible wrapper around TradingController.

``TradingBot`` now inherits from ``TradingController``, delegating all core logic
to the MVC services layer while keeping the exact same public API.

Usage::

    bot = TradingBot()
    bot.run_cycle()           # single cycle  (from TradingController)
    bot.run_trading_cycle()   # alias (backward compat)
    bot.status()              # get full status dict
"""

from typing import Dict, Optional

from src.controllers.trading_controller import TradingController
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TradingBot(TradingController):
    """Backward-compatible wrapper around TradingController.

    Maintains the exact same public API as the original ``TradingBot``
    while delegating all core logic to ``TradingController`` services.
    Only the thin extra layer that legacy callers depend on lives here.
    """

    def __init__(self, config=None, bypass_lock=False):
        super().__init__(config=config, bypass_lock=bypass_lock)

        # Backward-compat: some callers reference signal_aggregator directly
        # Alias to the real signal_service so both APIs stay in sync
        self.signal_aggregator = self.signal_service

        # Extra state that only the original TradingBot tracked
        self._dca_tracker: Dict[str, int] = {}
        self._dca_timestamps: Dict[str, float] = {}
        self._last_signals: Dict[str, int] = {}

        logger.info(f"TradingBot (wrapper) ready — delegating to controller")

    # ── Method aliases ─────────────────────────────────────

    def run_trading_cycle(self, force_refresh: bool = False) -> Dict:
        """Alias for ``run_cycle()`` — kept for backward compatibility.
        """
        return self.run_cycle(force_refresh=force_refresh)

    def get_signal(self, data, use_ml=False, use_agent=False, use_swarm=False) -> int:
        """Override to also store ``_last_signals`` for backward compat."""
        sig = super().get_signal(
            data, use_ml=use_ml, use_agent=use_agent, use_swarm=use_swarm,
        )
        self._last_signals = self.signal_service.get_last_signals()
        return sig

    def _get_roi_price(self, entry_price: float, side: str,
                       position_time_minutes: float) -> Optional[float]:
        """Backward-compat: delegate to roi_manager via trade_execution_service."""
        return self.trade_execution_service.roi_manager.get_roi_price(
            entry_price, side, position_time_minutes,
        )

    # ── Status ──────────────────────────────────────────────

    def status(self) -> Dict:
        """Status dict using the same keys as the original TradingBot.

        Delegates to ``TradingController.status()`` instead of duplicating.
        """
        return super().status()

    # ── Cleanup ─────────────────────────────────────────────

    def cleanup(self):
        """Shutdown — delegates to TradingController.cleanup() and logs."""
        logger.info("Shutting down TradingBot (wrapper)...")
        super().cleanup()
        logger.info("TradingBot shutdown complete")


# ── Backward compatibility aliases ──────────────────────────
TradingEngine = TradingBot

# New MVC controller alias (v2.2.0+)
TradingControllerV2 = TradingController
