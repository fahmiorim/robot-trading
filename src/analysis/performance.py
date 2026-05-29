"""
Performance tracking and metrics — inspired by Freqtrade's ``data/metrics.py``.

Provides functions for calculating Sharpe, Sortino, Calmar ratios,
win rate, drawdown, and other trade statistics.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def calculate_sharpe_ratio(returns: List[float],
                           risk_free_rate: float,
                           periods_per_year: int) -> float:
    """Annualised Sharpe ratio."""
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns)
    excess = arr - (risk_free_rate / periods_per_year)
    if np.std(excess) == 0:
        return 0.0
    return float(np.mean(excess) / np.std(excess) * np.sqrt(periods_per_year))


def calculate_sortino_ratio(returns: List[float],
                            risk_free_rate: float,
                            periods_per_year: int) -> float:
    """Annualised Sortino ratio (downside deviation only)."""
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns)
    target = risk_free_rate / periods_per_year
    excess = arr - target
    # Downside deviation uses all returns, but only penalizes returns below target (or 0)
    downside_diff = np.minimum(0, excess)
    downside_deviation = np.sqrt(np.mean(downside_diff ** 2))
    if downside_deviation == 0:
        return 0.0
    return float(np.mean(excess) / downside_deviation * np.sqrt(periods_per_year))


def calculate_calmar_ratio(total_return_pct: float, max_drawdown_pct: float,
                           years: float) -> float:
    """Calmar ratio = annualised return / max drawdown."""
    if max_drawdown_pct == 0 or years <= 0 or total_return_pct <= -100.0:
        return 0.0
    try:
        annualised = ((1 + total_return_pct / 100) ** (1 / years) - 1) * 100
        return annualised / max_drawdown_pct
    except Exception:
        return 0.0


def calculate_max_drawdown(equity_curve: List[float]) -> Tuple[float, int, int]:
    """Return (max_drawdown_pct, peak_index, trough_index)."""
    if len(equity_curve) < 2:
        return (0.0, 0, 0)
    arr = np.array(equity_curve)
    peak = np.maximum.accumulate(arr)
    dd = (peak - arr) / peak * 100
    max_idx = int(np.argmax(dd))
    peak_idx = int(np.argmax(arr[:max_idx + 1])) if max_idx > 0 else 0
    return (float(dd[max_idx]), peak_idx, max_idx)


def calculate_win_rate(trades: List[Dict]) -> Tuple[int, int, float]:
    """Return (wins, losses, win_rate_pct)."""
    wins = sum(1 for t in trades if t.get('profit', 0) > 0)
    losses = sum(1 for t in trades if t.get('profit', 0) < 0)
    total = wins + losses
    wr = (wins / total * 100) if total > 0 else 0.0
    return wins, losses, wr


def calculate_profit_factor(trades: List[Dict]) -> float:
    """Gross profit / gross loss."""
    gross_profit = sum(t.get('profit', 0) for t in trades if t.get('profit', 0) > 0)
    gross_loss = abs(sum(t.get('profit', 0) for t in trades if t.get('profit', 0) < 0))
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 1.0
    return gross_profit / gross_loss


def calculate_avg_holding_time(trades: List[Dict]) -> timedelta:
    """Average holding time per trade in hours."""
    durations = []
    for t in trades:
        entry = t.get('entry_time')
        exit = t.get('exit_time') or datetime.now()
        if entry:
            durations.append((exit - entry).total_seconds())
    if not durations:
        return timedelta()
    return timedelta(seconds=sum(durations) / len(durations))


def build_equity_curve(trades: List[Dict], initial_balance: float) -> pd.DataFrame:
    """Build equity curve from a list of trade dicts, sorted by exit_time."""
    df = pd.DataFrame(trades)
    if df.empty:
        return pd.DataFrame({'time': [datetime.now()], 'equity': [initial_balance],
                             'drawdown_pct': [0.0]})
    df = df[df['exit_time'].notna()].copy()
    if df.empty:
        return pd.DataFrame({'time': [datetime.now()], 'equity': [initial_balance],
                             'drawdown_pct': [0.0]})
    df = df.sort_values('exit_time')
    df['cumulative_pnl'] = df['profit'].cumsum()
    df['equity'] = initial_balance + df['cumulative_pnl']
    peak = df['equity'].cummax()
    df['drawdown_pct'] = (peak - df['equity']) / peak * 100
    return df[['exit_time', 'equity', 'drawdown_pct']].rename(
        columns={'exit_time': 'time'})


def calculate_cagr(initial_balance: float, final_balance: float,
                    years: float) -> float:
    """Compound Annual Growth Rate."""
    if initial_balance <= 0 or years <= 0:
        return 0.0
    return ((final_balance / initial_balance) ** (1.0 / years) - 1.0) * 100.0


def calculate_sqn(returns: List[float]) -> float:
    """System Quality Number (SQN).

    SQN = mean(returns) / std(returns) * sqrt(num_trades)
    A measure of trading system quality. > 2 = good, > 3 = excellent.
    """
    if len(returns) < 2 or np.std(returns) == 0:
        return 0.0
    return float(np.mean(returns) / np.std(returns) * np.sqrt(len(returns)))


def calculate_expectancy(trades: List[Dict], initial_balance: float) -> Dict:
    """Expectancy analysis.

    Returns:
        avg_win: Average profit per winning trade (as % of balance)
        avg_loss: Average loss per losing trade (as % of balance)
        expectancy: Expected return per trade (as % of balance)
        expectancy_ratio: Avg win / |avg loss|
    """
    wins = [t.get('profit', 0) for t in trades if t.get('profit', 0) > 0]
    losses = [t.get('profit', 0) for t in trades if t.get('profit', 0) < 0]
    avg_win = (sum(wins) / len(wins)) / initial_balance * 100 if wins else 0.0
    avg_loss = (abs(sum(losses)) / len(losses)) / initial_balance * 100 if losses else 0.0
    total_trades = len(wins) + len(losses)
    if total_trades == 0:
        return {'avg_win_pct': 0, 'avg_loss_pct': 0, 'expectancy_pct': 0, 'expectancy_ratio': 0}
    win_rate = len(wins) / total_trades
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    er = avg_win / avg_loss if avg_loss > 0 else float('inf') if avg_win > 0 else 0
    return {
        'avg_win_pct': round(avg_win, 3),
        'avg_loss_pct': round(avg_loss, 3),
        'expectancy_pct': round(expectancy, 3),
        'expectancy_ratio': round(er, 3),
    }


def calculate_streaks(trades: List[Dict]) -> Dict:
    """Calculate winning and losing streaks."""
    if not trades:
        return {'longest_win_streak': 0, 'longest_loss_streak': 0,
                'current_win_streak': 0, 'current_loss_streak': 0}

    # Sort by exit_time or time
    sorted_trades = sorted(trades, key=lambda t: t.get('exit_time') or t.get('time', 0))

    longest_win = 0
    longest_loss = 0
    current_win = 0
    current_loss = 0

    for t in sorted_trades:
        profit = t.get('profit', 0)
        if profit > 0:
            current_win += 1
            current_loss = 0
            longest_win = max(longest_win, current_win)
        elif profit < 0:
            current_loss += 1
            current_win = 0
            longest_loss = max(longest_loss, current_loss)

    return {
        'longest_win_streak': longest_win,
        'longest_loss_streak': longest_loss,
        'current_win_streak': current_win,
        'current_loss_streak': current_loss,
    }


def calculate_monthly_returns(trades: List[Dict]) -> pd.DataFrame:
    """Aggregate returns by month."""
    if not trades:
        return pd.DataFrame(columns=['month', 'profit', 'trades'])
    df = pd.DataFrame(trades)
    time_col = 'exit_time' if 'exit_time' in df.columns else 'time'
    if time_col not in df.columns or df.empty:
        return pd.DataFrame(columns=['month', 'profit', 'trades'])
    df[time_col] = pd.to_datetime(df[time_col])
    df['month'] = df[time_col].dt.to_period('M')
    grouped = df.groupby('month').agg(
        profit=('profit', 'sum'),
        trades=('profit', 'count'),
    ).reset_index()
    grouped['month'] = grouped['month'].astype(str)
    return grouped


def calculate_time_in_market(trades: List[Dict],
                              total_period_hours: Optional[float] = None) -> float:
    """Percentage of time spent in trades vs total period."""
    if not trades:
        return 0.0
    total_holding = 0.0
    for t in trades:
        entry = t.get('entry_time')
        exit_t = t.get('exit_time')
        if entry:
            if exit_t:
                total_holding += (exit_t - entry).total_seconds() / 3600
            else:
                from datetime import datetime
                total_holding += (datetime.now() - entry).total_seconds() / 3600
    if total_period_hours and total_period_hours > 0:
        return min(100.0, (total_holding / total_period_hours) * 100)
    # If no total period given, just return avg hours per trade
    return total_holding / len(trades)


def summarize_trades(trades: List[Dict], initial_balance: float,
                     risk_free_rate: float, periods_per_year: int,
                     total_period_hours: Optional[float] = None) -> Dict:
    """Return a comprehensive metrics dictionary from a list of trade dicts."""
    if not trades:
        return {
            'total_trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0,
            'total_profit': 0, 'profit_factor': 1.0,
            'max_drawdown_pct': 0, 'sharpe': 0, 'sortino': 0, 'calmar': 0,
            'cagr_pct': 0, 'sqn': 0, 'expectancy_pct': 0, 'expectancy_ratio': 0,
            'longest_win_streak': 0, 'longest_loss_streak': 0,
            'time_in_market_pct': 0,
        }

    wins, losses, wr = calculate_win_rate(trades)
    total_profit = sum(t.get('profit', 0) for t in trades)
    pf = calculate_profit_factor(trades)
    avg_hold = calculate_avg_holding_time(trades)
    equity_df = build_equity_curve(trades, initial_balance)
    max_dd, _, _ = calculate_max_drawdown(equity_df['equity'].tolist()
                                          if not equity_df.empty else [])
    returns = [t.get('profit', 0) / initial_balance for t in trades
               if t.get('profit') is not None]
    sharpe = calculate_sharpe_ratio(returns, risk_free_rate, periods_per_year)
    sortino = calculate_sortino_ratio(returns, risk_free_rate, periods_per_year)
    # Estimate period from trade times
    if total_period_hours is None and trades:
        times = [t.get('exit_time') or t.get('entry_time') for t in trades if t.get('entry_time')]
        if len(times) >= 2:
            span = (max(times) - min(times)).total_seconds() / 3600
            total_period_hours = max(span, 1)
        else:
            total_period_hours = 24

    years = total_period_hours / (365.25 * 24) if total_period_hours else 1.0
    calmar = calculate_calmar_ratio(
        total_profit / initial_balance * 100 if trades else 0,
        max_dd,
        years,
    )
    final_balance = initial_balance + total_profit
    cagr = calculate_cagr(initial_balance, final_balance, max(years, 0.01))
    sqn = calculate_sqn(returns)
    expectancy = calculate_expectancy(trades, initial_balance)
    streaks = calculate_streaks(trades)
    time_market = calculate_time_in_market(trades, total_period_hours)
    monthly_df = calculate_monthly_returns(trades)

    return {
        'total_trades': len(trades),
        'wins': wins,
        'losses': losses,
        'win_rate': round(wr, 2),
        'total_profit': round(total_profit, 2),
        'profit_factor': round(pf, 3),
        'avg_hold_time_hours': round(avg_hold.total_seconds() / 3600, 2),
        'max_drawdown_pct': round(max_dd, 2),
        'sharpe_ratio': round(sharpe, 3),
        'sortino_ratio': round(sortino, 3),
        'calmar_ratio': round(calmar, 3),
        'cagr_pct': round(cagr, 3),
        'sqn': round(sqn, 3),
        'expectancy_pct': round(expectancy['expectancy_pct'], 3),
        'expectancy_ratio': round(expectancy['expectancy_ratio'], 3),
        'avg_win_pct': round(expectancy['avg_win_pct'], 3),
        'avg_loss_pct': round(expectancy['avg_loss_pct'], 3),
        'longest_win_streak': streaks['longest_win_streak'],
        'longest_loss_streak': streaks['longest_loss_streak'],
        'current_win_streak': streaks['current_win_streak'],
        'current_loss_streak': streaks['current_loss_streak'],
        'time_in_market_pct': round(time_market, 2),
        'monthly_returns': monthly_df,
    }
