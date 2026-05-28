import numpy as np
import pandas as pd
from typing import Dict, List

from src.ml.model import MLModel
from src.strategy.implementations import (
    MACrossoverStrategy, RSIStrategy, MACDStrategy,
    BollingerStrategy, BreakoutStrategy,
)


class SwarmIntelligence:
    def __init__(self):
        self.models = {
            'random_forest': MLModel('random_forest'),
            'gb_classifier': MLModel('gradient_boosting')
        }
        self.strategies = {
            'ma': MACrossoverStrategy(fast_period=10, slow_period=21),
            'rsi': RSIStrategy(period=14),
            'macd': MACDStrategy()
        }
        self.weights = {k: 1.0 for k in self.models}
        self.weights.update({k: 1.0 for k in self.strategies})

    def train_all(self, data: pd.DataFrame):
        for name, model in self.models.items():
            try:
                model.train(data)
            except Exception:
                pass

    def get_predictions(self, data: pd.DataFrame) -> Dict[str, int]:
        predictions = {}
        for name, model in self.models.items():
            if model.is_trained:
                try:
                    pred = int(model.predict(data).item())
                    predictions[f"ml_{name}"] = pred
                except Exception:
                    pass
        for name, strategy in self.strategies.items():
            try:
                signals = strategy.calculate_signals(data)
                predictions[f"strategy_{name}"] = int(signals.iloc[-1])
            except Exception:
                pass
        return predictions

    def vote_signal(self, data: pd.DataFrame) -> int:
        predictions = self.get_predictions(data)
        if not predictions:
            return 0
        weighted_sum = sum(p * self.weights.get(k, 1.0) for k, p in predictions.items())
        avg = weighted_sum / len(predictions)
        if avg > 0.3:
            return 1
        elif avg < -0.3:
            return -1
        return 0

    def update_weights(self, performance: Dict[str, float]):
        for name, score in performance.items():
            if name in self.weights:
                self.weights[name] *= (1 + score * 0.05)


def get_swarm_signal(data: pd.DataFrame) -> int:
    """Helper function to run swarm intelligence voting and return signal."""
    swarm = SwarmIntelligence()
    swarm.train_all(data)
    return swarm.vote_signal(data)
