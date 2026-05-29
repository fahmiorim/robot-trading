"""Moving Average Crossover strategy."""
import pandas as pd
from src.strategy.interface import IStrategy
from src.analysis.indicators import calculate_sma


class MACrossoverStrategy(IStrategy):
    strategy_id = "MA_Crossover"
    param_space = {
        'fast_period': (3, 40, 'int'),
        'slow_period': (10, 80, 'int'),
    }

    def __init__(self, fast_period: int, slow_period: int):
        super().__init__(fast_period=fast_period, slow_period=slow_period)
        self.fast_period = fast_period
        self.slow_period = slow_period

    def calculate_signals(self, data: pd.DataFrame) -> pd.Series:
        fast_ma = calculate_sma(data['close'], self.fast_period)
        slow_ma = calculate_sma(data['close'], self.slow_period)
        signal = pd.Series(0, index=data.index)
        signal[fast_ma > slow_ma] = 1
        signal[fast_ma < slow_ma] = -1
        return signal.shift(1).fillna(0)
