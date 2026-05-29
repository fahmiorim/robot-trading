"""
Advanced feature engineering for ML models.

Provides sliding-window indicator computation so features
always reflect the most recent market conditions.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional

from src.analysis.indicators import calculate_rsi, calculate_sma, calculate_ema, \
    calculate_bollinger_bands, calculate_adx, calculate_macd, calculate_atr
from src.configuration.manager import ConfigManager


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

    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config or ConfigManager()
        self._feature_names: List[str] = self.DEFAULT_FEATURES.copy()

    def compute_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Compute the full feature set from OHLCV data."""
        close = data["close"]
        high = data["high"]
        low = data["low"]
        volume_col = "volume" if "volume" in data.columns else "tick_volume"
        volume = data.get(volume_col, pd.Series(0, index=data.index))

        features = pd.DataFrame(index=data.index)

        ret_period_1 = self.config.get("features", "returns_period_1")
        ret_period_5 = self.config.get("features", "returns_period_5")
        ret_period_10 = self.config.get("features", "returns_period_10")

        features["returns_1"] = close.pct_change(ret_period_1)
        features["returns_5"] = close.pct_change(ret_period_5)
        features["returns_10"] = close.pct_change(ret_period_10)

        sma_fast = self.config.get("agent", "sma_fast_period")
        sma_medium = self.config.get("features", "sma_medium_period")
        sma_slow = self.config.get("agent", "sma_slow_period")

        # Relative SMAs & EMAs (fractional difference from close price)
        features["sma_10"] = (close - calculate_sma(close, sma_fast)) / close
        features["sma_20"] = (close - calculate_sma(close, sma_medium)) / close
        features["sma_50"] = (close - calculate_sma(close, sma_slow)) / close
        features["ema_12"] = (close - calculate_ema(close, self.config.get("features", "ema_fast_period"))) / close
        features["ema_26"] = (close - calculate_ema(close, self.config.get("features", "ema_slow_period"))) / close

        features["rsi_14"] = calculate_rsi(close, self.config.get("features", "rsi_period"))

        bb_period = self.config.get("features", "bb_period")
        bb_std = self.config.get("features", "bb_std_dev")
        _, bb_upper, bb_lower = calculate_bollinger_bands(close, bb_period, bb_std)
        features["bb_upper"] = (bb_upper - close) / close
        features["bb_lower"] = (close - bb_lower) / close
        features["bb_width"] = (bb_upper - bb_lower) / close

        features["adx_14"] = calculate_adx(high, low, close, self.config.get("features", "adx_period"))

        macd_fast = self.config.get("features", "macd_fast_period")
        macd_slow = self.config.get("features", "macd_slow_period")
        macd_signal_period = self.config.get("features", "macd_signal_period")
        macd_line, signal_line, hist = calculate_macd(close, macd_fast, macd_slow, macd_signal_period)
        features["macd"] = macd_line / close
        features["macd_signal"] = signal_line / close
        features["macd_hist"] = hist / close

        features["atr_14"] = calculate_atr(high, low, close, self.config.get("features", "atr_period")) / close

        features["volume_change"] = volume.pct_change()

        vol_window_fast = self.config.get("features", "volatility_window_fast")
        vol_window = self.config.get("agent", "volatility_window")
        features["volatility_10"] = close.pct_change().rolling(vol_window_fast).std()
        features["volatility_20"] = close.pct_change().rolling(vol_window).std()

        return features.replace([np.inf, -np.inf], np.nan).dropna()

    def get_feature_names(self) -> List[str]:
        return self._feature_names.copy()

    def sliding_window_train_data(
        self, data: pd.DataFrame, window_size: int, step: int
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
