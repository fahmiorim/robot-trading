"""Signal service — aggregates signals from strategy, ML, agent, and swarm sources."""

from typing import Any, Dict, List, Optional

import pandas as pd

from src.models.signal import SignalResult, AggregatedSignal
from src.constants.trading import SignalType, SIGNAL_LABELS
from src.utils.logging import get_logger
from src.ml.agent_pipeline import get_agent_signal
from src.ml.swarm_intelligence import get_swarm_signal

logger = get_logger(__name__)


class SignalService:
    """Aggregates trading signals from multiple sources.

    Combines signals from strategies, ML model, AI agent, and swarm intelligence
    into a single consensus signal with voting logic.
    """

    def __init__(self):
        self._last_signals: Dict[str, int] = {}

    def get_signal(self, data: pd.DataFrame, strategies: Dict,
                   best_strategy: Any = None,
                   ml_trainer: Any = None,
                   current_regime: str = "unknown",
                   use_ml: bool = False,
                   use_agent: bool = False,
                   use_swarm: bool = False,
                   config: Optional[Any] = None) -> int:
        """Compute aggregated signal from all enabled sources.

        Returns:
            int: 1 = BUY, -1 = SELL, 0 = HOLD
        """
        votes: Dict[str, int] = {}

        # 1. Strategy signal
        strategy_sig = self._strategy_signal(data, strategies, best_strategy)
        votes["strategy"] = strategy_sig
        self._last_signals["strategy"] = strategy_sig

        # 2. ML signal
        if use_ml and ml_trainer is not None:
            ml_sig = self._ml_signal(data, ml_trainer)
            votes["ml"] = ml_sig
            self._last_signals["ml"] = ml_sig

        # 3. Agent signal
        if use_agent:
            agent_sig = self._agent_signal(data, config)
            votes["agent"] = agent_sig
            self._last_signals["agent"] = agent_sig

        # 4. Swarm signal
        if use_swarm:
            swarm_sig = self._swarm_signal(data, config)
            votes["swarm"] = swarm_sig
            self._last_signals["swarm"] = swarm_sig

        # Consensus voting
        buy_votes = sum(1 for v in votes.values() if v == 1)
        sell_votes = sum(1 for v in votes.values() if v == -1)
        total = len(votes)

        if total == 0:
            return SignalType.HOLD

        buy_ratio = buy_votes / total
        sell_ratio = sell_votes / total

        # Use thresholds from config if provided, else default to majority
        buy_threshold = 0.5
        sell_threshold = 0.5
        if config:
            buy_threshold = config.get("signals", "consensus_buy_threshold")
            sell_threshold = abs(config.get("signals", "consensus_sell_threshold"))

        if buy_ratio >= buy_threshold:
            return SignalType.BUY
        elif sell_ratio >= sell_threshold:
            return SignalType.SELL
        return SignalType.HOLD

    def get_last_signals(self) -> Dict[str, int]:
        return dict(self._last_signals)

    # ── Individual Signal Sources ──

    def _strategy_signal(self, data: pd.DataFrame, strategies: Dict,
                         best_strategy: Any = None) -> int:
        """Get signal from the best-performing strategy."""
        if best_strategy is not None and hasattr(best_strategy, 'calculate_signals'):
            try:
                sig_series = best_strategy.calculate_signals(data)
                if sig_series is not None and len(sig_series) > 0:
                    return int(sig_series.iloc[-1])
            except Exception as e:
                logger.warning(f"Strategy signal failed: {e}")

        # Fallback: aggregate across all strategies
        sigs = []
        for name, strategy in strategies.items():
            try:
                sig_series = strategy.calculate_signals(data)
                if sig_series is not None and len(sig_series) > 0:
                    sigs.append(int(sig_series.iloc[-1]))
            except Exception:
                pass

        if not sigs:
            return SignalType.HOLD
        return SignalType.BUY if sum(sigs) > 0 else SignalType.SELL if sum(sigs) < 0 else SignalType.HOLD

    def _ml_signal(self, data: pd.DataFrame, ml_trainer: Any) -> int:
        """Get signal from ML model prediction.

        ml_trainer.predict() returns int: 1=BUY, -1=SELL, 0=HOLD
        """
        try:
            if hasattr(ml_trainer, 'predict') and ml_trainer.is_trained:
                label = ml_trainer.predict(data)  # returns int
                if label == 1:
                    return SignalType.BUY
                elif label == -1:
                    return SignalType.SELL
                return SignalType.HOLD
        except Exception as e:
            logger.warning(f"ML signal failed: {e}")
        return SignalType.HOLD

    def _agent_signal(self, data: pd.DataFrame, config: Optional[Any] = None) -> int:
        """Get signal from AI agent (placeholder)."""
        try:
            return get_agent_signal(data, config=config)
        except Exception as e:
            logger.warning(f"Agent signal failed: {e}")
        return SignalType.HOLD

    def _swarm_signal(self, data: pd.DataFrame, config: Optional[Any] = None) -> int:
        """Get signal from swarm intelligence (placeholder)."""
        try:
            return get_swarm_signal(data, config=config)
        except Exception as e:
            logger.warning(f"Swarm signal failed: {e}")
        return SignalType.HOLD
