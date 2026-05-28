"""
ML training pipeline — orchestrates model training, evaluation,
and periodic retraining with sliding windows (inspired by FreqAI).
"""
import time
from typing import Dict, Optional, Callable

import pandas as pd

from src.ml.model import MLModel
from src.ml.features import FeatureEngineer
from src.utils.exceptions import MLTrainingError
from src.utils.logging import get_logger

logger = get_logger(__name__)

MODEL_PATH = "trained_models/latest_model.pkl"


class Trainer:
    """Orchestrates ML model lifecycle: train, retrain, evaluate.

    Supports:
    - Auto-loading saved model on init
    - Sliding-window retrain based on interval
    - Accuracy tracking across retrain cycles
    - Event hooks for dashboard notifications
    """

    def __init__(self, model_type: str = "random_forest",
                 retrain_interval_hours: int = 24):
        self.model = MLModel(model_type=model_type or "random_forest")
        self.feature_engineer = FeatureEngineer()
        interval = retrain_interval_hours or 24
        self.retrain_interval = interval * 3600  # seconds
        self._last_train_time: float = 0
        self._last_accuracy: Optional[float] = None
        self._event_hooks: Dict[str, Callable] = {}

        # Auto-load saved model
        try:
            loaded = self.model.load(MODEL_PATH)
            if loaded:
                logger.info("Loaded pre-trained ML model from disk")
        except Exception:
            logger.info("No pre-trained ML model found, will train on first cycle")

    def on(self, event: str, callback: Callable) -> None:
        """Register a callback for 'trained' or 'failed' events."""
        self._event_hooks[event] = callback

    def ensure_trained(self, data: pd.DataFrame) -> float:
        """Train model if not already trained. Returns accuracy."""
        if self.model.is_trained:
            return self._last_accuracy or 0.0
        return self.train(data)

    def train(self, data: pd.DataFrame, save: bool = True) -> float:
        """Train (or retrain) the ML model on the given data."""
        logger.info("Training ML model...")
        try:
            accuracy = self.model.train(data, save_path=MODEL_PATH if save else None)
            self._last_train_time = time.time()
            self._last_accuracy = accuracy
            logger.info(f"ML training complete: accuracy={accuracy:.2%}")

            if "trained" in self._event_hooks:
                self._event_hooks["trained"](accuracy)
            return accuracy
        except MLTrainingError as e:
            logger.warning(f"ML training skipped: {e}")
            if "failed" in self._event_hooks:
                self._event_hooks["failed"](str(e))
            return 0.0
        except Exception as e:
            logger.error(f"ML training failed: {e}")
            if "failed" in self._event_hooks:
                self._event_hooks["failed"](str(e))
            return 0.0

    def should_retrain(self) -> bool:
        """Check if retrain interval has elapsed."""
        if not self.model.is_trained:
            return True
        elapsed = time.time() - self._last_train_time
        return elapsed >= self.retrain_interval

    def retrain_if_needed(self, data: pd.DataFrame) -> Optional[float]:
        """Retrain only if the interval has passed. Returns accuracy or None."""
        if self.should_retrain():
            logger.info("Retrain interval elapsed, retraining ML model...")
            return self.train(data)
        return None

    def predict(self, data: pd.DataFrame) -> int:
        """Predict trading signal using the underlying model."""
        pred = self.model.predict(data)
        return int(pred.item()) if hasattr(pred, "item") else int(pred[0])

    @property
    def is_trained(self) -> bool:
        return self.model.is_trained

    @property
    def last_accuracy(self) -> Optional[float]:
        return self._last_accuracy

    @property
    def hours_since_train(self) -> float:
        if self._last_train_time == 0:
            return 999
        return (time.time() - self._last_train_time) / 3600
