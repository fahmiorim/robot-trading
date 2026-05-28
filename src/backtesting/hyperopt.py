"""
Hyperparameter optimization engine — Bayesian optimization via scikit-optimize.

Inspired by Freqtrade's hyperopt module, adapted for MT5 strategies.

Uses gp_minimize (Gaussian Process) for efficient search of strategy
parameter spaces defined in each strategy's ``param_space`` attribute.
"""
import time
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

try:
    from skopt import gp_minimize
    from skopt.space import Integer, Real, Categorical
    SKOPT_AVAILABLE = True
except ImportError:
    SKOPT_AVAILABLE = False

from src.configuration.manager import ConfigManager
from src.backtesting.engine import Backtester
from src.persistence.database import get_db
from src.utils.logging import get_logger

logger = get_logger(__name__)

# ── Default loss function ─────────────────────────────────────


def sharpe_loss(result: Dict[str, Any]) -> float:
    """Negative Sharpe ratio (minimize). Higher Sharpe = better."""
    return -result.get("sharpe_ratio", 0)


def sortino_loss(result: Dict[str, Any]) -> float:
    """Negative Sortino ratio."""
    return -result.get("sortino_ratio", result.get("sharpe_ratio", 0))


def calmar_loss(result: Dict[str, Any]) -> float:
    """Negative Calmar ratio."""
    calmar = result.get("total_return", 0) / max(result.get("max_drawdown", 1), 1)
    return -calmar


LOSS_FUNCTIONS = {
    "sharpe": sharpe_loss,
    "sortino": sortino_loss,
    "calmar": calmar_loss,
}


class Hyperopt:
    """Run Bayesian hyperparameter optimization for a strategy.

    Usage::
        h = Hyperopt(config, backtester)
        best = h.optimize(strategy_cls, data, loss="sharpe", n_calls=30)
        print(best.params, best.score)
    """

    def __init__(self, config: ConfigManager, backtester: Backtester):
        self.config = config
        self.backtester = backtester
        self.db = get_db()

    def optimize(self, strategy_cls: type, data: pd.DataFrame,
                 loss: str = "sharpe", n_calls: int = 30,
                 n_initial_points: int = 10) -> "HyperoptResult":
        """Run hyperparameter optimization.

        Args:
            strategy_cls: A subclass of IStrategy with ``param_space`` defined.
            data: OHLCV DataFrame for backtesting.
            loss: Name of loss function ('sharpe', 'sortino', 'calmar').
            n_calls: Number of optimization iterations.
            n_initial_points: Random points before Bayesian starts.

        Returns:
            HyperoptResult with best params and score.
        """
        if not SKOPT_AVAILABLE:
            logger.warning("scikit-optimize not installed. Install with: pip install scikit-optimize")
            return self._random_search(strategy_cls, data, loss, n_calls)

        param_space = getattr(strategy_cls, "param_space", {})
        if not param_space:
            logger.warning(f"{strategy_cls.__name__} has no param_space defined")
            result = self._eval_params(strategy_cls, {}, data, loss)
            return HyperoptResult(params={}, score=result["score"])

        spaces = self._build_skopt_space(param_space)
        loss_fn = LOSS_FUNCTIONS.get(loss, sharpe_loss)

        def objective(params):
            param_dict = self._params_to_dict(param_space, params)
            result = self._eval_params(strategy_cls, param_dict, data, loss)
            return result["score"]

        logger.info(f"Starting hyperopt for {strategy_cls.__name__}: "
                    f"{n_calls} calls, loss={loss}")

        t0 = time.time()
        res = gp_minimize(
            objective,
            spaces,
            n_calls=n_calls,
            n_initial_points=n_initial_points,
            random_state=42,
            acq_func="EI",
        )
        elapsed = time.time() - t0

        best_params = self._params_to_dict(param_space, res.x)
        best_score = res.fun

        final = self._eval_params(strategy_cls, best_params, data, loss, full_metrics=True)

        result = HyperoptResult(
            params=best_params,
            score=best_score,
            metrics=final.get("metrics", {}),
            n_trials=n_calls,
            elapsed=elapsed,
        )

        strategy_name = getattr(strategy_cls, "strategy_id", strategy_cls.__name__)
        try:
            # self.db is DatabaseManager — pass individual params directly
            self.db.save_hyperopt_result(
                strategy_name=strategy_name,
                params=best_params,
                score=-best_score,
                metrics=final.get("metrics", {}),
                n_trials=n_calls,
                elapsed=elapsed,
            )
        except Exception as e:
            logger.error(f"Failed to save hyperopt result: {e}")

        logger.info(f"Hyperopt complete: {best_params}, score={best_score:.4f}, "
                    f"elapsed={elapsed:.1f}s")
        return result

    def _eval_params(self, strategy_cls: type, params: Dict,
                     data: pd.DataFrame, loss: str,
                     full_metrics: bool = False) -> Dict:
        strategy = strategy_cls(**params)
        signals = strategy.calculate_signals(data)
        name = getattr(strategy_cls, "strategy_id", strategy_cls.__name__)
        result = self.backtester.run(data, signals, f"{name}_hyperopt")
        loss_fn = LOSS_FUNCTIONS.get(loss, sharpe_loss)
        result["score"] = loss_fn(result)
        result["metrics"] = {
            "total_return": result["total_return"],
            "sharpe_ratio": result.get("sharpe_ratio", 0),
            "max_drawdown": result.get("max_drawdown", 0),
            "win_rate": result.get("win_rate", 0),
            "num_trades": result.get("num_trades", 0),
        }
        return result

    def _random_search(self, strategy_cls: type, data: pd.DataFrame,
                        loss: str, n_calls: int) -> "HyperoptResult":
        param_space = getattr(strategy_cls, "param_space", {})
        best_params = {}
        best_score = float("inf")
        t0 = time.time()

        for i in range(n_calls):
            params = {}
            for name, (lo, hi, typ) in param_space.items():
                if typ == "int":
                    params[name] = int(np.random.randint(lo, hi + 1))
                elif typ == "float":
                    params[name] = float(np.random.uniform(lo, hi))
                else:
                    params[name] = lo
            result = self._eval_params(strategy_cls, params, data, loss)
            if result["score"] < best_score:
                best_score = result["score"]
                best_params = params

        elapsed = time.time() - t0
        final = self._eval_params(strategy_cls, best_params, data, loss, full_metrics=True)
        return HyperoptResult(
            params=best_params, score=best_score,
            metrics=final.get("metrics", {}),
            n_trials=n_calls, elapsed=elapsed,
        )

    @staticmethod
    def _build_skopt_space(param_space: Dict) -> List:
        spaces = []
        for name, (lo, hi, typ) in param_space.items():
            if typ == "int":
                spaces.append(Integer(lo, hi, name=name))
            elif typ == "float":
                spaces.append(Real(lo, hi, name=name))
            else:
                spaces.append(Categorical([lo, hi], name=name))
        return spaces

    @staticmethod
    def _params_to_dict(param_space: Dict, values: List) -> Dict:
        return {name: values[i] for i, name in enumerate(param_space.keys())}


class HyperoptResult:
    """Result of a hyperparameter optimization run."""

    def __init__(self, params: Dict, score: float,
                 metrics: Optional[Dict] = None,
                 n_trials: int = 0, elapsed: float = 0):
        self.params = params
        self.score = score
        self.metrics = metrics or {}
        self.n_trials = n_trials
        self.elapsed = elapsed


# ── Backward compatibility aliases ────────────────────────────
HyperoptEngine = Hyperopt
ObjectiveWeights = HyperoptResult
