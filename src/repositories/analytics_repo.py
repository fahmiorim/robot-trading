"""Analytics repository — wraps AnalyticsMixin for performance/equity/hyperopt."""

from typing import Any, Dict, List, Optional

from src.models.backtest import HyperoptResult
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AnalyticsRepository:
    """Repository for analytics data (performance, equity, circuit breaker, hyperopt).

    Usage:
        repo = AnalyticsRepository(db)
        repo.log_performance({...})
        results = repo.find_hyperopt_results()
    """

    def __init__(self, db):
        self._db = db

    # ── Performance ──

    def log_performance(self, perf: Dict[str, Any]) -> bool:
        return self._db.log_performance(perf)

    # ── Equity ──

    def save_equity_snapshot(self, balance: float, equity: Optional[float] = None,
                             drawdown_pct: Optional[float] = None) -> bool:
        return self._db.save_equity_snapshot(balance, equity, drawdown_pct)

    def get_equity_curve(self, days: int = 30) -> List[Dict]:
        return self._db.get_equity_curve(days=days)

    # ── Config Snapshots ──

    def save_config_snapshot(self, config_dict: Dict, notes: str = "") -> bool:
        return self._db.save_config_snapshot(config_dict, notes)

    # ── Circuit Breaker ──

    def log_circuit_breaker(self, reason: str, drawdown_pct: Optional[float] = None,
                            balance_before: Optional[float] = None,
                            balance_after: Optional[float] = None) -> Optional[int]:
        return self._db.log_circuit_breaker(reason, drawdown_pct, balance_before, balance_after)

    def is_circuit_breaker_active(self, cooldown_minutes: int = 120) -> bool:
        return self._db.is_circuit_breaker_active(cooldown_minutes)

    # ── Hyperopt ──

    def save_hyperopt_result(self, result: HyperoptResult) -> bool:
        """Persist a HyperoptResult to the database."""
        return self._db.save_hyperopt_result(
            strategy_name=result.strategy_name,
            params=result.best_params,
            score=result.best_score,
            metrics=result.metrics,
            n_trials=result.n_trials,
            elapsed=result.elapsed_seconds,
        )

    def find_best_hyperopt_params(self, strategy_name: str) -> Optional[HyperoptResult]:
        """Get best hyperopt params as a HyperoptResult model."""
        data = self._db.get_best_hyperopt_params(strategy_name)
        if data:
            try:
                return HyperoptResult(
                    strategy_name=data.get("strategy_name", strategy_name),
                    best_params=data.get("best_params", {}),
                    best_score=float(data.get("best_score", 0)),
                    metrics=data.get("metrics", {}),
                    n_trials=int(data.get("n_trials", 0)),
                    elapsed_seconds=float(data.get("elapsed_seconds", 0)),
                )
            except Exception as e:
                logger.warning(f"Failed to parse hyperopt result: {e}")
        return None

    def find_all_hyperopt_results(self) -> List[HyperoptResult]:
        """Get all hyperopt results as model objects."""
        rows = self._db.get_all_hyperopt_results()
        results = []
        for r in rows:
            try:
                results.append(HyperoptResult(
                    strategy_name=r.get("strategy_name", "unknown"),
                    best_params=r.get("best_params", {}),
                    best_score=float(r.get("best_score", 0)),
                    n_trials=int(r.get("n_trials", 0)),
                    elapsed_seconds=float(r.get("elapsed_seconds", 0)),
                ))
            except Exception as e:
                logger.warning(f"Failed to parse hyperopt row: {e}")
        return results

    # ── Health Check ──

    def log_health_check(self, status: str, mt5_connected: bool,
                         last_cycle_seconds_ago: Optional[int] = None,
                         consecutive_errors: int = 0,
                         error_message: Optional[str] = None) -> bool:
        return self._db.log_health_check(
            status=status, mt5_connected=mt5_connected,
            last_cycle_seconds_ago=last_cycle_seconds_ago,
            consecutive_errors=consecutive_errors,
            error_message=error_message,
        )
