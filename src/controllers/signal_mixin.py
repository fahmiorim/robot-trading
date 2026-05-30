"""Signal mixin — signal generation methods extracted from TradingController."""

from typing import Any, Dict, Optional

import pandas as pd


class SignalMixin:
    """Mixin providing signal generation methods for TradingController.

    Requires the host class to have:
        self.config, self.signal_service, self.strategies,
        self.strategy_service, self.ml_service
    """

    # ── Signal ──

    def get_signal(self, data: pd.DataFrame,
                   use_ml: bool = False,
                   use_agent: bool = False,
                   use_swarm: bool = False) -> int:
        sig = self.signal_service.get_signal(
            data=data,
            strategies=self.strategies,
            best_strategy=self.strategy_service.best_strategy,
            ml_trainer=self.ml_service.trainer,
            current_regime=self.strategy_service.current_regime,
            use_ml=use_ml,
            use_agent=use_agent,
            use_swarm=use_swarm,
            config=self.config,
        )
        return sig

    def get_individual_signals(self, data: pd.DataFrame) -> Dict[str, int]:
        """Get raw signals from each source individually (no consensus).

        Returns dict: {"strategy": int, "ml": int, "agent": int, "swarm": int}
        Each value: 1=BUY, -1=SELL, 0=HOLD
        """
        return self.signal_service.get_individual_signals(
            data=data,
            strategies=self.strategies,
            best_strategy=self.strategy_service.best_strategy,
            ml_trainer=self.ml_service.trainer,
            config=self.config,
        )

    def detect_regime(self, data: pd.DataFrame) -> str:
        """Detect market regime from price data."""
        return self.strategy_service.detect_regime(data)

    # Keep backward-compat alias
    _detect_regime = detect_regime
