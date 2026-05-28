"""Bollinger Bands reversal strategy."""
import pandas as pd
from src.strategy.interface import IStrategy
from src.analysis.indicators import calculate_bollinger_bands


class BollingerStrategy(IStrategy):
    strategy_id = "Bollinger"
    param_space = {
        'period': (10, 30, 'int'),
        'std_dev': (1.5, 3.0, 'float'),
    }

    def __init__(self, period: int, std_dev: float):
        super().__init__(period=period, std_dev=std_dev)
        self.period = period
        self.std_dev = std_dev

    def calculate_signals(self, data: pd.DataFrame) -> pd.Series:
        _, upper, lower = calculate_bollinger_bands(data['close'], self.period, self.std_dev)
        signal = pd.Series(0, index=data.index)
        signal[data['close'] < lower] = 1
        signal[data['close'] > upper] = -1
        return signal.fillna(0)
