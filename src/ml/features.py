"""
Advanced feature engineering for ML models.

Provides sliding-window indicator computation so features
always reflect the most recent market conditions.
"""
import pandas as pd
import numpy as np
from typing import List, Dict

from src.analysis.indicators import calculate_rsi, calculate_sma, calculate_ema, \
    calculate_bollinger_bands, calculate_adx, calculate_macd, calculate_atr


class FeatureEngineer:
    """Creates and manages feature sets for ML model training.

    Supports sliding-window feature computation so the model
    is always trained on the most recent market regime.
    """

    DEFAULT_FEATURES: List[str] = [
        "returns_1", "returns_5", "returns_10",
        "sma_10", "sma_20", "sma_50",
        "ema_12", "ema_26",
        "rsi_14",
        "bb_upper", "bb_lower", "bb_width",
        "adx_14",
        "macd", "macd_signal", "macd_hist",
        "atr_14",
        "volume_change",
        "volatility_10", "volatility_20",
    ]

    def __init__(self):
        self._feature_names: List[str] = self.DEFAULT_FEATURES.copy()

    def compute_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Compute the full feature set from OHLCV data."""
        close = data["close"]
        high = data["high"]
        low = data["low"]
        volume_col = "volume" if "volume" in data.columns else "tick_volume"
        volume = data.get(volume_col, pd.Series(0, index=data.index))

        features = pd.DataFrame(index=data.index)

        # Returns
        features["returns_1"] = close.pct_change(1)
        features["returns_5"] = close.pct_change(5)
        features["returns_10"] = close.pct_change(10)

        # Moving averages
        features["sma_10"] = calculate_sma(close, 10)
        features["sma_20"] = calculate_sma(close, 20)
        features["sma_50"] = calculate_sma(close, 50)
        features["ema_12"] = calculate_ema(close, 12)
        features["ema_26"] = calculate_ema(close, 26)

        # RSI
        features["rsi_14"] = calculate_rsi(close, 14)

        # Bollinger Bands
        _, bb_upper, bb_lower = calculate_bollinger_bands(close, 20, 2.0)
        features["bb_upper"] = (bb_upper - close) / close
        features["bb_lower"] = (close - bb_lower) / close
        features["bb_width"] = (bb_upper - bb_lower) / close

        # ADX
        features["adx_14"] = calculate_adx(high, low, close, 14)

        # MACD
        macd_line, signal_line, hist = calculate_macd(close, 12, 26, 9)
        features["macd"] = macd_line
        features["macd_signal"] = signal_line
        features["macd_hist"] = hist

        # ATR
        features["atr_14"] = calculate_atr(high, low, close, 14)

        # Volume
        features["volume_change"] = volume.pct_change()

        # Volatility
        features["volatility_10"] = close.pct_change().rolling(10).std()
        features["volatility_20"] = close.pct_change().rolling(20).std()

        return features.replace([np.inf, -np.inf], np.nan).dropna()

    def get_feature_names(self) -> List[str]:
        return self._feature_names.copy()

    def sliding_window_train_data(
        self, data: pd.DataFrame, window_size: int = 2000, step: int = 200
    ) -> List[pd.DataFrame]:
        """Generate sliding windows of training data for walk-forward training."""
        features = self.compute_features(data)
        if len(features) < window_size:
            return [features]
        windows = []
        for start in range(0, len(features) - window_size + 1, step):
            windows.append(features.iloc[start:start + window_size])
        if len(features) > windows[-1].index[-1] + step:
            windows.append(features.iloc[-window_size:])
        return windows
