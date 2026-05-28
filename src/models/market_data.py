"""Market data domain models — pure data classes for OHLCV and market state."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from src.constants.trading import RegimeType


@dataclass
class OHLCV:
    """A single OHLCV candle."""
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    spread: int = 0

    def to_dict(self) -> Dict:
        return {
            "time": self.time, "open": self.open, "high": self.high,
            "low": self.low, "close": self.close, "volume": self.volume,
        }


@dataclass
class MarketFrame:
    """Container for a full OHLCV dataset with metadata."""
    symbol: str
    timeframe: str
    dataframe: Optional[pd.DataFrame] = None
    cached_at: Optional[datetime] = None

    @property
    def latest_close(self) -> Optional[float]:
        if self.dataframe is not None and len(self.dataframe) > 0:
            return float(self.dataframe["close"].iloc[-1])
        return None

    @property
    def count(self) -> int:
        return len(self.dataframe) if self.dataframe is not None else 0


@dataclass
class MarketRegime:
    """Market regime classification result."""
    regime: str          # trending / ranging / choppy / unknown
    adx: float = 0.0
    volatility: float = 0.0
    confidence: float = 0.0

    @property
    def is_trending(self) -> bool:
        return self.regime == RegimeType.TRENDING

    @property
    def is_ranging(self) -> bool:
        return self.regime == RegimeType.RANGING

    @property
    def is_choppy(self) -> bool:
        return self.regime == RegimeType.CHOPPY
