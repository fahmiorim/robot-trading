"""
ML training pipeline — orchestrates model training, evaluation,
and periodic retraining with sliding windows (inspired by FreqAI).
"""
from __future__ import annotations
import time
from typing import Dict, Optional, Callable, TYPE_CHECKING

import pandas as pd

from src.ml.model import MLModel
from src.ml.features import FeatureEngineer
from src.utils.exceptions import MLTrainingError
from src.utils.logging import get_logger

if TYPE_CHECKING:
    from src.configuration.manager import ConfigManager

logger = get_logger(__name__)

class Trainer:
    """Orchestrates ML model lifecycle: train, retrain, evaluate.

    Supports:
    - Auto-loading saved model on init
    - Sliding-window retrain based on interval
    - Accuracy tracking across retrain cycles
    - Concept drift detection (auto-retrain on accuracy drop > 5%)
    - Event hooks for dashboard notifications
    """

    def __init__(self, model_type: str,
                 retrain_interval_hours: int,
                 model_path: str,
                 config: Optional['ConfigManager'] = None):
        self.model = MLModel(model_type=model_type, config=config)
        self.feature_engineer = FeatureEngineer(config=config)
        self.model_path = model_path
        self.retrain_interval = retrain_interval_hours * 3600  # seconds
        self._last_train_time: float = 0
        self._last_accuracy: Optional[float] = None
        self._event_hooks: Dict[str, Callable] = {}
        self._concept_drifted: bool = False

        # Auto-load saved model
        try:
            loaded = self.model.load(self.model_path)
            if loaded:
                import os
                if os.path.exists(self.model_path):
                    self._last_train_time = os.path.getmtime(self.model_path)
                else:
                    self._last_train_time = time.time()
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
        """Train (or retrain) the ML model on the given data.

        After training, checks for concept drift by comparing latest accuracy
        against the average of the previous 3 training runs. If accuracy
        dropped >5%, sets ``concept_drifted`` flag so the trading cycle can
        trigger an immediate retrain with fresh data.
        """
        logger.info("Training ML model...")
        try:
            accuracy = self.model.train(data, save_path=self.model_path if save else None)
            self._last_train_time = time.time()
            self._last_accuracy = accuracy
            self._concept_drifted = False
            logger.info(f"ML training complete: accuracy={accuracy:.2%}")

            # ── Concept drift check after training ────────────
            try:
                from src.repositories.analytics_repo import AnalyticsRepository
                from src.persistence.database import get_db
                repo = AnalyticsRepository(get_db())
                drift = repo.check_concept_drift(threshold_pct=5.0)
                if drift.get("drifted"):
                    self._concept_drifted = True
                    logger.warning(
                        f"⚠️ Concept drift detected: latest accuracy {drift['latest_acc']:.2%} "
                        f"dropped {drift['drop_pct']:.1f}% vs avg of last 3 ({drift['avg_prev_3']:.2%}). "
                        "Auto-retrain will be triggered on next cycle."
                    )
                    if "drift" in self._event_hooks:
                        self._event_hooks["drift"](drift)
            except Exception as e:
                logger.warning(f"Concept drift check failed: {e}")

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
    def last_train_stats(self) -> Optional[dict]:
        return self.model.last_train_stats if hasattr(self.model, 'last_train_stats') else None

    @property
    def hours_since_train(self) -> float:
        if self._last_train_time == 0:
            raise RuntimeError("Model has never been trained")
        return (time.time() - self._last_train_time) / 3600

    @property
    def concept_drifted(self) -> bool:
        """True if latest training accuracy dropped >5% vs previous 3 runs.
        Reset after each successful train."""
        return self._concept_drifted
