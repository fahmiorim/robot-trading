"""
Walk-forward validation — test strategy robustness across multiple time windows.

Extracted from the ``Backtester`` class into a standalone helper.
"""

from typing import Any, Callable, Dict

import numpy as np
import pandas as pd

from src.utils.logging import get_logger

logger = get_logger(__name__)


def run_walk_forward(
    data: pd.DataFrame,
    signal_generator: Callable,
    strategy_name: str,
    n_windows: int = 3,
    train_frac: float = 0.7,
    run_fn: Callable = None,
    initial_balance: float = 10_000,
) -> Dict[str, Any]:
    """Run walk-forward validation on historical data.

    Args:
        data: OHLCV DataFrame with datetime index.
        signal_generator: Function that takes training data and returns
                          a function that generates signals on test data.
        strategy_name: Name for logging.
        n_windows: Number of windows for walk-forward.
        train_frac: Fraction of each window used for training.
        run_fn: Callable with signature ``run_fn(test_data, signals, name)``.
        initial_balance: Starting balance for the run.

    Returns:
        Dict with aggregated walk-forward results.
    """
    logger.info(f"Walk-forward: {strategy_name}, {n_windows} windows")
    n = len(data)
    window_size = n // n_windows
    all_trades = []
    window_results = []

    for w in range(n_windows):
        train_end = (w + 1) * window_size
        if train_end > n:
            train_end = n
        test_start = max(int(train_end * train_frac), w * window_size)
        train_data = data.iloc[test_start:train_end]
        gen = signal_generator(train_data)
        if w + 1 < n_windows:
            test_data = data.iloc[train_end:(w + 2) * window_size]
        else:
            test_data = data.iloc[train_end:]
        if len(test_data) < 10:
            continue
        signals = gen(test_data)
        result = run_fn(test_data, signals, f"{strategy_name}_w{w}")
        window_results.append(result)
        all_trades.extend(result.get("trades", []))

    if not window_results:
        return {
            "total_return": 0, "num_trades": 0, "max_drawdown": 0,
            "win_rate": 0, "sharpe_ratio": 0,
            "equity_curve": [initial_balance], "trades": [],
        }

    avg_return = float(np.mean([r["total_return"] for r in window_results]))
    return {
        "total_return": avg_return,
        "num_trades": sum(r["num_trades"] for r in window_results),
        "max_drawdown": float(max(r.get("max_drawdown", 0) for r in window_results)),
        "win_rate": float(np.mean([r.get("win_rate", 0) for r in window_results])),
        "sharpe_ratio": float(np.mean([r.get("sharpe_ratio", 0) for r in window_results])),
        "equity_curve": [initial_balance],
        "trades": all_trades,
        "window_results": window_results,
    }
