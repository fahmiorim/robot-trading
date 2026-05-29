"""Signal aggregation — orchestrates strategy, ML, agent, and swarm signals."""

from typing import Any, Dict, List, Optional

import pandas as pd

from src.utils.logging import get_logger

logger = get_logger(__name__)


class SignalAggregator:
    """Aggregates trading signals from multiple sources (strategies, ML, agent, swarm)."""

    def __init__(self):
        self._last_signals: Dict[str, int] = {}

    def get_signal(
        self,
        data: pd.DataFrame,
        strategies: Dict[str, Any],
        best_strategy: Optional[Any] = None,
        ml_trainer: Optional[Any] = None,
        current_regime: str = "unknown",
        use_ml: bool = False,
        use_agent: bool = False,
        use_swarm: bool = False,
    ) -> int:
        """Get consensus signal from the best available source."""
        try:
            if use_swarm:
                sig = self._swarm_signal(data, strategies, ml_trainer)
                self._last_signals["swarm"] = sig
                return sig
            if use_agent and current_regime != "unknown":
                sig = self._agent_signal(data, current_regime)
                self._last_signals["agent"] = sig
                return sig
            if use_ml and ml_trainer is not None and ml_trainer.is_trained:
                sig = self._ml_signal(data, ml_trainer)
                self._last_signals["ml"] = sig
                return sig
            if best_strategy is not None:
                sig = int(best_strategy.calculate_signals(data).iloc[-1])
                self._last_signals["best_strategy"] = sig
                return sig
            if strategies:
                sig = int(list(strategies.values())[0].calculate_signals(data).iloc[-1])
                self._last_signals["fallback"] = sig
                return sig
            return 0
        except Exception as e:
            logger.error(f"Signal error: {e}")
            return 0

    def _swarm_signal(
        self, data: pd.DataFrame, strategies: Dict[str, Any], ml_trainer: Optional[Any]
    ) -> int:
        """Swarm intelligence — votes from ML model + all strategies."""
        try:
            from src.ml.model import MLModel
            from src.configuration.manager import ConfigManager
            import os

            if not hasattr(self, "_swarm_model"):
                self._swarm_model = MLModel(config=ConfigManager())

            model = self._swarm_model
            # Dynamically resolve model path from config
            try:
                sym = model.config.get("general", "symbol")
                tf = model.config.get("general", "timeframe")
            except Exception:
                sym, tf = "XAUUSD", "TIMEFRAME_M15"
            model_path = MLModel.get_default_model_path(sym, tf)
            
            # Reload from disk if the file has changed
            if os.path.exists(model_path):
                mtime = os.path.getmtime(model_path)
                if not hasattr(self, "_swarm_model_mtime") or self._swarm_model_mtime != mtime:
                    model.load(model_path)
                    self._swarm_model_mtime = mtime

            ml_sig = 0
            if model.is_trained:
                pred = model.predict(data)
                ml_sig = int(pred.item()) if hasattr(pred, "item") else int(pred[0])

            strategy_votes = []
            for s in strategies.values():
                try:
                    sig = int(s.calculate_signals(data).iloc[-1])
                    strategy_votes.append(sig)
                except Exception:
                    pass

            all_votes = [ml_sig] + strategy_votes
            avg = sum(all_votes) / len(all_votes) if all_votes else 0
            return 1 if avg > 0.3 else (-1 if avg < -0.3 else 0)
        except Exception as e:
            logger.error(f"Swarm signal error: {e}")
            return 0

    def _agent_signal(self, data: pd.DataFrame, current_regime: str) -> int:
        """Agent-based signal via AgentPipeline."""
        try:
            from src.ml.agent_pipeline import AgentPipeline

            agent = AgentPipeline()
            result = agent.run_pipeline(data, current_regime)
            return result.get("decision", 0)
        except Exception as e:
            logger.error(f"Agent signal error: {e}")
            return 0

    def _ml_signal(self, data: pd.DataFrame, ml_trainer: Any) -> int:
        """ML model prediction signal."""
        try:
            pred = ml_trainer.model.predict(data)
            return int(pred.item()) if hasattr(pred, "item") else int(pred[0])
        except Exception as e:
            logger.error(f"ML signal error: {e}")
            return 0

    def get_last_signals(self) -> Dict[str, int]:
        """Return the last signals from each source."""
        return dict(self._last_signals)
