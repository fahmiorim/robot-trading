"""Risk state repository — wraps RiskStateMixin for risk persistence."""

from typing import Any, Dict, Optional

from src.models.risk import RiskState
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RiskRepository:
    """Repository for risk state persistence.

    Usage:
        repo = RiskRepository(db)
        state = repo.load()
        repo.save_state(symbol="XAUUSD", initial_balance=10000.0)
    """

    def __init__(self, db):
        self._db = db

    def save_state(self, symbol: str, initial_balance: Optional[float],
                   peak_balance: Optional[float],
                   daily_start_balance: Optional[float]) -> bool:
        """Save current risk state to database."""
        return self._db.save_risk_state(
            symbol=symbol,
            initial_balance=initial_balance,
            peak_balance=peak_balance,
            daily_start_balance=daily_start_balance,
        )

    def load(self) -> Optional[RiskState]:
        """Load risk state from database as a RiskState model."""
        data = self._db.load_risk_state()
        if data:
            try:
                return RiskState(
                    symbol=data.get("symbol", "XAUUSD"),
                    initial_balance=float(data["initial_balance"]) if data.get("initial_balance") is not None else None,
                    peak_balance=float(data["peak_balance"]) if data.get("peak_balance") is not None else None,
                    daily_start_balance=float(data["daily_start_balance"]) if data.get("daily_start_balance") is not None else None,
                )
            except Exception as e:
                logger.error(f"Failed to parse RiskState: {e}")
        return None
