"""Configuration domain models — typed wrappers over raw config dicts."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ExchangeConfig:
    type: str
    name: str
    api_key: str
    secret: str
    password: str
    sandbox: bool
    options: Optional[Dict]


@dataclass
class GeneralConfig:
    symbol: str
    timeframe: str
    magic_number: int
    cycle_interval_minutes: int
    auto_trade: bool


@dataclass
class RiskConfig:
    position_size_pct: float
    max_drawdown_pct: float
    max_daily_loss_pct: float
    stop_loss_pct: float
    take_profit_pct: float
    max_open_positions: int
    use_trailing_stop: bool
    trailing_stop_activation_pct: float
    trailing_stop_distance_pct: float


@dataclass
class TradingConfig:
    mode: str
    strategy_pre_validation: bool
    min_backtest_trades: int
    min_win_rate: float
    max_backtest_drawdown: float


@dataclass
class MLConfig:
    model_type: str
    retrain_interval_hours: int


@dataclass
class BacktestConfig:
    initial_balance: float
    commission_pct: float
    slippage_pct: float


@dataclass
class BotConfig:
    """Complete typed bot configuration — all fields must be provided from DB."""
    general: GeneralConfig
    exchange: ExchangeConfig
    risk: RiskConfig
    trading: TradingConfig
    ml: MLConfig
    backtest: BacktestConfig
    raw: Dict[str, Any]
