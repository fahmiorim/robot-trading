"""
Backtesting metrics — compute performance statistics from trade results.

Extracted from the ``Backtester.run()`` method into standalone helpers.
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.analysis.performance import (
    calculate_profit_factor,
    calculate_calmar_ratio,
    calculate_cagr,
    calculate_sqn,
    calculate_expectancy,
    calculate_streaks,
    calculate_time_in_market,
    calculate_monthly_returns,
)

ANNUALIZE_THRESHOLD_YEARS = 0.1


def compute_metrics(
    trades: List[Dict],
    equity_curve: List[float],
    initial_balance: float,
    data: pd.DataFrame,
) -> Dict[str, Any]:
    """Compute all performance metrics from completed backtest trades.

    Args:
        trades: List of trade dicts (each with 'profit', 'profit_pct', etc.).
        equity_curve: List of equity values over time.
        initial_balance: Starting account balance.
        data: OHLCV DataFrame (used for data span calculation).

    Returns:
        Dict with all metrics (sharpe, sortino, calmar, cagr, sqn, etc.).
    """
    total_return = (equity_curve[-1] - initial_balance) / initial_balance * 100

    # ── Drawdown ──
    equity_series = pd.Series(equity_curve)
    rolling_max = equity_series.cummax()
    drawdown_series = (rolling_max - equity_series) / rolling_max * 100
    max_dd = float(drawdown_series.max()) if len(drawdown_series) > 0 else 0.0

    wins = sum(1 for t in trades if t.get("profit", t.get("profit_pct", 0)) > 0)
    losses = sum(1 for t in trades if t.get("profit", t.get("profit_pct", 0)) < 0)
    wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0

    proper_trades = _extract_proper_trades(trades)
    returns = [t["profit"] / initial_balance for t in proper_trades]

    # ── Sharpe & Sortino ──
    sharpe, sortino = _compute_sharpe_sortino(returns, data)

    pf = calculate_profit_factor(proper_trades)
    calmar = calculate_calmar_ratio(total_return, max_dd, 1.0)

    total_period_hours = _compute_period_hours(trades, data)
    years = total_period_hours / (365.25 * 24) if total_period_hours else 1.0
    cagr = calculate_cagr(initial_balance, equity_curve[-1], max(years, 0.01))
    sqn = calculate_sqn(returns)
    expectancy = calculate_expectancy(proper_trades, initial_balance)
    streaks = calculate_streaks(proper_trades)
    time_market = calculate_time_in_market(proper_trades, total_period_hours)
    monthly_df = calculate_monthly_returns(proper_trades)

    return {
        "total_return": total_return,
        "final_balance": equity_curve[-1],
        "num_trades": len(proper_trades),
        "wins": wins,
        "losses": losses,
        "max_drawdown": max_dd,
        "win_rate": round(wr, 2),
        "sharpe_ratio": round(sharpe, 3),
        "sortino_ratio": round(sortino, 3),
        "calmar_ratio": round(calmar, 3),
        "profit_factor": round(pf, 3),
        "cagr_pct": round(cagr, 3),
        "sqn": round(sqn, 3),
        "expectancy_pct": round(expectancy["expectancy_pct"], 3),
        "expectancy_ratio": round(expectancy["expectancy_ratio"], 3),
        "avg_win_pct": round(expectancy["avg_win_pct"], 3),
        "avg_loss_pct": round(expectancy["avg_loss_pct"], 3),
        "longest_win_streak": streaks["longest_win_streak"],
        "longest_loss_streak": streaks["longest_loss_streak"],
        "current_win_streak": streaks["current_win_streak"],
        "current_loss_streak": streaks["current_loss_streak"],
        "time_in_market_pct": round(time_market, 2),
        "monthly_returns": monthly_df,
        "equity_curve": equity_curve,
        "trades": trades,
    }


def _extract_proper_trades(trades: List[Dict]) -> List[Dict]:
    """Filter trades to only those with a profit value."""
    result = []
    for t in trades:
        profit_val = t.get("profit", t.get("profit_pct", 0))
        if not isinstance(profit_val, (int, float)):
            profit_val = 0.0
        result.append({
            "profit": float(profit_val),
            "entry_time": t.get("entry_time"),
            "exit_time": t.get("time"),
        })
    return result


def _compute_sharpe_sortino(returns: List[float],
                            data: pd.DataFrame) -> tuple:
    """Compute Sharpe and Sortino ratios from trade returns."""
    if len(returns) < 2:
        return 0.0, 0.0

    arr = np.array(returns)
    r_mean = float(np.mean(arr))
    r_std = float(np.std(arr))
    if r_std <= 0:
        return 0.0, 0.0

    data_span_hours = (
        (data.index[-1] - data.index[0]).total_seconds() / 3600
        if len(data) > 1 else 1.0
    )
    data_years = data_span_hours / (365.25 * 24)

    downside_diff = np.minimum(0, arr)
    downside_dev = float(np.sqrt(np.mean(downside_diff ** 2)))

    if data_years >= ANNUALIZE_THRESHOLD_YEARS:
        annual_factor = (len(returns) / max(data_years, 0.001)) ** 0.5
        sharpe = round(r_mean / r_std * annual_factor, 3)
        sortino = round(r_mean / downside_dev * annual_factor, 3) if downside_dev > 0 else 0.0
    else:
        sharpe = round(r_mean / r_std, 3)
        sortino = round(r_mean / downside_dev, 3) if downside_dev > 0 else 0.0

    return sharpe, sortino


def _compute_period_hours(trades: List[Dict], data: pd.DataFrame) -> Optional[float]:
    """Compute the total trading period in hours."""
    trade_times = [
        t.get("time") for t in trades
        if isinstance(t.get("time"), pd.Timestamp)
    ]
    if len(trade_times) >= 2:
        span = (max(trade_times) - min(trade_times)).total_seconds() / 3600
        return max(span, 1)
    return None
