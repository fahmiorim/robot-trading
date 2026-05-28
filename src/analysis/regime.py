"""
Market regime detector — classifies market as trending, ranging, or choppy.

Uses ADX from shared indicators instead of duplicating the calculation.
"""
import numpy as np
import pandas as pd
from typing import Optional, Literal

from src.analysis.indicators import calculate_adx


DEFAULT_STRATEGY_WEIGHTS = {
    'trending': {'Breakout': 1.0, 'MA_Crossover': 0.8, 'MACD': 0.6, 'RSI': 0.3, 'Bollinger': 0.4},
    'ranging': {'Bollinger': 1.0, 'RSI': 0.9, 'MA_Crossover': 0.5, 'MACD': 0.4, 'Breakout': 0.2},
    'choppy': {'RSI': 0.8, 'Bollinger': 0.7, 'MACD': 0.5, 'MA_Crossover': 0.3, 'Breakout': 0.2},
}


class RegimeDetector:
    """Detects market regime (trending, ranging, choppy) from OHLCV data."""

    def __init__(self, adx_period: int = 14, adx_threshold: float = 25):
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.regime = 'unknown'

    def detect_regime(self, data: pd.DataFrame) -> Literal['trending', 'choppy', 'ranging']:
        """Classify the current market regime based on ADX and price action."""
        adx = calculate_adx(data['high'], data['low'], data['close'], self.adx_period)
        current_adx = adx.dropna().iloc[-1] if len(adx.dropna()) > 0 else 25

        x = np.arange(20)
        y = data['close'].iloc[-20:].values
        slope = np.polyfit(x, y, 1)[0]
        price_volatility = data['close'].pct_change().rolling(20).std().iloc[-1]
        normalized_slope = abs(slope) / (np.mean(y) + 1e-10) * 100

        if current_adx > self.adx_threshold and normalized_slope > 0.01:
            self.regime = 'trending'
        elif current_adx < self.adx_threshold and price_volatility < 0.003:
            self.regime = 'ranging'
        else:
            self.regime = 'choppy'
        return self.regime

    def get_strategy_weights(self, config: Optional[dict] = None) -> dict:
        """
        Return strategy weights for the current regime.

        If *config* is provided, user overrides are merged on top of defaults
        so users can tune weights via the dashboard / DB without touching code.
        """
        weights = dict(DEFAULT_STRATEGY_WEIGHTS.get(self.regime, DEFAULT_STRATEGY_WEIGHTS['choppy']))
        if config:
            weights.update(config.get(self.regime))
        return weights
