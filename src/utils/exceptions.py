"""
Custom exceptions for the trading bot.
"""


class TradingBotError(Exception):
    """Base exception for all trading bot errors."""
    pass


class ExchangeError(TradingBotError):
    """Exchange-level error (connection, order, data)."""
    pass


class ConnectionError(ExchangeError):
    """Exchange connection failed."""
    pass


class OrderError(ExchangeError):
    """Order placement or cancellation failed."""
    pass


class InvalidPriceError(OrderError):
    """Invalid price value."""
    pass


class InvalidVolumeError(OrderError):
    """Invalid volume/lot size."""
    pass


class DataFetchError(TradingBotError):
    """Market data fetch failed."""
    pass


class MLTrainingError(TradingBotError):
    """ML model training failed."""
    pass


class MLPredictionError(TradingBotError):
    """ML model prediction failed."""
    pass


class StrategyError(TradingBotError):
    """Strategy instantiation or execution error."""
    pass


class ConfigError(TradingBotError):
    """Configuration error."""
    pass
