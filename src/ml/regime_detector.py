import numpy as np
import pandas as pd
from typing import Optional, Literal


DEFAULT_STRATEGY_WEIGHTS = {
    'trending': {'Breakout': 1.0, 'MA_Crossover': 0.8, 'MACD': 0.6, 'RSI': 0.3, 'Bollinger': 0.4},
    'ranging': {'Bollinger': 1.0, 'RSI': 0.9, 'MA_Crossover': 0.5, 'MACD': 0.4, 'Breakout': 0.2},
    'choppy': {'RSI': 0.8, 'Bollinger': 0.7, 'MACD': 0.5, 'MA_Crossover': 0.3, 'Breakout': 0.2},
}


class RegimeDetector:
    def __init__(self, adx_period: int = 14, adx_threshold: float = 25):
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.regime = 'unknown'

    def calculate_adx(self, data: pd.DataFrame) -> pd.Series:
        high = data['high']
        low = data['low']
        close = data['close']
        plus_dm = (high - high.shift(1)).clip(lower=0)
        minus_dm = (low.shift(1) - low).clip(lower=0)
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        plus_di = 100 * (plus_dm / (tr + 1e-10)).rolling(self.adx_period).mean()
        minus_di = 100 * (minus_dm / (tr + 1e-10)).rolling(self.adx_period).mean()
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.ewm(span=self.adx_period).mean()
        return adx

    def detect_regime(self, data: pd.DataFrame) -> Literal['trending', 'choppy', 'ranging']:
        adx = self.calculate_adx(data)
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

        If *config* (a dict, e.g. ``config.to_dict().get("strategy_weights", {})``)
        is provided, those overrides are merged on top of the built-in defaults so
        users can tune weights via the dashboard / DB without touching code.
        """
        weights = dict(DEFAULT_STRATEGY_WEIGHTS.get(self.regime, DEFAULT_STRATEGY_WEIGHTS['choppy']))
        if config:
            weights.update(config.get(self.regime))
        return weights
