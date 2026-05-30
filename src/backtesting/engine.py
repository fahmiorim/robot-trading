"""
Backtesting engine — realistic trade simulation with SL/TP, commissions, slippage.

Inspired by Freqtrade's backtesting engine and Backtrader analyzers.
"""
from typing import Any, Callable, Dict, List

import numpy as np
import pandas as pd

from src.configuration.manager import ConfigManager
from src.strategy.interface import IStrategy
from src.backtesting.position_manager import check_sltp, current_equity
from src.backtesting.metrics import compute_metrics
from src.backtesting.walk_forward import run_walk_forward
from src.utils.logging import get_logger

logger = get_logger(__name__)

RANDOM_SEED = 42
MIN_POSITION_SIZE = 0.01


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
            Dict with all performance metrics.
        """
        rng = np.random.RandomState(RANDOM_SEED + hash(strategy_name) % 10000)
        balance = self.initial_balance
        equity_curve = [balance]
        trades: List[Dict] = []
        position = 0  # 1=long, -1=short, 0=flat
        entry_price = 0.0
        position_size = 0.0
        trailing_sl = 0.0
        last_sl = self.sl_pct
        entry_time = None
        entry_comm = 0.0

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
                            "profit": pnl - comm - (position_size * entry_price) - entry_comm,
                            "entry_time": entry_time,
                        })
                        position = 0
                        position_size = 0.0
                        entry_price = 0.0
                        trailing_sl = 0.0
                        entry_time = None
                        last_sl = self.sl_pct
                        equity_curve.append(balance)
                        continue

                pnl = check_sltp(position, entry_price, high, low,
                                 price, position_size, trades, data.index[i],
                                 sl_pct=last_sl, tp_pct=self.tp_pct,
                                 commission_pct=self.commission_pct,
                                 entry_already_deducted=True,
                                 entry_time=entry_time, entry_comm=entry_comm)
                if pnl is not None:
                    balance += pnl
                    position = 0
                    position_size = 0.0
                    entry_price = 0.0
                    trailing_sl = 0.0
                    entry_time = None
                    last_sl = self.sl_pct
                    equity_curve.append(balance)
                    continue

            # Signal processing
            if signal == 1 and position <= 0:
                if position < 0:
                    comm = price * position_size * (self.commission_pct / 100.0)
                    profit_val = (entry_price - price) * position_size - comm
                    balance -= price * position_size + comm
                    trades.append({
                        "time": data.index[i], "action": "BUY (cover)",
                        "price": price,
                        "profit_pct": (entry_price - price) / entry_price * 100,
                        "profit": profit_val - entry_comm,
                        "entry_time": entry_time,
                    })
                    position = 0
                    position_size = 0.0
                    entry_time = None

                # Open long
                risk_amt = balance * (self.position_size_pct / 100.0)
                pos_size = risk_amt / price if price > 0 else 0.01
                pos_size = max(MIN_POSITION_SIZE, round(pos_size, 4))
                slippage = price * (self.slippage_pct / 100.0) * rng.uniform(-1, 1)
                entry_price = price + slippage
                position_size = pos_size
                comm = entry_price * position_size * (self.commission_pct / 100.0)
                balance -= entry_price * position_size + comm
                position = 1
                trailing_sl = 0.0
                last_sl = self.sl_pct
                entry_time = data.index[i]
                entry_comm = comm
                trades.append({
                    "time": data.index[i], "action": "BUY",
                    "price": entry_price, "size": position_size,
                    "entry_time": entry_time,
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
                        "profit": profit_val - (position_size * entry_price) - entry_comm,
                        "entry_time": entry_time,
                    })
                    position = 0
                    position_size = 0.0
                    trailing_sl = 0.0
                    entry_time = None
                    last_sl = self.sl_pct

                # Open short
                risk_amt = balance * (self.position_size_pct / 100.0)
                pos_size = risk_amt / price if price > 0 else 0.01
                pos_size = max(MIN_POSITION_SIZE, round(pos_size, 4))
                slippage = price * (self.slippage_pct / 100.0) * rng.uniform(-1, 1)
                entry_price = price + slippage
                position_size = pos_size
                comm = entry_price * position_size * (self.commission_pct / 100.0)
                balance += entry_price * position_size - comm
                position = -1
                entry_time = data.index[i]
                entry_comm = comm
                trades.append({
                    "time": data.index[i], "action": "SELL (short)",
                    "price": entry_price, "size": position_size,
                    "entry_time": entry_time,
                })

            # Track equity
            equity_curve.append(
                current_equity(balance, position, position_size, entry_price, price)
            )

        # Close remaining position at last price
        if position != 0 and position_size > 0:
            last_price = float(data["close"].iloc[-1])
            if position == 1:
                pnl = position_size * last_price
            else:
                pnl = -position_size * last_price
            comm = last_price * position_size * (self.commission_pct / 100.0)
            balance += pnl - comm
            equity_curve[-1] = balance
            pnl_pct = (last_price - entry_price) / entry_price * 100 if position == 1 \
                else (entry_price - last_price) / entry_price * 100
            if position == 1:
                trade_profit = pnl - comm - (position_size * entry_price) - entry_comm
            else:
                trade_profit = (entry_price - last_price) * position_size - comm - entry_comm
            trades.append({
                "time": data.index[-1], "action": f"CLOSE {'LONG' if position == 1 else 'SHORT'} (end)",
                "price": last_price,
                "profit_pct": pnl_pct,
                "profit": trade_profit,
                "entry_time": entry_time or data.index[-1],
            })

        # ── Compute all metrics via extracted helper ──
        result = compute_metrics(trades, equity_curve, self.initial_balance, data)
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
        return run_walk_forward(
            data, signal_generator, strategy_name,
            n_windows=n_windows, train_frac=train_frac,
            run_fn=self.run,
            initial_balance=self.initial_balance,
        )

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
