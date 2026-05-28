"""Trading strategy package."""
from src.strategy.interface import IStrategy, create_strategies_from_config
from src.strategy.implementations import (
    BreakoutStrategy, MACrossoverStrategy, RSIStrategy,
    MACDStrategy, BollingerStrategy,
)

__all__ = [
    "IStrategy", "create_strategies_from_config",
    "BreakoutStrategy", "MACrossoverStrategy", "RSIStrategy",
    "MACDStrategy", "BollingerStrategy",
]
