"""Analysis controller — backtesting, hyperparameter optimization, and performance analysis.

Usage:
    ctrl = AnalysisController(config)
    results = ctrl.run_backtest_all(data, strategies)
    best = ctrl.run_hyperopt(MyStrategy, data)
    df = ctrl.get_comparison_df()
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from src.configuration.manager import ConfigManager
from src.models.backtest import HyperoptResult
from src.services.backtest_service import BacktestService
from src.repositories.analytics_repo import AnalyticsRepository
from src.repositories.trade_repo import TradeRepository
from src.persistence.database import get_db
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AnalysisController:
    """Thin orchestrator for backtesting, hyperopt, and performance queries."""

    def __init__(self, config: ConfigManager):
        self.config = config
        self._db = get_db()
        self.analytics_repo = AnalyticsRepository(self._db)
        self.trade_repo = TradeRepository(self._db)
        self.backtest_service = BacktestService(config, self.analytics_repo)

    # ── Backtesting ──

    def run_backtest(self, data: pd.DataFrame, strategy,
                     strategy_name: str) -> Dict[str, Any]:
        """Run a single backtest for a given strategy."""
        return self.backtest_service.run_backtest(data, strategy, strategy_name)

    def run_backtest_all(self, data: pd.DataFrame,
                         strategies: Dict[str, Any]) -> Dict[str, Any]:
        """Run backtest on all strategies and return results."""
        return self.backtest_service.compare_all(data, strategies)

    def run_walk_forward(self, data: pd.DataFrame,
                          signal_generator,
                          strategy_name: str,
                          train_frac: float = 0.7,
                          n_windows: int = 3) -> Dict[str, Any]:
        """Run walk-forward validation."""
        return self.backtest_service.run_walk_forward(
            data, signal_generator, strategy_name,
            train_frac=train_frac, n_windows=n_windows,
        )

    def get_comparison_df(self) -> pd.DataFrame:
        """Get DataFrame comparing strategy backtest results."""
        return self.backtest_service.engine.compare_strategies()

    # ── Hyperparameter Optimization ──

    def run_hyperopt(self, strategy_cls: type, data: pd.DataFrame,
                     loss: str = "sharpe",
                     n_calls: int = 30) -> Any:
        """Run Bayesian hyperparameter optimization."""
        return self.backtest_service.run_hyperopt(
            strategy_cls, data, loss=loss, n_calls=n_calls,
        )

    # ── Analytics Queries ──

    def get_trade_history(self, limit: int = 100,
                          offset: int = 0) -> List[Dict]:
        """Get trade history from repository."""
        return self.trade_repo.get_trade_history(limit=limit, offset=offset)

    def get_open_trades(self) -> List[Dict]:
        """Get currently open trades."""
        return self.trade_repo.get_open_trades()

    def get_trade_summary(self, days: int = 7) -> Dict:
        """Get trade summary statistics."""
        return self.trade_repo.get_trade_summary(days=days)

    def get_equity_curve(self, days: int = 30) -> List[Dict]:
        """Get equity curve data."""
        return self.analytics_repo.get_equity_curve(days=days)

    def get_best_hyperopt_params(self, strategy_name: str) -> Optional[HyperoptResult]:
        """Get best hyperopt params for a strategy."""
        return self.analytics_repo.find_best_hyperopt_params(strategy_name)

    def get_all_hyperopt_results(self) -> List[HyperoptResult]:
        """Get all hyperopt results as domain models."""
        return self.analytics_repo.find_all_hyperopt_results()

    def is_circuit_breaker_active(self) -> bool:
        """Check if circuit breaker is active."""
        return self.analytics_repo.is_circuit_breaker_active()

    # ── Performance Logging ──

    def log_performance(self, perf: Dict[str, Any]) -> bool:
        """Log a performance snapshot."""
        return self.analytics_repo.log_performance(perf)

    def save_equity_snapshot(self, balance: float, equity: Optional[float] = None) -> bool:
        """Save equity snapshot."""
        return self.analytics_repo.save_equity_snapshot(balance, equity)

    # ── Status ──

    def get_status(self) -> Dict:
        """Get controller status."""
        return {
            "has_results": self.backtest_service.has_results(),
            "num_results": self.backtest_service.num_results(),
            "strategies_tested": self.backtest_service.get_strategies_tested(),
        }
