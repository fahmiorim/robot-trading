"""RSI Overbought/Oversold strategy."""
import pandas as pd
from src.strategy.interface import IStrategy
from src.analysis.indicators import calculate_rsi


class RSIStrategy(IStrategy):
    strategy_id = "RSI"
    param_space = {
        'period': (7, 21, 'int'),
        'overbought': (60, 85, 'int'),
        'oversold': (15, 40, 'int'),
    }

    def __init__(self, period: int, overbought: int, oversold: int):
        super().__init__(period=period, overbought=overbought, oversold=oversold)
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def calculate_signals(self, data: pd.DataFrame) -> pd.Series:
        rsi = calculate_rsi(data['close'], self.period)
        signal = pd.Series(0, index=data.index)
        signal[rsi < self.oversold] = 1
        signal[rsi > self.overbought] = -1
        return signal.fillna(0)
