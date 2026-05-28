"""
Data provider — fetch, cache, and serve OHLCV market data.

Inspired by Freqtrade's DataProvider: provides a clean API for strategies
and the bot to access price data without worrying about the source.

Supports:
- Incremental fetch from MT5 (only new candles since last fetch)
- DB cache (MySQL market_data table) for persistence across restarts
- In-memory hot cache (fast lookup within same timeframe window)
"""
import time
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from src.utils.exceptions import DataFetchError
from src.exchange.base import IExchange
from src.persistence.database import get_db
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Global in-memory cache
_data_cache: Dict[str, Dict] = {}


class DataProvider:
    """Provides market data to the trading bot.

    Uses a 3-tier cache:
        1. In-memory dict (fastest, intra-cycle)
        2. MySQL market_data table (persistent across restarts)
        3. MT5 exchange (source of truth)
    """

    def __init__(self, exchange: IExchange, symbol: str = "XAUUSD",
                 timeframe: str = "TIMEFRAME_M15", default_count: int = 2000):
        self.exchange = exchange
        self.symbol = symbol
        self.timeframe = timeframe
        self.default_count = default_count
        self._last_data: Optional[pd.DataFrame] = None

    # ── Public API ────────────────────────────────────────────

    def fetch(self, count: Optional[int] = None,
              force_refresh: bool = False) -> pd.DataFrame:
        """Fetch OHLCV data with 3-tier caching.

        Args:
            count: Number of candles to fetch (default from config).
            force_refresh: Skip cache, fetch fresh from MT5.

        Returns:
            DataFrame with columns [open, high, low, close, volume] and datetime index.
        """
        count = count or self.default_count

        # 1. In-memory hot cache
        cached = self._check_memory_cache(count)
        if cached is not None and not force_refresh:
            self._last_data = cached
            return cached

        # 2. DB cache
        df = self._load_from_db(count)

        if df is not None and not force_refresh:
            # Incremental fetch from MT5 for new candles only
            df = self._incremental_fetch(df, count)
            self._update_memory_cache(df, count)
            self._last_data = df
            return df

        # 3. Full fetch from MT5
        df = self._full_fetch_from_exchange(count)
        self._update_memory_cache(df, count)
        self._last_data = df
        return df

    @property
    def last_data(self) -> Optional[pd.DataFrame]:
        return self._last_data

    def ohlcv(self, column: str = "close") -> pd.Series:
        """Convenience: get a single price column from last fetched data."""
        if self._last_data is None or column not in self._last_data.columns:
            return pd.Series(dtype=float)
        return self._last_data[column]

    def clear_cache(self) -> None:
        _data_cache.clear()
        self._last_data = None
        logger.info("Data cache cleared")

    # ── Cache Tiers ───────────────────────────────────────────

    def _check_memory_cache(self, count: int) -> Optional[pd.DataFrame]:
        cache_key = self._cache_key(count)
        cached = _data_cache.get(cache_key)
        if cached is None:
            return None
        age = time.time() - cached["timestamp"]
        # Invalidate after half the timeframe interval
        max_age = self._timeframe_seconds() // 2
        if age > max_age:
            return None
        if len(cached["data"]) < count:
            return None
        logger.debug(f"Memory cache hit ({age:.0f}s old)")
        return cached["data"]

    def _update_memory_cache(self, df: pd.DataFrame, count: int) -> None:
        cache_key = self._cache_key(count)
        _data_cache[cache_key] = {
            "data": df,
            "timestamp": time.time(),
            "last_candle_time": df.index[-1] if len(df) > 0 else None,
        }

    def _load_from_db(self, count: int) -> Optional[pd.DataFrame]:
        try:
            db = get_db()
            df = db.load_market_data(self.symbol, self.timeframe, limit=count)
            if df is not None and len(df) > 0:
                logger.debug(f"DB cache: {len(df)} candles for {self.symbol}")
                return df
        except Exception as e:
            logger.warning(f"DB load failed: {e}")
        return None

    def _incremental_fetch(self, df: pd.DataFrame, count: int) -> pd.DataFrame:
        """Fetch only new candles from MT5 and merge with existing data."""
        latest = df.index[-1]
        if not isinstance(latest, datetime):
            latest = latest.to_pydatetime()

        try:
            rates = self.exchange.fetch_ohlcv(
                self.symbol, self.timeframe, count=count
            )
            if rates is not None and len(rates) > 0:
                new = rates[rates.index > latest]
                if len(new) > 0:
                    logger.info(f"Incremental: {len(new)} new candles")
                    df = pd.concat([df, new])
                    df = df[~df.index.duplicated(keep="last")].iloc[-count:]

                    # Save new candles to DB
                    try:
                        get_db().save_market_data(self.symbol, self.timeframe, new)
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Incremental fetch failed: {e}")

        return df

    def _full_fetch_from_exchange(self, count: int) -> pd.DataFrame:
        """Fetch full dataset from exchange and save to DB."""
        logger.info(f"Full fetch: {self.symbol} {self.timeframe} ({count} candles)")
        try:
            df = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, count=count)
        except Exception as e:
            raise DataFetchError(f"Exchange fetch failed: {e}") from e

        if df is None or len(df) == 0:
            raise DataFetchError(f"No data received for {self.symbol}")

        # Save to DB
        try:
            get_db().save_market_data(self.symbol, self.timeframe, df)
        except Exception as e:
            logger.warning(f"Failed to save market data to DB: {e}")

        return df

    # ── Helpers ───────────────────────────────────────────────

    def _cache_key(self, count: int) -> str:
        return f"{self.symbol}_{self.timeframe}_{count}"

    def _timeframe_seconds(self) -> int:
        from src.constants import TIMEFRAME_MAP
        minutes = TIMEFRAME_MAP.get(self.timeframe, 15)
        return minutes * 60
