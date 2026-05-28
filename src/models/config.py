"""Configuration domain models — typed wrappers over raw config dicts."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ExchangeConfig:
    type: str = "mt5"
    name: str = "MetaTrader"
    api_key: str = ""
    secret: str = ""
    password: str = ""
    sandbox: bool = False
    options: Optional[Dict] = None


@dataclass
class GeneralConfig:
    symbol: str = "XAUUSD"
    timeframe: str = "TIMEFRAME_M15"
    magic_number: int = 123456
    cycle_interval_minutes: int = 15
    auto_trade: bool = False


@dataclass
class RiskConfig:
    position_size_pct: float = 1.0
    max_drawdown_pct: float = 20.0
    max_daily_loss_pct: float = 5.0
    stop_loss_pct: float = 1.0
    take_profit_pct: float = 2.0
    max_open_positions: int = 5
    use_trailing_stop: bool = False
    trailing_stop_activation_pct: float = 0.5
    trailing_stop_distance_pct: float = 0.3


@dataclass
class TradingConfig:
    mode: str = "paper"       # paper / live / dry-run
    strategy_pre_validation: bool = False
    min_backtest_trades: int = 5
    min_win_rate: float = 50.0
    max_backtest_drawdown: float = 30.0


@dataclass
class MLConfig:
    model_type: str = "random_forest"
    retrain_interval_hours: int = 24


@dataclass
class BacktestConfig:
    initial_balance: float = 10000.0
    commission_pct: float = 0.1
    slippage_pct: float = 0.05


@dataclass
class BotConfig:
    """Complete typed bot configuration."""
    general: GeneralConfig = None
    exchange: ExchangeConfig = None
    risk: RiskConfig = None
    trading: TradingConfig = None
    ml: MLConfig = None
    backtest: BacktestConfig = None
    raw: Dict[str, Any] = None

    def __post_init__(self):
        if self.general is None:
            self.general = GeneralConfig()
        if self.exchange is None:
            self.exchange = ExchangeConfig()
        if self.risk is None:
            self.risk = RiskConfig()
        if self.trading is None:
            self.trading = TradingConfig()
        if self.ml is None:
            self.ml = MLConfig()
        if self.backtest is None:
            self.backtest = BacktestConfig()
        if self.raw is None:
            self.raw = {}
