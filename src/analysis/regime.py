"""
Market regime detector — classifies market as trending, ranging, or choppy.

Uses ADX from shared indicators instead of duplicating the calculation.
"""
import numpy as np
import pandas as pd
from typing import Optional

from src.analysis.indicators import calculate_adx


class RegimeDetector:
    """Detects market regime (trending, ranging, choppy) from OHLCV data."""

    def __init__(self, adx_period: int, adx_threshold: float,
                 window_size: int, slope_threshold: float,
                 volatility_threshold: float):
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.window_size = window_size
        self.slope_threshold = slope_threshold
        self.volatility_threshold = volatility_threshold
        self.regime = 'unknown'

    def detect_regime(self, data: pd.DataFrame) -> str:
        """Classify the current market regime based on ADX and price action."""
        if len(data) < max(self.adx_period * 2, self.window_size):
            return 'unknown'

        adx = calculate_adx(data['high'], data['low'], data['close'], self.adx_period)
        clean = adx.dropna()
        if len(clean) == 0:
            return 'unknown'
        current_adx = clean.iloc[-1]

        x = np.arange(self.window_size)
        y = data['close'].iloc[-self.window_size:].values
        if len(y) < self.window_size:
            return 'unknown'
            
        slope = np.polyfit(x, y, 1)[0]
        price_volatility_series = data['close'].pct_change().rolling(self.window_size).std()
        if len(price_volatility_series.dropna()) == 0:
            return 'unknown'
            
        price_volatility = price_volatility_series.iloc[-1]
        normalized_slope = abs(slope) / (np.mean(y) + 1e-10) * 100

        if current_adx > self.adx_threshold and normalized_slope > self.slope_threshold:
            self.regime = 'trending'
        elif current_adx < self.adx_threshold and price_volatility < self.volatility_threshold:
            self.regime = 'ranging'
        else:
            self.regime = 'choppy'
        return self.regime
