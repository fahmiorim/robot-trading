#!/usr/bin/env python3
"""
Hyperparameter Optimization Runner - M1, M5, M15.
Robust version with numpy type handling.
"""
import sys
import time
import json
import warnings
from datetime import datetime
from typing import Dict, Any

import numpy as np
import MetaTrader5 as mt5
import pandas as pd

warnings.filterwarnings("ignore", category=RuntimeWarning)

from src.configuration.manager import ConfigManager
from src.backtesting.engine import Backtester
from src.backtesting.hyperopt import Hyperopt
from src.strategy.interface import IStrategy


TIMEFRAMES = {"TIMEFRAME_M1": 1, "TIMEFRAME_M5": 5, "TIMEFRAME_M15": 15}
SYMBOL = "XAUUSD"
CANDLE_COUNT = 3000
N_HYPEROPT_CALLS = 30
N_INITIAL_POINTS = 8


# Custom JSON encoder for numpy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, complex):
            return float(obj.real)
        return super().default(obj)


def safe_float(v, default=0.0):
    """Safely convert any value to float, handling complex numbers."""
    if v is None:
        return default
    try:
        f = float(v)
        if np.isnan(f) or np.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def fetch_data(timeframe_mt5: int, count: int = CANDLE_COUNT) -> pd.DataFrame:
    print(f"  Fetching {count} candles @ TF={timeframe_mt5}...")
    rates = mt5.copy_rates_from_pos(SYMBOL, timeframe_mt5, 0, count)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No data returned: {mt5.last_error()}")
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df.set_index("time")
    if "tick_volume" in df.columns:
        df = df.rename(columns={"tick_volume": "volume"})
    # Remove rows with NaN
    df = df.dropna()
    print(f"  Got {len(df)} candles ({df.index[0]} -> {df.index[-1]})")
    return df


def load_strategies():
    registry = IStrategy.get_registry()
    found = {}
    for name in ["MA_Crossover", "RSI", "MACD", "Bollinger", "Breakout"]:
        if name in registry:
            found[name] = registry[name]
            print(f"  [+] {name}: {registry[name].__name__}")
        else:
            print(f"  [X] {name} not found in registry!")
    return found


def run_hyperopt(strategy_cls, data: pd.DataFrame, config: ConfigManager,
                 tf_label: str) -> Dict[str, Any]:
    strategy_name = getattr(strategy_cls, "strategy_id", strategy_cls.__name__)
    param_space = getattr(strategy_cls, "param_space", {})
    print(f"\n  -- {strategy_name} ({len(param_space)} params) --")

    if not param_space:
        print(f"  [SKIP] No param_space defined")
        return {}

    print(f"  Param space: {param_space}")
    backtester = Backtester(config)
    hyperopt = Hyperopt(config, backtester)

    # Monkey-patch _eval_params to handle complex values
    orig_eval = hyperopt._eval_params

    def safe_eval(strategy_cls, params, data, loss, full_metrics=False):
        try:
            result = orig_eval(strategy_cls, params, data, loss, full_metrics)
            # Clean up any complex or invalid values
            for key in ["total_return", "sharpe_ratio", "max_drawdown",
                        "win_rate", "num_trades"]:
                result[key] = safe_float(result.get(key, 0))
            if "score" in result:
                result["score"] = safe_float(result["score"])
            if "metrics" in result:
                for k in result["metrics"]:
                    result["metrics"][k] = safe_float(result["metrics"].get(k, 0))
            return result
        except Exception as e:
            print(f"    [WARN] Backtest failed: {e}")
            return {
                "total_return": 0, "sharpe_ratio": 0, "max_drawdown": 0,
                "win_rate": 0, "num_trades": 0, "score": 999.0,
                "metrics": {"total_return": 0, "sharpe_ratio": 0,
                           "max_drawdown": 0, "win_rate": 0, "num_trades": 0},
            }

    hyperopt._eval_params = safe_eval

    t0 = time.time()
    try:
        result = hyperopt.optimize(
            strategy_cls, data, loss="sortino",
            n_calls=N_HYPEROPT_CALLS,
            n_initial_points=N_INITIAL_POINTS,
        )
    except Exception as e:
        print(f"  [X] Hyperopt failed: {e}")
        return {}

    elapsed = time.time() - t0
    metrics = result.metrics or {}

    print(f"  [OK] Best params: {result.params}")
    print(f"       Score: {safe_float(result.score):.4f}")
    print(f"       Return: {safe_float(metrics.get('total_return', 0)):.2f}%")
    print(f"       Sharpe: {safe_float(metrics.get('sharpe_ratio', 0)):.3f}")
    print(f"       Max DD: {safe_float(metrics.get('max_drawdown', 0)):.2f}%")
    print(f"       Win Rate: {safe_float(metrics.get('win_rate', 0)):.1f}%")
    print(f"       Trades: {int(metrics.get('num_trades', 0))}")
    print(f"       Time: {elapsed:.1f}s")

    return {
        "strategy": strategy_name,
        "timeframe": tf_label,
        "best_params": {k: safe_float(v) if isinstance(v, (float, np.floating)) else int(v) if isinstance(v, np.integer) else v for k, v in result.params.items()},
        "score": safe_float(result.score),
        "metrics": {k: safe_float(v) for k, v in metrics.items()},
        "elapsed": round(elapsed, 1),
        "n_trials": int(result.n_trials),
    }


def main():
    print("=" * 65)
    print("  HYPERPARAMETER OPTIMIZATION - M1 / M5 / M15")
    print(f"  Symbol: {SYMBOL}, Candles: {CANDLE_COUNT}")
    print(f"  Iterations per run: {N_HYPEROPT_CALLS}")
    print("=" * 65)

    print("\n[1] Initializing MT5...")
    if not mt5.initialize():
        print(f"  [X] MT5 init failed: {mt5.last_error()}")
        sys.exit(1)
    print(f"  [+] MT5 connected: {mt5.terminal_info().connected}")

    print("\n[2] Loading strategies...")
    strategy_classes = load_strategies()

    print("\n[3] Setting up config...")
    config = ConfigManager()
    for k, v in {"initial_balance": 10000.0, "commission_pct": 0.03,
                 "slippage_pct": 0.05}.items():
        config.set("backtest", k, v)
    config.save()

    print("\n[4] Running hyperparameter optimization...")
    all_results = []

    for tf_label, tf_mt5 in TIMEFRAMES.items():
        print(f"\n{'#' * 60}")
        print(f"  TIMEFRAME: {tf_label} ({tf_mt5} min)")
        print(f"{'#' * 60}")
        data = fetch_data(tf_mt5)

        for sname, sclass in strategy_classes.items():
            try:
                result = run_hyperopt(sclass, data, config, tf_label)
                if result:
                    all_results.append(result)
            except Exception as e:
                print(f"  [X] {sname} error: {e}")

    # 5. Summary
    print(f"\n\n{'=' * 65}")
    print("  RESULTS SUMMARY")
    print(f"{'=' * 65}")

    summary_data = []
    for r in all_results:
        params_str = ", ".join(f"{k}={v}" for k, v in r["best_params"].items())
        m = r.get("metrics", {})
        summary_data.append({
            "Strategy": r["strategy"],
            "TF": r["timeframe"].replace("TIMEFRAME_", ""),
            "Return%": safe_float(m.get("total_return", 0)),
            "Sharpe": safe_float(m.get("sharpe_ratio", 0)),
            "MaxDD%": safe_float(m.get("max_drawdown", 0)),
            "WinRate%": safe_float(m.get("win_rate", 0)),
            "Trades": int(m.get("num_trades", 0)),
            "Params": params_str,
        })

    print(f"\n{'Strategy':<15} {'TF':<5} {'Return%':>8} {'Sharpe':>7} "
          f"{'MaxDD%':>7} {'WinRate%':>8} {'Trades':>7}  Best Params")
    print("-" * 150)
    for row in sorted(summary_data, key=lambda x: (x["TF"], -x["Sharpe"])):
        print(f"{row['Strategy']:<15} {row['TF']:<5} {row['Return%']:>8.2f} "
              f"{row['Sharpe']:>7.3f} {row['MaxDD%']:>7.2f} "
              f"{row['WinRate%']:>8.1f} {row['Trades']:>7}  {row['Params']}")

    # 6. Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"hyperopt_results_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(all_results, f, indent=2, cls=NumpyEncoder)
    print(f"\n[+] Results saved to: {filename}")

    # 7. Best overall params
    print(f"\n{'=' * 65}")
    print("  BEST PARAMS PER STRATEGY (for Settings)")
    print(f"{'=' * 65}")

    by_strategy = {}
    for r in all_results:
        s = r["strategy"]
        by_strategy.setdefault(s, []).append(r)

    for sname, results in sorted(by_strategy.items()):
        best = max(results, key=lambda x: x.get("metrics", {}).get("sharpe_ratio", -999))
        m = best.get("metrics", {})
        print(f"\n  {sname}:")
        print(f"    Timeframe: {best['timeframe'].replace('TIMEFRAME_', '')}")
        print(f"    Params: {best['best_params']}")
        print(f"    Sharpe={safe_float(m.get('sharpe_ratio',0)):.3f}, "
              f"Return={safe_float(m.get('total_return',0)):.2f}%, "
              f"DD={safe_float(m.get('max_drawdown',0)):.2f}%")

    mt5.shutdown()
    print(f"\n{'=' * 65}")
    print("  DONE")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    main()
