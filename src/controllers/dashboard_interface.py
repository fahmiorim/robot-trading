"""Abstract interface for the dashboard controller — thin controller pattern.

Defines the contract between the Streamlit dashboard pages and the
backend.  All dashboard pages should depend on this interface so they
are decoupled from the concrete implementation.

Usage:
    from src.controllers.dashboard_interface import IDashboardController

    ctrl: IDashboardController = st.session_state.get("dashboard_ctrl")
    trades = ctrl.get_trade_history(limit=10)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.models.backtest import HyperoptResult
from src.models.config import BotConfig


class IDashboardController(ABC):
    """Interface for the dashboard controller.

    All methods that the Streamlit dashboard pages call are declared here.
    Concrete implementations (e.g. ``DashboardController``) inherit from
    this interface.
    """

    # ── Bot Status ───────────────────────────────────────────

    @abstractmethod
    def get_status(self, bot=None) -> Dict:
        """Get combined status from bot and config."""
        ...

    # ── Trade History ────────────────────────────────────────

    @abstractmethod
    def get_trade_history(self, limit: int = 500) -> List[Dict]:
        """Get recent trade history."""
        ...

    @abstractmethod
    def get_open_trades(self) -> List[Dict]:
        """Get currently open trades."""
        ...

    @abstractmethod
    def get_trade_summary(self, days: int = 7) -> Dict:
        """Get trade summary statistics."""
        ...

    # ── Equity & Performance ─────────────────────────────────

    @abstractmethod
    def get_equity_curve(self, days: int = 30) -> List[Dict]:
        """Get equity curve data points."""
        ...

    @abstractmethod
    def get_best_hyperopt_params(self, strategy_name: str) -> Optional[HyperoptResult]:
        """Get best hyperopt parameters for a strategy."""
        ...

    @abstractmethod
    def get_all_hyperopt_results(self) -> List[HyperoptResult]:
        """Get all hyperopt results from the database."""
        ...

    @abstractmethod
    def get_ml_training_log(self, limit: int = 20) -> List[Dict]:
        """Get recent ML training logs."""
        ...

    @abstractmethod
    def check_concept_drift(self, threshold_pct: float = 5.0) -> Dict:
        """Check if ML model accuracy has drifted significantly."""
        ...

    # ── Settings ─────────────────────────────────────────────

    @abstractmethod
    def get_all_settings(self) -> BotConfig:
        """Get all settings as a BotConfig object."""
        ...

    @abstractmethod
    def set_setting(self, section: str, key: str, value: Any) -> bool:
        """Set a single configuration value."""
        ...
