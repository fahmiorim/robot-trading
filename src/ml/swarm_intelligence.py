import os

import time
import numpy as np
import pandas as pd
from typing import Dict, List, Optional

from src.configuration.manager import ConfigManager
from src.ml.model import MLModel
from src.strategy.implementations import (
    MACrossoverStrategy, RSIStrategy, MACDStrategy,
    BollingerStrategy, BreakoutStrategy,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SwarmIntelligence:
    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config or ConfigManager()
        self.models = {
            'random_forest': MLModel('random_forest', config=self.config),
            'gb_classifier': MLModel('gradient_boosting', config=self.config)
        }
        
        # Try to load existing models from disk (only if not already trained)
        os.makedirs("trained_models", exist_ok=True)
        for name, model in self.models.items():
            if not model.is_trained:
                model.load(f"trained_models/swarm_{name}.pkl")
        
        ma_cfg = self.config.get("strategies", "MA_Crossover")
        ma_fast = ma_cfg.get("fast_period", 10)
        ma_slow = ma_cfg.get("slow_period", 25)
        rsi_cfg = self.config.get("strategies", "RSI")
        rsi_period = rsi_cfg.get("period", 9)
        rsi_overbought = rsi_cfg.get("overbought", 80)
        rsi_oversold = rsi_cfg.get("oversold", 20)
        macd_cfg = self.config.get("strategies", "MACD")
        macd_fast = macd_cfg.get("fast", 12)
        macd_slow = macd_cfg.get("slow", 26)
        macd_signal = macd_cfg.get("signal", 9)
        self.strategies = {
            'ma': MACrossoverStrategy(fast_period=ma_fast, slow_period=ma_slow),
            'rsi': RSIStrategy(period=rsi_period, overbought=rsi_overbought, oversold=rsi_oversold),
            'macd': MACDStrategy(fast=macd_fast, slow=macd_slow, signal=macd_signal),
        }
        self.weights = {k: 1.0 for k in self.models}
        self.weights.update({k: 1.0 for k in self.strategies})
        
        # Track last train times
        self._last_train_times = {}
        for name in self.models:
            save_path = f"trained_models/swarm_{name}.pkl"
            if os.path.exists(save_path):
                self._last_train_times[name] = os.path.getmtime(save_path)
            else:
                self._last_train_times[name] = 0

    def train_all(self, data: pd.DataFrame, force: bool = False):
        try:
            retrain_interval_hours = self.config.get("ml", "retrain_interval_hours")
        except Exception:
            retrain_interval_hours = 24
        retrain_interval = retrain_interval_hours * 3600  # seconds

        for name, model in self.models.items():
            save_path = f"trained_models/swarm_{name}.pkl"
            last_train = self._last_train_times.get(name, 0)
            
            should_train = force or not model.is_trained or (time.time() - last_train >= retrain_interval)
            if should_train:
                try:
                    logger.info(f"Swarm model {name} training...")
                    model.train(data, save_path=save_path)
                    self._last_train_times[name] = time.time()
                except Exception as e:
                    logger.warning(f"Swarm model {name} training failed: {e}")

    def get_predictions(self, data: pd.DataFrame) -> Dict[str, int]:
        predictions = {}
        for name, model in self.models.items():
            if model.is_trained:
                try:
                    pred = int(model.predict(data).item())
                    predictions[f"ml_{name}"] = pred
                except Exception:
                    pass
        
        # Recreate strategies dynamically in case periods changed in the DB config
        try:
            ma_cfg = self.config.get("strategies", "MA_Crossover")
            ma_fast = ma_cfg.get("fast_period", 10)
            ma_slow = ma_cfg.get("slow_period", 25)
            rsi_cfg = self.config.get("strategies", "RSI")
            rsi_period = rsi_cfg.get("period", 9)
            rsi_overbought = rsi_cfg.get("overbought", 80)
            rsi_oversold = rsi_cfg.get("oversold", 20)
            macd_cfg = self.config.get("strategies", "MACD")
            macd_fast = macd_cfg.get("fast", 12)
            macd_slow = macd_cfg.get("slow", 26)
            macd_signal = macd_cfg.get("signal", 9)
            
            self.strategies = {
                'ma': MACrossoverStrategy(fast_period=ma_fast, slow_period=ma_slow),
                'rsi': RSIStrategy(period=rsi_period, overbought=rsi_overbought, oversold=rsi_oversold),
                'macd': MACDStrategy(fast=macd_fast, slow=macd_slow, signal=macd_signal),
            }
        except Exception as e:
            logger.warning(f"Failed to refresh Swarm strategies from config: {e}")

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
        buy_threshold = self.config.get("signals", "consensus_buy_threshold")
        sell_threshold = self.config.get("signals", "consensus_sell_threshold")
        if avg > buy_threshold:
            return 1
        elif avg < sell_threshold:
            return -1
        return 0

    def update_weights(self, performance: Dict[str, float]):
        learning_rate = self.config.get("ml", "swarm_learning_rate")
        for name, score in performance.items():
            if name in self.weights:
                self.weights[name] *= (1 + score * learning_rate)


_swarm_instance: Optional[SwarmIntelligence] = None


def get_swarm_signal(data: pd.DataFrame, config: Optional[ConfigManager] = None) -> int:
    """Helper function to run swarm intelligence voting and return signal."""
    global _swarm_instance
    if _swarm_instance is None:
        _swarm_instance = SwarmIntelligence(config=config)
    elif config is not None:
        _swarm_instance.config = config
        for model in _swarm_instance.models.values():
            model.config = config
    _swarm_instance.train_all(data)
    return _swarm_instance.vote_signal(data)

