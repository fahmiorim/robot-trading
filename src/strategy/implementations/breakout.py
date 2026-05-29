"""Price Breakout strategy."""
import pandas as pd
from src.strategy.interface import IStrategy


class BreakoutStrategy(IStrategy):
    strategy_id = "Breakout"
    param_space = {
        'lookback': (5, 50, 'int'),
    }

    def __init__(self, lookback: int):
        super().__init__(lookback=lookback)
        self.lookback = lookback

    def calculate_signals(self, data: pd.DataFrame) -> pd.Series:
        high_max = data['high'].rolling(self.lookback).max()
        low_min = data['low'].rolling(self.lookback).min()
        signal = pd.Series(0, index=data.index)
        signal[data['close'] > high_max.shift(1)] = 1
        signal[data['close'] < low_min.shift(1)] = -1
        return signal.fillna(0)
