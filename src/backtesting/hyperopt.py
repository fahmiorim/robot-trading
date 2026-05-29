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
        best = h.optimize(strategy_cls, data, loss, n_calls, n_initial_points)
        print(best.params, best.score)
    """

    def __init__(self, config: ConfigManager, backtester: Backtester):
        self.config = config
        self.backtester = backtester
        self.db = get_db()

    def optimize(self, strategy_cls: type, data: pd.DataFrame,
                 loss: str = "sortino", n_calls: int = 30,
                 n_initial_points: int = 8, callback: Any = None, **kwargs) -> "HyperoptResult":
        """Run hyperparameter optimization.

        Args:
            strategy_cls: A subclass of IStrategy with ``param_space`` defined.
            data: OHLCV DataFrame for backtesting.
            loss: Name of loss function ('sharpe', 'sortino', 'calmar').
            n_calls: Number of optimization iterations.
            n_initial_points: Random points before Bayesian starts.
            callback: Function to invoke after each evaluation for real-time progress.

        Returns:
            HyperoptResult with best params and score.
        """
        # Handle backward-compatibility n_trials from dashboard
        if "n_trials" in kwargs:
            n_calls = kwargs["n_trials"]

        optimize_risk = kwargs.get("optimize_risk", False)

        n_initial_points = max(1, min(n_initial_points, n_calls))
        if not SKOPT_AVAILABLE:
            logger.warning("scikit-optimize not installed. Install with: pip install scikit-optimize")
            return self._random_search(strategy_cls, data, loss, n_calls, callback=callback, optimize_risk=optimize_risk)

        param_space = dict(getattr(strategy_cls, "param_space", {}))
        if optimize_risk:
            param_space['stop_loss_pct'] = (0.1, 5.0, 'float')
            param_space['take_profit_pct'] = (0.2, 15.0, 'float')

        if not param_space:
            logger.warning(f"{strategy_cls.__name__} has no param_space defined")
            result = self._eval_params(strategy_cls, {}, data, loss)
            return HyperoptResult(params={}, score=result["score"], n_trials=0, elapsed=0.0)

        spaces = self._build_skopt_space(param_space)
        loss_fn = LOSS_FUNCTIONS.get(loss, sharpe_loss)

        def objective(params):
            param_dict = self._params_to_dict(param_space, params)
            
            # Constraint: fast period must be less than slow period
            strategy_name = getattr(strategy_cls, "strategy_id", strategy_cls.__name__)
            if strategy_name == "MA_Crossover":
                if param_dict.get("fast_period", 0) >= param_dict.get("slow_period", 0):
                    return 1e6
            elif strategy_name == "MACD":
                if param_dict.get("fast", 0) >= param_dict.get("slow", 0):
                    return 1e6

            result = self._eval_params(strategy_cls, param_dict, data, loss)
            return result["score"]

        logger.info(f"Starting hyperopt for {strategy_cls.__name__}: "
                    f"{n_calls} calls, loss={loss}")

        t0 = time.time()
        
        def on_step(res):
            if callback:
                try:
                    current_trial = len(res.func_vals)
                    best_score = -res.fun
                    if best_score < -1000:
                        best_score = 0.0
                    best_params = self._params_to_dict(param_space, res.x)
                    
                    # Extract current trial info
                    current_val = -res.func_vals[-1] if len(res.func_vals) > 0 else 0.0
                    if current_val < -1000:
                        current_val = 0.0
                    current_x = res.x_iters[-1] if len(res.x_iters) > 0 else res.x
                    current_params = self._params_to_dict(param_space, current_x)
                    
                    callback(
                        current=current_trial,
                        total=n_calls,
                        best_score=best_score,
                        best_params=best_params,
                        current_score=current_val,
                        current_params=current_params
                    )
                except Exception as e:
                    logger.warning(f"Hyperopt callback error: {e}")

        res = gp_minimize(
            objective,
            spaces,
            n_calls=n_calls,
            n_initial_points=n_initial_points,
            random_state=42,
            acq_func="EI",
            callback=on_step,
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
        strat_params = {k: v for k, v in params.items() if k not in ['stop_loss_pct', 'take_profit_pct']}
        strategy = strategy_cls(**strat_params)
        signals = strategy.calculate_signals(data)
        name = getattr(strategy_cls, "strategy_id", strategy_cls.__name__)
        
        # Override SL/TP temporarily if present
        original_sl = self.backtester.sl_pct
        original_tp = self.backtester.tp_pct
        if 'stop_loss_pct' in params:
            self.backtester.sl_pct = float(params['stop_loss_pct'])
        if 'take_profit_pct' in params:
            self.backtester.tp_pct = float(params['take_profit_pct'])

        result = self.backtester.run(data, signals, f"{name}_hyperopt")

        # Restore original SL/TP
        self.backtester.sl_pct = original_sl
        self.backtester.tp_pct = original_tp

        loss_fn = LOSS_FUNCTIONS.get(loss, sharpe_loss)
        result["score"] = loss_fn(result)
        result["metrics"] = {
            "total_return": result["total_return"],
            "sharpe_ratio": result.get("sharpe_ratio", 0),
            "sortino_ratio": result.get("sortino_ratio", 0),
            "calmar_ratio": result.get("calmar_ratio", 0),
            "profit_factor": result.get("profit_factor", 1.0),
            "max_drawdown": result.get("max_drawdown", 0),
            "win_rate": result.get("win_rate", 0),
            "num_trades": result.get("num_trades", 0),
        }
        return result

    def _random_search(self, strategy_cls: type, data: pd.DataFrame,
                        loss: str, n_calls: int, callback: Any = None,
                        optimize_risk: bool = False) -> "HyperoptResult":
        param_space = dict(getattr(strategy_cls, "param_space", {}))
        if optimize_risk:
            param_space['stop_loss_pct'] = (0.1, 5.0, 'float')
            param_space['take_profit_pct'] = (0.2, 15.0, 'float')
        best_params = {}
        best_score = float("inf")
        t0 = time.time()

        for i in range(n_calls):
            # Try to generate valid parameters (up to 20 attempts)
            for _ in range(20):
                params = {}
                for name, (lo, hi, typ) in param_space.items():
                    if typ == "int":
                        params[name] = int(np.random.randint(lo, hi + 1))
                    elif typ == "float":
                        params[name] = float(np.random.uniform(lo, hi))
                    else:
                        params[name] = lo
                
                strategy_name = getattr(strategy_cls, "strategy_id", strategy_cls.__name__)
                if strategy_name == "MA_Crossover":
                    if params.get("fast_period", 0) < params.get("slow_period", 0):
                        break
                elif strategy_name == "MACD":
                    if params.get("fast", 0) < params.get("slow", 0):
                        break
                else:
                    break

            result = self._eval_params(strategy_cls, params, data, loss)
            if result["score"] < best_score:
                best_score = result["score"]
                best_params = params

            if callback:
                try:
                    callback(
                        current=i + 1,
                        total=n_calls,
                        best_score=-best_score,
                        best_params=best_params,
                        current_score=-result["score"],
                        current_params=params
                    )
                except Exception as e:
                    logger.warning(f"Hyperopt random search callback error: {e}")

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
                 n_trials: int, elapsed: float,
                 metrics: Optional[Dict] = None):
        self.params = params
        self.score = score
        self.metrics = metrics or {}
        self.n_trials = n_trials
        self.elapsed = elapsed

    @property
    def best_params(self) -> Dict:
        return self.params

    @property
    def best_score(self) -> float:
        return self.score

    @property
    def best_results(self) -> Dict:
        return self.metrics

    @property
    def trials(self) -> List:
        return [None] * self.n_trials

    @property
    def total_elapsed(self) -> float:
        return self.elapsed


# ── Backward compatibility aliases ────────────────────────────
HyperoptEngine = Hyperopt
ObjectiveWeights = HyperoptResult
