"""Domain models — pure data classes with no I/O dependencies.

Usage:
    from src.models.trade import Trade, TradeManager
    from src.models.signal import SignalResult, AggregatedSignal
    from src.models.backtest import BacktestResult, HyperoptResult
    from src.models.market_data import MarketFrame, MarketRegime
    from src.models.config import BotConfig, GeneralConfig, RiskConfig
    from src.models.risk import RiskState, CircuitBreakerEvent
"""

from src.models.trade import Trade, TradeManager
from src.models.signal import SignalResult, AggregatedSignal, SignalLogEntry
from src.models.backtest import BacktestResult, HyperoptResult, TradeRecord, WalkForwardResult
from src.models.market_data import OHLCV, MarketFrame, MarketRegime
from src.models.config import BotConfig, GeneralConfig, ExchangeConfig, RiskConfig, TradingConfig, MLConfig, BacktestConfig
from src.models.risk import RiskState, DrawdownInfo, ProtectionRule, CircuitBreakerEvent

__all__ = [
    "Trade", "TradeManager",
    "SignalResult", "AggregatedSignal", "SignalLogEntry",
    "BacktestResult", "HyperoptResult", "TradeRecord", "WalkForwardResult",
    "OHLCV", "MarketFrame", "MarketRegime",
    "BotConfig", "GeneralConfig", "ExchangeConfig", "RiskConfig",
    "TradingConfig", "MLConfig", "BacktestConfig",
    "RiskState", "DrawdownInfo", "ProtectionRule", "CircuitBreakerEvent",
]
