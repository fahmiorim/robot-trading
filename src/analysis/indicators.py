"""
Shared technical indicator functions.
Source of truth for all indicator calculations to avoid DRY violations.
"""

import pandas as pd


def calculate_rsi(prices: pd.Series, period: int) -> pd.Series:
    """Relative Strength Index (Wilder's - 0-100)."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))
    
    # Use exponential moving average (Wilder's method)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / (avg_loss + 1e-10)
    return 100 - (100 / (1 + rs))


def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return prices.rolling(period).mean()


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return prices.ewm(span=period, adjust=False).mean()


def calculate_bollinger_bands(
    prices: pd.Series, period: int, std_dev: float
) -> tuple:
    """Return (middle, upper, lower) Bollinger Bands."""
    ma = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    upper = ma + (std * std_dev)
    lower = ma - (std * std_dev)
    return ma, upper, lower


def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series,
                  period: int) -> pd.Series:
    """Average Directional Index."""
    plus_dm = (high - high.shift(1)).clip(lower=0)
    minus_dm = (low.shift(1) - low).clip(lower=0)
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    plus_di = 100 * (plus_dm / (tr + 1e-10)).rolling(period).mean()
    minus_di = 100 * (minus_dm / (tr + 1e-10)).rolling(period).mean()
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
    return dx.ewm(span=period).mean()


def calculate_macd(prices: pd.Series, fast: int, slow: int,
                   signal: int) -> tuple:
    """Return (MACD line, signal line, histogram)."""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series,
                  period: int) -> pd.Series:
    """Average True Range."""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()
