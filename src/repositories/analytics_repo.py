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
                            balance_after: Optional[float] = None,
                            cooldown_minutes: int = 120) -> Optional[int]:
        return self._db.log_circuit_breaker(reason, drawdown_pct, balance_before, balance_after, cooldown_minutes)

    def is_circuit_breaker_active(self, cooldown_minutes: int) -> bool:
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

    # ── ML Training Log ──

    def save_ml_training_log(self, log_data: Dict[str, Any]) -> bool:
        """Persist an ML training run record."""
        return self._db.save_ml_training_log(log_data)

    def get_ml_training_log(self, limit: int = 20,
                            symbol: Optional[str] = None,
                            timeframe: Optional[str] = None) -> List[Dict]:
        """Get recent ML training runs."""
        return self._db.get_ml_training_log(limit=limit, symbol=symbol, timeframe=timeframe)

    def check_concept_drift(self, threshold_pct: float = 5.0,
                            symbol: Optional[str] = None,
                            timeframe: Optional[str] = None) -> Dict[str, Any]:
        """Check if latest training accuracy dropped >threshold_pct vs average of previous 3 runs.

        Returns:
            drifted: bool — True if concept drift detected
            latest_acc: float — latest training accuracy
            avg_prev_3: float — average accuracy of 3 runs before latest
            drop_pct: float — percentage drop relative to avg_prev_3
            n_available: int — number of training records available
        """
        logs = self.get_ml_training_log(limit=4, symbol=symbol, timeframe=timeframe)
        result = {
            "drifted": False,
            "latest_acc": 0.0,
            "avg_prev_3": 0.0,
            "drop_pct": 0.0,
            "n_available": len(logs),
        }
        if len(logs) < 4:
            # Need at least 4 records (1 latest + 3 previous) to detect drift
            return result

        # logs are newest-first; latest is [0], previous 3 are [1:4]
        latest = logs[0]
        prev_3 = logs[1:4]

        latest_acc = float(latest.get("accuracy", 0) or 0)
        prev_accs = [float(r.get("accuracy", 0) or 0) for r in prev_3]
        avg_prev = sum(prev_accs) / len(prev_accs)

        if avg_prev > 0:
            drop_pct = ((avg_prev - latest_acc) / avg_prev) * 100
        else:
            drop_pct = 0.0

        result["latest_acc"] = latest_acc
        result["avg_prev_3"] = avg_prev
        result["drop_pct"] = round(drop_pct, 2)
        result["drifted"] = drop_pct > threshold_pct
        return result

    # ── Health Check ──

    def log_health_check(self, status: str, mt5_connected: bool,
                         consecutive_errors: int,
                         last_cycle_seconds_ago: Optional[int] = None,
                         error_message: Optional[str] = None) -> bool:
        return self._db.log_health_check(
            status=status, mt5_connected=mt5_connected,
            last_cycle_seconds_ago=last_cycle_seconds_ago,
            consecutive_errors=consecutive_errors,
            error_message=error_message,
        )
