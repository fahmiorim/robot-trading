"""Backtest domain models — pure data classes for backtest results."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TradeRecord:
    """A single trade in a backtest simulation."""
    time: Any
    action: str
    price: float
    profit_pct: float = 0.0
    profit: float = 0.0
    size: float = 0.0
    entry_time: Any = None


@dataclass
class BacktestResult:
    """Complete result of a strategy backtest."""
    strategy_name: str
    total_return: float = 0.0
    final_balance: float = 0.0
    num_trades: int = 0
    wins: int = 0
    losses: int = 0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    profit_factor: float = 0.0
    cagr_pct: float = 0.0
    sqn: float = 0.0
    expectancy_pct: float = 0.0
    expectancy_ratio: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    longest_win_streak: int = 0
    longest_loss_streak: int = 0
    current_win_streak: int = 0
    current_loss_streak: int = 0
    time_in_market_pct: float = 0.0
    trades: List[TradeRecord] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    monthly_returns: Any = None

    @property
    def is_profitable(self) -> bool:
        return self.total_return > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "total_return": self.total_return,
            "final_balance": self.final_balance,
            "num_trades": self.num_trades,
            "win_rate": self.win_rate,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
        }


@dataclass
class HyperoptResult:
    """Result of hyperparameter optimization."""
    strategy_name: str
    best_params: Dict[str, Any] = field(default_factory=dict)
    best_score: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    n_trials: int = 0
    elapsed_seconds: float = 0.0


@dataclass
class WalkForwardResult:
    """Result of walk-forward validation."""
    total_return: float = 0.0
    num_trades: int = 0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    trades: List[TradeRecord] = field(default_factory=list)
    window_results: List[BacktestResult] = field(default_factory=list)
