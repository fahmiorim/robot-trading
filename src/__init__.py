"""
AI Trading Robot - Package Root.

Re-exports key symbols for backward compatibility.
"""
from src.strategy.implementations.ma_crossover import MACrossoverStrategy as MovingAverageCrossover  # noqa: F401
from src.strategy.implementations.rsi import RSIStrategy  # noqa: F401
from src.strategy.implementations.macd import MACDStrategy  # noqa: F401
from src.strategy.implementations.bollinger import BollingerStrategy as BollingerBandsStrategy  # noqa: F401
from src.strategy.implementations.breakout import BreakoutStrategy  # noqa: F401
from src.ml.model import MLModel  # noqa: F401
from src.backtesting.engine import Backtester  # noqa: F401
from src.configuration.manager import ConfigManager  # noqa: F401
from src.risk.manager import RiskManager  # noqa: F401
from src.services.trading.engine import TradingBot as AIRobot  # noqa: F401

# ── MVC Architecture (v2.2.0) ──
# Models (pure data)
from src.models import (  # noqa: F401
    Trade, TradeManager, SignalResult, AggregatedSignal,
    BacktestResult, HyperoptResult, OHLCV, MarketFrame,
    BotConfig, RiskState, CircuitBreakerEvent,
)

# Repositories (data access)
from src.repositories import (  # noqa: F401
    TradeRepository, SettingsRepository, AnalyticsRepository,
    MarketDataRepository, RiskRepository,
)

# Services (business logic)
from src.services import (  # noqa: F401
    SignalService, StrategyService, TradeExecutionService,
    MLService, RiskService, NotificationService, BacktestService,
)

# Controllers (thin orchestration)
from src.controllers import (  # noqa: F401
    TradingController, AnalysisController, DashboardController,
)

__version__ = "2.2.0"
