"""Concrete strategy implementations. Import to trigger auto-registration."""
from src.strategy.implementations.breakout import BreakoutStrategy
from src.strategy.implementations.ma_crossover import MACrossoverStrategy
from src.strategy.implementations.rsi import RSIStrategy
from src.strategy.implementations.macd import MACDStrategy
from src.strategy.implementations.bollinger import BollingerStrategy

__all__ = [
    "BreakoutStrategy",
    "MACrossoverStrategy",
    "RSIStrategy",
    "MACDStrategy",
    "BollingerStrategy",
]
