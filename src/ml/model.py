"""
ML trading model — scikit-learn classifiers for signal prediction.

Wraps RandomForest / GradientBoosting with feature engineering,
training, prediction, and persistence.
"""
import time
from typing import Optional

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

from src.configuration.manager import ConfigManager
from src.utils.exceptions import MLTrainingError, MLPredictionError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MLModel:
    """Machine learning model for trading signal prediction.

    Default: RandomForest with 100 estimators.
    Supports: random_forest, gradient_boosting.
    """

    def __init__(self, model_type: str, config: Optional[ConfigManager] = None):
        self.model_type = model_type
        self.config = config or ConfigManager()
        self.scaler = StandardScaler()
        self.is_trained = False
        self.last_train_stats = None
        self.model = self._init_model()

    def _init_model(self):
        n_estimators = self.config.get("ml", "n_estimators")
        max_depth = self.config.get("ml", "max_depth")
        min_samples_split = self.config.get("ml", "min_samples_split")

        # The string "None" from DB settings gets converted to Python None
        if isinstance(max_depth, str) and max_depth.strip().lower() == "none":
            max_depth = None
        else:
            max_depth = int(max_depth) if max_depth is not None else None

        if self.model_type == "gradient_boosting":
            return GradientBoostingClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth or 3,
                min_samples_split=min_samples_split,
                random_state=42,
            )
        return RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            random_state=42,
            class_weight='balanced',
        )

    # ── Feature Engineering ───────────────────────────────────

    def create_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Build feature matrix from OHLCV data using FeatureEngineer."""
        from src.ml.features import FeatureEngineer
        fe = FeatureEngineer(config=self.config)
        return fe.compute_features(data)

    def create_target(self, data: pd.DataFrame, horizon: int) -> pd.Series:
        """Create classification target: 1=up, -1=down, 0=flat.

        Uses ATR-adaptive threshold so the label balance stays reasonable
        across different timeframes and volatility regimes.
        """
        from src.analysis.indicators import calculate_atr

        future_returns = data["close"].shift(-horizon) / data["close"] - 1

        # ── ATR-adaptive threshold ────────────────────────────
        atr = calculate_atr(data["high"], data["low"], data["close"], period=14)
        atr_pct = atr / data["close"]
        atr_multiplier = self.config.get("ml", "atr_multiplier")
        adaptive_threshold = float(atr_pct.mean() * atr_multiplier)

        min_threshold = self.config.get("ml", "classification_threshold")
        threshold = max(adaptive_threshold, min_threshold)

        target = pd.Series(0, index=data.index)
        target[future_returns > threshold] = 1
        target[future_returns < -threshold] = -1
        # Set the last 'horizon' rows to NaN because their future returns are unknown
        if horizon > 0:
            target.iloc[-horizon:] = np.nan
        return target

    # ── Training ──────────────────────────────────────────────

    def train(self, data: pd.DataFrame, horizon: int = 1,
              save_path: Optional[str] = None) -> float:
        """Train the model on historical data.

        Returns test accuracy. Also logs training stats to DB
        (ml_training_log table) for historical tracking.
        """
        features = self.create_features(data)
        target = self.create_target(data, horizon)
        
        # Drop rows where target is NaN
        target = target.dropna()
        
        common = features.index.intersection(target.index)
        X = features.loc[common].values
        y = target.loc[common].values

        if len(X) < 50:
            raise MLTrainingError(f"Not enough samples ({len(X)}), need at least 50")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )
        
        # Thread-safe scaling & model fitting: use temporary instances
        from sklearn.preprocessing import StandardScaler
        temp_scaler = StandardScaler()
        X_train_scaled = temp_scaler.fit_transform(X_train)
        X_test_scaled = temp_scaler.transform(X_test)
        
        model_to_fit = self._init_model()
        model_to_fit.fit(X_train_scaled, y_train)
        preds = model_to_fit.predict(X_test_scaled)
        accuracy = float(accuracy_score(y_test, preds))
        
        # Calculate class distribution stats on target values
        unique, counts = np.unique(y, return_counts=True)
        self.last_train_stats = {
            "accuracy": accuracy,
            "class_distribution": {
                int(k): int(v) for k, v in zip(unique, counts)
            },
            "class_percentages": {
                int(k): float(v/len(y)) for k, v in zip(unique, counts)
            }
        }
        
        # Atomic update of model attributes to prevent multi-threaded AttributeError/ValueError
        self.scaler = temp_scaler
        self.model = model_to_fit
        self.is_trained = True
        logger.info(f"ML model trained: accuracy={accuracy:.2%}")

        # ── Persist training log to DB ───────────────────────────
        try:
            from src.repositories.analytics_repo import AnalyticsRepository
            from src.persistence.database import get_db
            repo = AnalyticsRepository(get_db())

            # Build feature importance list if model supports it
            feature_importance = []
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
                feature_names = features.columns.tolist()
                ranking = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
                feature_importance = [
                    {"name": name, "importance": round(float(imp), 4)}
                    for name, imp in ranking[:20]  # top 20 features
                ]

            # Determine data range
            data_range_start = None
            data_range_end = None
            if hasattr(data, 'index') and hasattr(data.index, 'min'):
                try:
                    data_range_start = data.index.min()
                    data_range_end = data.index.max()
                except Exception:
                    pass

            # Build params used dict
            params_used = {}
            for p in ['n_estimators', 'max_depth', 'min_samples_split',
                       'classification_threshold', 'atr_multiplier']:
                try:
                    params_used[p] = self.config.get('ml', p)
                except Exception:
                    pass
            params_used['model_type'] = self.model_type

            log_data = {
                'model_type': self.model_type,
                'accuracy': round(accuracy, 4),
                'params_used': params_used,
                'class_distribution': self.last_train_stats['class_distribution'],
                'feature_importance': feature_importance,
                'n_samples': len(y),
                'data_range_start': data_range_start,
                'data_range_end': data_range_end,
                'atr_multiplier': self.config.get('ml', 'atr_multiplier'),
                'threshold': self.config.get('ml', 'classification_threshold'),
                'data_source': 'mt5',
                'symbol': self.config.get('general', 'symbol'),
                'timeframe': self.config.get('general', 'timeframe'),
            }
            repo.save_ml_training_log(log_data)

            # ── Push real-time event to WebSocket shared state ──
            try:
                from src.rpc.websocket import set_shared
                set_shared("ml_training_event", {
                    "timestamp": time.time(),
                    "accuracy": accuracy,
                    "model_type": self.model_type,
                    "n_samples": len(y),
                })
            except Exception as e:
                logger.warning(f"Failed to push WS training event: {e}")
        except Exception as e:
            logger.warning(f"Failed to save ML training log: {e}")

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
        timeframe = self.config.get("general", "timeframe")
        joblib.dump({
            "model": self.model,
            "scaler": self.scaler,
            "timeframe": timeframe
        }, filepath)
        logger.info(f"ML model saved to {filepath} with timeframe {timeframe}")

    def load(self, filepath: str) -> bool:
        """Load model from disk. Returns True on success."""
        try:
            loaded = joblib.load(filepath)
            
            # Validate timeframe if stored in model file
            timeframe_in_file = loaded.get("timeframe")
            current_timeframe = self.config.get("general", "timeframe")
            if timeframe_in_file and timeframe_in_file != current_timeframe:
                logger.warning(
                    f"ML model timeframe mismatch: file has {timeframe_in_file}, "
                    f"but config has {current_timeframe}. Forcing retrain."
                )
                return False

            scaler = loaded["scaler"]

            # Validate feature count to avoid StandardScaler shape mismatch errors
            from src.ml.features import FeatureEngineer
            fe = FeatureEngineer(config=self.config)
            expected_features = len(fe.get_feature_names())

            if hasattr(scaler, "n_features_in_") and scaler.n_features_in_ != expected_features:
                logger.warning(f"ML model feature count mismatch: scaler expects {scaler.n_features_in_} features, "
                               f"but current FeatureEngineer creates {expected_features}. Forcing retrain.")
                return False

            self.model = loaded["model"]
            self.scaler = scaler
            self.is_trained = True
            logger.info(f"ML model loaded from {filepath} (timeframe={timeframe_in_file or 'legacy'})")
            return True
        except Exception as e:
            logger.warning(f"Failed to load ML model from {filepath}: {e}")
            return False
