"""Backtest service — backtesting and hyperparameter optimization orchestration.

Usage:
    service = BacktestService(config)
    results = service.run_backtest(data, strategy, name)
    best_params = service.run_hyperopt(strategy_cls, data, loss="sharpe")
"""

from typing import Any, Dict, Optional

import pandas as pd

from src.configuration.manager import ConfigManager
from src.backtesting.engine import Backtester
from src.backtesting.hyperopt import Hyperopt
from src.repositories.analytics_repo import AnalyticsRepository
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BacktestService:
    """Manages backtesting and hyperparameter optimization.

    Usage:
        service = BacktestService(config, analytics_repo)
        df = service.compare_all(data, strategies)
        best = service.run_hyperopt(MyStrategy, data)
    """

    def __init__(self, config: ConfigManager,
                 analytics_repo: Optional[AnalyticsRepository] = None):
        self.config = config
        self.analytics_repo = analytics_repo
        self.engine = Backtester(config)
        self.hyperopt = Hyperopt(config, self.engine)

    def run_backtest(self, data: pd.DataFrame, strategy,
                     strategy_name: str) -> Dict[str, Any]:
        """Run a single backtest for a given strategy."""
        return self.engine.run_strategy(data, strategy, strategy_name)

    def run_walk_forward(self, data: pd.DataFrame,
                          signal_generator,
                          strategy_name: str,
                           train_frac: float,
                           n_windows: int) -> Dict[str, Any]:
        """Run walk-forward validation."""
        return self.engine.run_walk_forward(
            data, signal_generator, strategy_name,
            train_frac=train_frac, n_windows=n_windows,
        )

    def compare_all(self, data: pd.DataFrame,
                    strategies: Dict[str, Any]) -> pd.DataFrame:
        """Run & compare all strategies, return sorted results DataFrame."""
        for name, strategy in strategies.items():
            try:
                self.run_backtest(data, strategy, name)
            except Exception as e:
                logger.error(f"Backtest failed for {name}: {e}")
        return self.engine.compare_strategies()

    def run_hyperopt(self, strategy_cls: type, data: pd.DataFrame,
                     loss: str,
                     n_calls: int) -> Any:
        """Run Bayesian hyperparameter optimization."""
        return self.hyperopt.optimize(
            strategy_cls, data, loss=loss, n_calls=n_calls,
        )

    def get_strategies_tested(self) -> list:
        """Get list of strategy names that have been tested."""
        return list(self.engine.results.keys())

    def has_results(self) -> bool:
        """Check if any backtest results exist."""
        return len(self.engine.results) > 0

    def num_results(self) -> int:
        """Get number of backtest results."""
        return len(self.engine.results)

