"""Risk service — risk management, circuit breaker, trailing stop."""

from typing import Any, Dict, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class RiskService:
    """Manages risk state, drawdown tracking, trailing stops, and circuit breaker.

    Usage:
        service = RiskService(config, risk_manager, protection_manager)
        state = service.get_state()
        service.check_circuit_breaker()
        service.update_trailing_stops()
    """

    def __init__(self, risk_manager, protection_manager=None,
                 analytics_repo=None):
        self.risk = risk_manager
        self.protections = protection_manager
        self.analytics_repo = analytics_repo

    def get_state(self) -> Dict:
        """Get current risk state."""
        return self.risk.get_state() if hasattr(self.risk, 'get_state') else {}

    def can_trade(self) -> bool:
        """Check if trading is allowed based on risk rules."""
        try:
            summary = self.risk.get_status_summary()
            return summary.get('can_trade', (True, ''))[0]
        except Exception:
            return True

    def check_circuit_breaker(self, drawdown_pct: float = None,
                              balance_before: float = None,
                              balance_after: float = None) -> bool:
        """Check and trigger circuit breaker if needed."""
        if not self.analytics_repo:
            return False

        is_active = self.analytics_repo.is_circuit_breaker_active()
        if is_active:
            logger.warning("Circuit breaker is active — trading paused")
            return True

        if drawdown_pct and drawdown_pct > 20:
            self.analytics_repo.log_circuit_breaker(
                reason=f"Drawdown exceeded: {drawdown_pct:.1f}%",
                drawdown_pct=drawdown_pct,
                balance_before=balance_before,
                balance_after=balance_after,
            )
            logger.warning(f"Circuit breaker triggered at {drawdown_pct:.1f}% drawdown")
            return True

        return False

    def update_trailing_stops(self, exchange=None, symbol: str = None) -> None:
        """Update trailing stops for open positions."""
        try:
            if hasattr(self.risk, 'update_trailing_stops'):
                self.risk.update_trailing_stops()
        except Exception as e:
            logger.warning(f"Trailing stop update failed: {e}")

    def get_daily_stats(self) -> Dict:
        """Get daily trading statistics."""
        try:
            summary = self.risk.get_status_summary()
            return {
                "drawdown_pct": summary.get("drawdown_pct", 0),
                "daily_loss_pct": summary.get("daily_loss_pct", 0),
                "can_trade": summary.get("can_trade", (True, ""))[0],
                "reason": summary.get("can_trade", (True, ""))[1],
            }
        except Exception:
            return {"drawdown_pct": 0, "daily_loss_pct": 0, "can_trade": True}
