"""
Strategy interface — inspired by Freqtrade's ``IStrategy``.

All strategies inherit from ``IStrategy`` and are auto-discovered via the
``__init_subclass__`` pattern.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Type

import pandas as pd

from src.constants import SignalType


class IStrategy(ABC):
    """Abstract base for all trading strategies.

    Subclasses are auto-registered when they define a ``strategy_id`` class attribute.
    No manual registration required.

    Optional ``param_space`` enables hyperopt parameter optimisation.
    """

    _registry: Dict[str, Type["IStrategy"]] = {}

    # Override in subclass
    strategy_id: str = ""

    # Optional: {(param_name, (min, max, type))}
    # type can be 'int', 'float', or 'categorical'
    param_space: Dict[str, Tuple] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        sid = getattr(cls, "strategy_id", None)
        if sid:
            IStrategy._registry[sid] = cls

    def __init__(self, **params):
        self.name = self.__class__.__name__
        self.params: Dict[str, Any] = params

    @classmethod
    def get_registry(cls) -> Dict[str, Type["IStrategy"]]:
        return dict(cls._registry)

    @abstractmethod
    def calculate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Return a Series of signals: 1=BUY, -1=SELL, 0=HOLD."""
        ...

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Alias for calculate_signals (compatibility)."""
        return self.calculate_signals(data)

    def get_params(self) -> Dict[str, Any]:
        return dict(self.params)


def create_strategies_from_config(config: "ConfigManager") -> Dict[str, IStrategy]:
    """Instantiate strategies from config using the auto-discovered registry.

    Reads enabled/disabled status and per-strategy parameters from config.
    """
    registry = IStrategy.get_registry()
    strategies: Dict[str, IStrategy] = {}
    for name, cls in registry.items():
        params = config.get("strategies", name)
        if not isinstance(params, dict):
            continue
        if not params.get("enabled", True):
            continue
        filtered = {k: v for k, v in params.items() if k != "enabled"}
        strategies[name] = cls(**filtered)
    return strategies
