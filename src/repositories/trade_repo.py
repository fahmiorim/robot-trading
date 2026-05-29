"""Trade repository — wraps TradingMixin and returns Trade domain models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.models.trade import Trade
from src.constants.trading import OrderSide, TradeStatus
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TradeRepository:
    """Repository for trade persistence. Wraps DatabaseManager's TradingMixin.

    Usage:
        repo = TradeRepository(db)
        repo.save(trade)
        trades = repo.find_all(limit=100)
    """

    def __init__(self, db):
        self._db = db

    # ── Write ──

    def save(self, trade: Trade) -> Optional[int]:
        """Persist a trade to the database."""
        return self._db.log_trade(trade.to_dict())

    def update_exit(self, ticket: int, exit_price: float, profit: float,
                    exit_time: Optional[datetime] = None) -> bool:
        """Update trade exit details (close trade)."""
        return self._db.update_trade_exit(ticket, exit_price, profit, exit_time)

    # ── Read ──

    def find_all(self, limit: int = 100, offset: int = 0) -> List[Trade]:
        """Get recent trade history as Trade objects."""
        rows = self._db.get_trade_history(limit=limit, offset=offset)
        return self._rows_to_trades(rows)

    def find_open(self) -> List[Trade]:
        """Get all open trades."""
        rows = self._db.get_open_trades()
        return self._rows_to_trades(rows)

    def find_by_ticket(self, ticket: int) -> Optional[Trade]:
        """Find a trade by ticket number."""
        row = self._db.get_trade_by_ticket(ticket)
        if row:
            return Trade.from_dict(row)
        return None

    def summary(self, days: int = 30) -> Dict[str, Any]:
        """Get aggregate trade statistics."""
        return self._db.get_trade_summary(days=days)

    def log_signal(self, signal_data: Dict[str, Any]) -> Optional[int]:
        """Log a signal entry."""
        return self._db.log_signal(signal_data)

    # ── Helpers ──

    @staticmethod
    def _rows_to_trades(rows: List[Dict]) -> List[Trade]:
        """Convert DB result rows to Trade objects."""
        trades = []
        for r in rows:
            try:
                trades.append(Trade.from_dict(r))
            except Exception as e:
                logger.warning(f"Failed to parse trade row: {e}")
        return trades
