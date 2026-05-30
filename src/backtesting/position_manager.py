"""
Backtesting position management — SL/TP checks and equity tracking.

Standalone helpers used by ``Backtester.run()``.
"""

from typing import Any, Dict, List, Optional


def check_sltp(position: int, entry: float, high: float, low: float,
               price: float, size: float, trades: List[Dict], idx,
               sl_pct: float = 1.0, tp_pct: float = 2.0,
               commission_pct: float = 0.0,
               entry_already_deducted: bool = False,
               entry_time=None, entry_comm: float = 0.0):
    """Check if stop-loss or take-profit has been hit.

    Returns the profit/loss if triggered, otherwise None.
    """
    if position == 1:
        sl = entry * (1 - sl_pct / 100.0)
        tp = entry * (1 + tp_pct / 100.0)
        if low <= sl:
            pnl = size * sl
            comm = sl * size * (commission_pct / 100.0)
            profit_val = pnl - comm - (size * entry) - entry_comm
            trades.append({
                "time": idx, "action": "SELL (SL)",
                "price": sl,
                "profit_pct": (sl - entry) / entry * 100,
                "profit": profit_val,
                "entry_time": entry_time or idx,
            })
            return pnl - comm - (size * entry if not entry_already_deducted else 0)
        elif high >= tp:
            pnl = size * tp
            comm = tp * size * (commission_pct / 100.0)
            profit_val = pnl - comm - (size * entry) - entry_comm
            trades.append({
                "time": idx, "action": "SELL (TP)",
                "price": tp,
                "profit_pct": (tp - entry) / entry * 100,
                "profit": profit_val,
                "entry_time": entry_time or idx,
            })
            return pnl - comm - (size * entry if not entry_already_deducted else 0)
    else:
        sl = entry * (1 + sl_pct / 100.0)
        tp = entry * (1 - tp_pct / 100.0)
        if high >= sl:
            comm = sl * size * (commission_pct / 100.0)
            profit_val = (entry - sl) * size - comm - entry_comm
            trades.append({
                "time": idx, "action": "BUY (SL)",
                "price": sl,
                "profit_pct": (entry - sl) / entry * 100,
                "profit": profit_val,
                "entry_time": entry_time or idx,
            })
            if entry_already_deducted:
                return -sl * size - comm
            return profit_val
        elif low <= tp:
            comm = tp * size * (commission_pct / 100.0)
            profit_val = (entry - tp) * size - comm - entry_comm
            trades.append({
                "time": idx, "action": "BUY (TP)",
                "price": tp,
                "profit_pct": (entry - tp) / entry * 100,
                "profit": profit_val,
                "entry_time": entry_time or idx,
            })
            if entry_already_deducted:
                return -tp * size - comm
            return profit_val
    return None


def current_equity(balance: float, position: int,
                   size: float, entry: float, price: float) -> float:
    """Calculate current account equity with open position."""
    if position == 1 and size > 0:
        return balance + size * price
    elif position == -1 and size > 0:
        return balance - size * price
    return balance


def close_position(position: int, size: float,
                   entry: float, price: float) -> float:
    """Calculate PnL for closing a position."""
    if position == 1:
        return size * price - size * entry
    return size * (entry - price)
