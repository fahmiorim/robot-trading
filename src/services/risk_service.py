"""Risk service — risk management, circuit breaker, trailing stop."""

from typing import Dict

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

    def __init__(self, config, risk_manager, protection_manager=None,
                 analytics_repo=None):
        self.config = config
        self.risk = risk_manager
        self.protections = protection_manager
        self.analytics_repo = analytics_repo

    def get_state(self) -> Dict:
        """Get current risk state."""
        return self.risk.get_state() if hasattr(self.risk, 'get_state') else {}

    def can_trade(self) -> bool:
        """Check if trading is allowed based on risk rules."""
        if not self.config.get("risk_management", "circuit_breaker_enabled"):
             # Basic limit check if CB is disabled
             summary = self.risk.get_status_summary()
             return summary.get('can_trade', True)

        try:
            cooldown = self.config.get("risk_management", "circuit_breaker_cooldown_minutes")
            if self.analytics_repo and self.analytics_repo.is_circuit_breaker_active(cooldown):
                logger.warning("Circuit breaker is active — trading paused")
                return False
                
            summary = self.risk.get_status_summary()
            return summary.get('can_trade', True)
        except Exception as e:
            logger.error(f"Risk check failed: {e}")
            return True

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
                "can_trade": summary.get("can_trade", True),
                "reason": summary.get("can_trade_reason", ""),
            }
        except Exception:
            return {"drawdown_pct": 0, "daily_loss_pct": 0, "can_trade": True}
