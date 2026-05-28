"""
ML trading model — scikit-learn classifiers for signal prediction.

Wraps RandomForest / GradientBoosting with feature engineering,
training, prediction, and persistence.
"""
from typing import Optional

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

from src.utils.exceptions import MLTrainingError, MLPredictionError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MLModel:
    """Machine learning model for trading signal prediction.

    Default: RandomForest with 100 estimators.
    Supports: random_forest, gradient_boosting.
    """

    def __init__(self, model_type: str = "random_forest"):
        self.model_type = model_type
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model = self._init_model()

    def _init_model(self):
        if self.model_type == "gradient_boosting":
            return GradientBoostingClassifier(n_estimators=100, random_state=42)
        return RandomForestClassifier(n_estimators=100, random_state=42)

    # ── Feature Engineering ───────────────────────────────────

    @staticmethod
    def create_features(data: pd.DataFrame) -> pd.DataFrame:
        """Build feature matrix from OHLCV data."""
        from src.analysis.indicators import calculate_rsi

        features = pd.DataFrame(index=data.index)
        features["returns"] = data["close"].pct_change()
        features["sma_10"] = data["close"].rolling(10).mean()
        features["sma_20"] = data["close"].rolling(20).mean()
        features["rsi"] = calculate_rsi(data["close"])
        features["volatility"] = data["close"].rolling(20).std()
        volume_col = "volume" if "volume" in data.columns else "tick_volume"
        if volume_col in data.columns:
            features["volume_change"] = data[volume_col].pct_change()
        else:
            features["volume_change"] = 0.0
        return features.dropna()

    @staticmethod
    def create_target(data: pd.DataFrame, horizon: int = 5) -> pd.Series:
        """Create classification target: 1=up, -1=down, 0=flat."""
        future_returns = data["close"].shift(-horizon) / data["close"] - 1
        target = pd.Series(0, index=data.index)
        target[future_returns > 0.005] = 1
        target[future_returns < -0.005] = -1
        return target

    # ── Training ──────────────────────────────────────────────

    def train(self, data: pd.DataFrame, horizon: int = 5,
              save_path: Optional[str] = None) -> float:
        """Train the model on historical data.

        Returns test accuracy.
        """
        features = self.create_features(data)
        target = self.create_target(data, horizon)
        common = features.index.intersection(target.index)
        X = features.loc[common].values
        y = target.loc[common].values

        if len(X) < 50:
            raise MLTrainingError(f"Not enough samples ({len(X)}), need at least 50")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        self.model.fit(X_train_scaled, y_train)
        preds = self.model.predict(X_test_scaled)
        accuracy = float(accuracy_score(y_test, preds))
        self.is_trained = True
        logger.info(f"ML model trained: accuracy={accuracy:.2%}")

        if save_path:
            self.save(save_path)
        return accuracy

    def predict(self, data: pd.DataFrame) -> np.ndarray:
        """Predict signal for the latest candle only.

        Returns numpy array of shape (1,) with value -1, 0, or 1.
        """
        if not self.is_trained:
            raise MLPredictionError("Model not trained — call train() first")
        features = self.create_features(data)
        if len(features) == 0:
            return np.array([0])
        X = self.scaler.transform(features.values)
        return self.model.predict(X[-1:])

    def predict_proba(self, data: pd.DataFrame) -> np.ndarray:
        """Return class probabilities for the latest candle."""
        if not self.is_trained:
            return np.array([[0.33, 0.34, 0.33]])
        features = self.create_features(data)
        if len(features) == 0:
            return np.array([[0.33, 0.34, 0.33]])
        X = self.scaler.transform(features.values)
        return self.model.predict_proba(X[-1:])

    # ── Persistence ───────────────────────────────────────────

    def save(self, filepath: str) -> None:
        joblib.dump({"model": self.model, "scaler": self.scaler}, filepath)
        logger.info(f"ML model saved to {filepath}")

    def load(self, filepath: str) -> bool:
        """Load model from disk. Returns True on success."""
        try:
            loaded = joblib.load(filepath)
            self.model = loaded["model"]
            self.scaler = loaded["scaler"]
            self.is_trained = True
            logger.info(f"ML model loaded from {filepath}")
            return True
        except Exception as e:
            logger.warning(f"Failed to load ML model from {filepath}: {e}")
            return False
