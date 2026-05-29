"""ML service — ML model training and prediction orchestration."""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING

import pandas as pd

from src.ml.trainer import Trainer
from src.utils.logging import get_logger

if TYPE_CHECKING:
    from src.configuration.manager import ConfigManager

logger = get_logger(__name__)


class MLService:
    """Manages ML model lifecycle: training, retraining, and predictions.

    Usage:
        service = MLService(config)
        service.ensure_trained(data)
        accuracy = service.train(data)
        pred = service.predict(data)
    """

    def __init__(self, model_type: str,
                 retrain_interval_hours: int,
                 model_path: Optional[str] = None,
                 config: Optional['ConfigManager'] = None):
        if model_path is None:
            model_path = "trained_models/latest_model.pkl"
        self.trainer = Trainer(
            model_type=model_type,
            retrain_interval_hours=retrain_interval_hours,
            model_path=model_path,
            config=config,
        )

    def ensure_trained(self, data: pd.DataFrame) -> float:
        """Train if not already trained. Returns accuracy."""
        return self.trainer.ensure_trained(data)

    def train(self, data: pd.DataFrame, save: bool = True) -> float:
        """Train the ML model."""
        return self.trainer.train(data, save=save)

    def predict(self, data: pd.DataFrame) -> Optional[float]:
        """Get ML prediction for the latest data point."""
        if self.trainer.is_trained and hasattr(self.trainer, 'predict'):
            try:
                return self.trainer.predict(data)
            except Exception as e:
                logger.warning(f"ML predict failed: {e}")
        return None

    def retrain_if_needed(self, data: pd.DataFrame) -> Optional[float]:
        """Retrain if interval has elapsed."""
        return self.trainer.retrain_if_needed(data)

    @property
    def is_trained(self) -> bool:
        return self.trainer.is_trained

    @property
    def last_train_stats(self) -> Optional[dict]:
        return self.trainer.last_train_stats

    @property
    def last_accuracy(self) -> Optional[float]:
        return self.trainer.last_accuracy
