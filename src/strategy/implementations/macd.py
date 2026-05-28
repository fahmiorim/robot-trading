"""MACD crossover strategy."""
import pandas as pd
from src.strategy.interface import IStrategy
from src.analysis.indicators import calculate_ema


class MACDStrategy(IStrategy):
    strategy_id = "MACD"
    param_space = {
        'fast': (8, 20, 'int'),
        'slow': (20, 40, 'int'),
        'signal': (5, 15, 'int'),
    }

    def __init__(self, fast: int, slow: int, signal: int):
        super().__init__(fast=fast, slow=slow, signal=signal)
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def calculate_signals(self, data: pd.DataFrame) -> pd.Series:
        exp1 = calculate_ema(data['close'], self.fast)
        exp2 = calculate_ema(data['close'], self.slow)
        macd = exp1 - exp2
        signal_line = calculate_ema(macd, self.signal)
        signal = pd.Series(0, index=data.index)
        signal[macd > signal_line] = 1
        signal[macd < signal_line] = -1
        return signal.shift(1).fillna(0)
