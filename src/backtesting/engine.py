"""
Backtesting engine — realistic trade simulation with SL/TP, commissions, slippage.

Inspired by Freqtrade's backtesting engine and Backtrader analyzers.
"""
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from src.configuration.manager import ConfigManager
from src.strategy.interface import IStrategy
from src.analysis.performance import (
    calculate_sharpe_ratio, calculate_sortino_ratio,
    calculate_calmar_ratio, calculate_profit_factor,
    calculate_cagr, calculate_sqn, calculate_expectancy,
    calculate_streaks, calculate_monthly_returns, calculate_time_in_market,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class Backtester:
    """Backtesting engine with realistic trade simulation.

    Features:
    - Position sizing (fixed_pct)
    - Commission & slippage
    - SL/TP for each trade
    - Trailing stop-loss
    - Walk-forward validation
    - Comprehensive metrics (Sharpe, Sortino, Calmar, CAGR, SQN, etc.)
    - Winning/losing streaks, monthly returns, time in market
    """

    def __init__(self, config: ConfigManager):
        self.config = config
        self.initial_balance = config.get("backtest", "initial_balance")
        self.commission_pct = config.get("backtest", "commission_pct")
        self.slippage_pct = config.get("backtest", "slippage_pct")
        self.position_size_pct = config.get("risk_management", "position_size_pct")
        self.sl_pct = config.get("risk_management", "stop_loss_pct")
        self.tp_pct = config.get("risk_management", "take_profit_pct")
        self.use_trailing_stop = config.get("risk_management", "use_trailing_stop")
        self.trailing_activation_pct = config.get(
            "risk_management", "trailing_stop_activation_pct")
        self.trailing_distance_pct = config.get(
            "risk_management", "trailing_stop_distance_pct")
        self.results: Dict[str, Dict] = {}

    def run(self, data: pd.DataFrame, signals: pd.Series,
            strategy_name: str) -> Dict[str, Any]:
        """Run a single backtest on historical data.

        Args:
            data: OHLCV DataFrame with datetime index.
            signals: Signal Series: 1=BUY, -1=SELL, 0=HOLD.
            strategy_name: Name for result tracking.

        Returns:
            Dict with metrics (return, trades, drawdown, sharpe, sortino, calmar,
            CAGR, SQN, profit_factor, streaks, time_in_market, monthly_returns, etc.).
        """
        rng = np.random.RandomState(42 + hash(strategy_name) % 10000)
        balance = self.initial_balance
        equity_curve = [balance]
        trades: List[Dict] = []
        position = 0  # 1=long, -1=short, 0=flat
        entry_price = 0.0
        position_size = 0.0
        trailing_sl = 0.0
        last_sl = self.sl_pct

        for i in range(len(data)):
            price = float(data["close"].iloc[i])
            high = float(data["high"].iloc[i])
            low = float(data["low"].iloc[i])
            signal = int(signals.iloc[i])

            # Trailing stop check (only for long positions)
            if position == 1 and self.use_trailing_stop and entry_price > 0:
                pnl_pct = (price - entry_price) / entry_price * 100
                if pnl_pct >= self.trailing_activation_pct:
                    new_sl = price * (1 - self.trailing_distance_pct / 100.0)
                    if new_sl > trailing_sl:
                        trailing_sl = new_sl
                        last_sl = self.trailing_distance_pct

            # SL/TP checks on open positions
            if position != 0 and entry_price > 0:
                if self.use_trailing_stop and position == 1 and trailing_sl > 0:
                    if low <= trailing_sl:
                        pnl = position_size * trailing_sl
                        comm = trailing_sl * position_size * (self.commission_pct / 100.0)
                        balance += pnl - comm
                        trades.append({
                            "time": data.index[i], "action": "SELL (Trail SL)",
                            "price": trailing_sl,
                            "profit_pct": (trailing_sl - entry_price) / entry_price * 100,
                            "profit": pnl - comm - (position_size * entry_price),
                            "entry_time": data.index[i - 1] if i > 0 else data.index[i],
                        })
                        position = 0
                        position_size = 0.0
                        entry_price = 0.0
                        trailing_sl = 0.0
                        last_sl = self.sl_pct
                        equity_curve.append(balance)
                        continue

                pnl = self._check_sltp(position, entry_price, high, low,
                                       price, position_size, trades, data.index[i],
                                       sl_pct=last_sl, entry_already_deducted=True)
                if pnl is not None:
                    balance += pnl
                    position = 0
                    position_size = 0.0
                    entry_price = 0.0
                    trailing_sl = 0.0
                    last_sl = self.sl_pct
                    equity_curve.append(balance)
                    continue

            # Signal processing
            if signal == 1 and position <= 0:
                if position < 0:
                    pnl = position_size * (entry_price - price)
                    comm = price * position_size * (self.commission_pct / 100.0)
                    profit_val = pnl - comm
                    balance += profit_val
                    trades.append({
                        "time": data.index[i], "action": "BUY (cover)",
                        "price": price,
                        "profit_pct": (entry_price - price) / entry_price * 100,
                        "profit": profit_val,
                        "entry_time": data.index[i - 1] if i > 0 else data.index[i],
                    })
                    position = 0
                    position_size = 0.0

                # Open long — track cost basis
                risk_amt = balance * (self.position_size_pct / 100.0)
                pos_size = risk_amt / price if price > 0 else 0.01
                pos_size = max(0.01, round(pos_size, 4))
                slippage = price * (self.slippage_pct / 100.0) * rng.uniform(-1, 1)
                entry_price = price + slippage
                position_size = pos_size
                comm = entry_price * position_size * (self.commission_pct / 100.0)
                balance -= entry_price * position_size + comm
                position = 1
                trailing_sl = 0.0
                last_sl = self.sl_pct
                trades.append({
                    "time": data.index[i], "action": "BUY",
                    "price": entry_price, "size": position_size,
                    "entry_time": data.index[i],
                })

            elif signal == -1 and position >= 0:
                if position > 0:
                    pnl = position_size * price
                    comm = price * position_size * (self.commission_pct / 100.0)
                    profit_val = pnl - comm
                    balance += profit_val
                    trades.append({
                        "time": data.index[i], "action": "SELL",
                        "price": price,
                        "profit_pct": (price - entry_price) / entry_price * 100,
                        "profit": profit_val - (position_size * entry_price),
                        "entry_time": data.index[i - 1] if i > 0 else data.index[i],
                    })
                    position = 0
                    position_size = 0.0
                    trailing_sl = 0.0
                    last_sl = self.sl_pct

                # Open short
                risk_amt = balance * (self.position_size_pct / 100.0)
                pos_size = risk_amt / price if price > 0 else 0.01
                pos_size = max(0.01, round(pos_size, 4))
                slippage = price * (self.slippage_pct / 100.0) * rng.uniform(-1, 1)
                entry_price = price + slippage
                position_size = pos_size
                comm = entry_price * position_size * (self.commission_pct / 100.0)
                balance -= comm
                position = -1
                trades.append({
                    "time": data.index[i], "action": "SELL (short)",
                    "price": entry_price, "size": position_size,
                    "entry_time": data.index[i],
                })

            # Track equity
            equity_curve.append(self._current_equity(
                balance, position, position_size, entry_price, price))

        # Close remaining position at last price
        if position != 0 and position_size > 0:
            last_price = float(data["close"].iloc[-1])
            if position == 1:
                # For long: just proceeds (cost already deducted from balance at entry)
                pnl = position_size * last_price
            else:
                # For short: profit (no principal was deducted at entry)
                pnl = position_size * (entry_price - last_price)
            comm = last_price * position_size * (self.commission_pct / 100.0)
            balance += pnl - comm
            equity_curve[-1] = balance
            pnl_pct = (last_price - entry_price) / entry_price * 100 if position == 1 \
                else (entry_price - last_price) / entry_price * 100
            trade_profit = pnl - comm - (position_size * entry_price if position == 1 else 0)
            trades.append({
                "time": data.index[-1], "action": f"CLOSE {'LONG' if position == 1 else 'SHORT'} (end)",
                "price": last_price,
                "profit_pct": pnl_pct,
                "profit": trade_profit,
                "entry_time": trades[-1]["time"] if trades else data.index[-1],
            })

        total_return = (balance - self.initial_balance) / self.initial_balance * 100

        # ── Core Metrics ──
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.cummax()
        drawdown_series = (rolling_max - equity_series) / rolling_max * 100
        max_dd = float(drawdown_series.max()) if len(drawdown_series) > 0 else 0.0

        wins = sum(1 for t in trades if t.get("profit", t.get("profit_pct", 0)) > 0)
        losses = sum(1 for t in trades if t.get("profit", t.get("profit_pct", 0)) < 0)
        wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0

        proper_trades = []
        for t in trades:
            profit_val = t.get("profit", t.get("profit_pct", 0))
            if not isinstance(profit_val, (int, float)):
                profit_val = 0.0
            proper_trades.append({
                "profit": float(profit_val),
                "entry_time": t.get("entry_time"),
                "exit_time": t.get("time"),
            })

        # ── Advanced Metrics ──
        returns = [t.get("profit", 0) / self.initial_balance for t in proper_trades]
        sharpe = calculate_sharpe_ratio(returns)
        sortino = calculate_sortino_ratio(returns)
        pf = calculate_profit_factor(proper_trades)
        calmar = calculate_calmar_ratio(total_return, max_dd, 1.0)

        total_period_hours = None
        trade_times = [
            t.get("time") for t in trades
            if isinstance(t.get("time"), pd.Timestamp)
        ]
        if len(trade_times) >= 2:
            span = (max(trade_times) - min(trade_times)).total_seconds() / 3600
            total_period_hours = max(span, 1)

        years = total_period_hours / (365.25 * 24) if total_period_hours else 1.0
        cagr = calculate_cagr(self.initial_balance, balance, max(years, 0.01))
        sqn = calculate_sqn(returns)
        expectancy = calculate_expectancy(proper_trades, self.initial_balance)
        streaks = calculate_streaks(proper_trades)
        time_market = calculate_time_in_market(proper_trades, total_period_hours)
        monthly_df = calculate_monthly_returns(proper_trades)

        result = {
            "total_return": total_return,
            "final_balance": balance,
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
        self.results[strategy_name] = result
        return result

    def run_strategy(self, data: pd.DataFrame, strategy: IStrategy,
                     strategy_name: str) -> Dict[str, Any]:
        signals = strategy.calculate_signals(data)
        return self.run(data, signals, strategy_name)

    def run_walk_forward(self, data: pd.DataFrame,
                          signal_generator: Callable,
                          strategy_name: str,
                          train_frac: float = 0.7,
                          n_windows: int = 3) -> Dict[str, Any]:
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
            result = self.run(test_data, signals, f"{strategy_name}_w{w}")
            window_results.append(result)
            all_trades.extend(result.get("trades", []))

        if not window_results:
            return {"total_return": 0, "num_trades": 0, "max_drawdown": 0,
                    "win_rate": 0, "sharpe_ratio": 0, "equity_curve": [self.initial_balance],
                    "trades": []}

        avg_return = float(np.mean([r["total_return"] for r in window_results]))
        return {
            "total_return": avg_return,
            "num_trades": sum(r["num_trades"] for r in window_results),
            "max_drawdown": float(max(r.get("max_drawdown", 0) for r in window_results)),
            "win_rate": float(np.mean([r.get("win_rate", 0) for r in window_results])),
            "sharpe_ratio": float(np.mean([r.get("sharpe_ratio", 0) for r in window_results])),
            "equity_curve": [self.initial_balance],
            "trades": all_trades,
            "window_results": window_results,
        }

    def compare_strategies(self) -> pd.DataFrame:
        if not self.results:
            return pd.DataFrame()
        rows = []
        for name, r in self.results.items():
            rows.append({
                "Strategy": name,
                "Return %": round(r["total_return"], 2),
                "Trades": r["num_trades"],
                "Win Rate %": r.get("win_rate", 0),
                "Max DD %": r.get("max_drawdown", 0),
                "Sharpe": r.get("sharpe_ratio", 0),
                "Sortino": r.get("sortino_ratio", 0),
                "Profit Factor": r.get("profit_factor", 0),
                "CAGR %": r.get("cagr_pct", 0),
                "SQN": r.get("sqn", 0),
                "Time In Mkt %": r.get("time_in_market_pct", 0),
            })
        df = pd.DataFrame(rows).sort_values("Return %", ascending=False)
        return df

    # ── Internal helpers ──────────────────────────────────────

    def _check_sltp(self, position, entry, high, low, price, size, trades, idx,
                    sl_pct=None, entry_already_deducted=False):
        sl_pct = sl_pct or self.sl_pct
        tp_pct = self.tp_pct

        if position == 1:
            sl = entry * (1 - sl_pct / 100.0)
            tp = entry * (1 + tp_pct / 100.0)
            if low <= sl:
                pnl = size * sl
                comm = sl * size * (self.commission_pct / 100.0)
                trades.append({"time": idx, "action": "SELL (SL)",
                               "price": sl,
                               "profit_pct": (sl - entry) / entry * 100,
                               "entry_time": idx})
                return pnl - comm - (size * entry if not entry_already_deducted else 0)
            elif high >= tp:
                pnl = size * tp
                comm = tp * size * (self.commission_pct / 100.0)
                trades.append({"time": idx, "action": "SELL (TP)",
                               "price": tp,
                               "profit_pct": (tp - entry) / entry * 100,
                               "entry_time": idx})
                return pnl - comm - (size * entry if not entry_already_deducted else 0)
        else:
            sl = entry * (1 + sl_pct / 100.0)
            tp = entry * (1 - tp_pct / 100.0)
            if high >= sl:
                pnl = size * (entry - sl)
                comm = sl * size * (self.commission_pct / 100.0)
                trades.append({"time": idx, "action": "BUY (SL)",
                               "price": sl,
                               "profit_pct": (entry - sl) / entry * 100,
                               "entry_time": idx})
                return pnl - comm
            elif low <= tp:
                pnl = size * (entry - tp)
                comm = tp * size * (self.commission_pct / 100.0)
                trades.append({"time": idx, "action": "BUY (TP)",
                               "price": tp,
                               "profit_pct": (entry - tp) / entry * 100,
                               "entry_time": idx})
                return pnl - comm
        return None

    @staticmethod
    def _current_equity(balance, position, size, entry, price):
        if position == 1 and size > 0:
            return balance + size * price
        elif position == -1 and size > 0:
            return balance + size * (entry - price)
        return balance

    @staticmethod
    def _close_position(position, size, entry, price):
        if position == 1:
            return size * price - size * entry
        return size * (entry - price)
