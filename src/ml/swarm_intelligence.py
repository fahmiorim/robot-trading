import os

import time
import numpy as np
import pandas as pd
from typing import Any, Dict, Optional

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
        
        # Determine symbol for per-symbol model isolation
        try:
            self._swarm_symbol = self.config.get("general", "symbol")
            self._swarm_timeframe = self.config.get("general", "timeframe")
        except Exception:
            self._swarm_symbol = "XAUUSD"
            self._swarm_timeframe = "TIMEFRAME_M15"

        # Try to load existing models from disk (only if not already trained)
        os.makedirs("trained_models", exist_ok=True)
        for name, model in self.models.items():
            if not model.is_trained:
                model.load(f"trained_models/{self._swarm_symbol}/swarm_{name}.pkl")
        
        self.strategies = self._build_strategies_from_config()
        self.weights = {k: 1.0 for k in self.models}
        self.weights.update({k: 1.0 for k in self.strategies})
        
        # Track last train times
        self._last_train_times = {}
        for name in self.models:
            save_path = f"trained_models/{self._swarm_symbol}/swarm_{name}.pkl"
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
            save_path = f"trained_models/{self._swarm_symbol}/swarm_{name}.pkl"
            last_train = self._last_train_times.get(name, 0)
            
            should_train = force or not model.is_trained or (time.time() - last_train >= retrain_interval)
            if should_train:
                try:
                    logger.info(f"Swarm model {name} training...")
                    model.train(data, save_path=save_path)
                    self._last_train_times[name] = time.time()
                except Exception as e:
                    logger.warning(f"Swarm model {name} training failed: {e}")

    def _build_strategies_from_config(self) -> Dict[str, Any]:
        """Build strategy instances from DB config, respecting enabled flags.

        Membaca semua 5 strategi dari database dan hanya mengaktifkan
        yang memiliki enabled=True. Termasuk Bollinger & Breakout.
        """
        strategies = {}

        strategy_configs = [
            ("MA_Crossover", "ma", lambda cfg: MACrossoverStrategy(
                fast_period=cfg.get("fast_period", 10),
                slow_period=cfg.get("slow_period", 25),
            )),
            ("RSI", "rsi", lambda cfg: RSIStrategy(
                period=cfg.get("period", 14),
                overbought=cfg.get("overbought", 70),
                oversold=cfg.get("oversold", 30),
            )),
            ("MACD", "macd", lambda cfg: MACDStrategy(
                fast=cfg.get("fast", 12),
                slow=cfg.get("slow", 26),
                signal=cfg.get("signal", 9),
            )),
            ("Bollinger", "bollinger", lambda cfg: BollingerStrategy(
                period=cfg.get("period", 20),
                std_dev=cfg.get("std_dev", 2.0),
            )),
            ("Breakout", "breakout", lambda cfg: BreakoutStrategy(
                lookback=cfg.get("lookback", 20),
            )),
        ]

        for db_name, short_name, factory in strategy_configs:
            try:
                cfg = self.config.get("strategies", db_name)
                if not isinstance(cfg, dict):
                    cfg = {}
                enabled = cfg.get("enabled", True)
                if not enabled:
                    logger.debug(f"Swarm skipping disabled strategy: {db_name}")
                    continue
                strategies[short_name] = factory(cfg)
            except Exception as e:
                logger.warning(f"Swarm failed to load strategy {db_name}: {e}")

        return strategies

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
            self.strategies = self._build_strategies_from_config()
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
        # Majority voting: hitung berapa sumber setuju BUY / SELL
        buy_votes = sum(1 for p in predictions.values() if p == 1)
        sell_votes = sum(1 for p in predictions.values() if p == -1)
        total = len(predictions)
        if total == 0:
            return 0
        buy_ratio = buy_votes / total
        sell_ratio = sell_votes / total
        buy_threshold = self.config.get("signals", "consensus_buy_threshold")
        sell_threshold = self.config.get("signals", "consensus_sell_threshold")
        if buy_ratio >= buy_threshold:
            return 1
        elif sell_ratio >= abs(sell_threshold):
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

