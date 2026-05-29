"""Market data repository — wraps MarketDataMixin for OHLCV cache."""

from typing import Optional

import pandas as pd

from src.utils.logging import get_logger

logger = get_logger(__name__)


class MarketDataRepository:
    """Repository for cached market data (OHLCV).

    Usage:
        repo = MarketDataRepository(db)
        df = repo.load("XAUUSD", "TIMEFRAME_M15", limit=2000)
        repo.save("XAUUSD", "TIMEFRAME_M15", new_candles)
    """

    def __init__(self, db):
        self._db = db

    def load(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """Load cached market data from database."""
        return self._db.load_market_data(symbol, timeframe, limit=limit)

    def save(self, symbol: str, timeframe: str, df: pd.DataFrame) -> bool:
        """Save market data to database cache."""
        return self._db.save_market_data(symbol, timeframe, df)

    def delete_old(self, symbol: str, timeframe: str, keep_count: int) -> bool:
        """Delete old candles, keeping only the most recent keep_count."""
        try:
            df = self.load(symbol, timeframe, limit=keep_count + 100)
            if df is not None and len(df) > keep_count:
                # Re-save only the latest keep_count rows
                self.save(symbol, timeframe, df.tail(keep_count))
            return True
        except Exception as e:
            logger.error(f"Failed to trim market data: {e}")
            return False
