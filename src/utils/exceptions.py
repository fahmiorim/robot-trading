"""
Custom exceptions for the trading bot.
"""


class TradingBotError(Exception):
    """Base exception for all trading bot errors."""


class ExchangeError(TradingBotError):
    """Exchange-level error (connection, order, data)."""


class ConnectionError(ExchangeError):
    """Exchange connection failed."""


class OrderError(ExchangeError):
    """Order placement or cancellation failed."""


class InvalidPriceError(OrderError):
    """Invalid price value."""


class InvalidVolumeError(OrderError):
    """Invalid volume/lot size."""


class DataFetchError(TradingBotError):
    """Market data fetch failed."""


class MLTrainingError(TradingBotError):
    """ML model training failed."""


class MLPredictionError(TradingBotError):
    """ML model prediction failed."""


class StrategyError(TradingBotError):
    """Strategy instantiation or execution error."""


class ConfigError(TradingBotError):
    """Configuration error."""
