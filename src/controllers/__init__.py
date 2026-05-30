"""Thin controllers — bridge between services and views with no business logic.

Usage:
    from src.controllers import TradingController, DashboardController
    from src.controllers.dashboard_interface import IDashboardController
"""

from src.controllers.trading_controller import TradingController
from src.controllers.analysis_controller import AnalysisController
from src.controllers.dashboard_controller import DashboardController
from src.controllers.dashboard_interface import IDashboardController
from src.controllers.execution_mixin import ExecutionMixin
from src.controllers.signal_mixin import SignalMixin

__all__ = [
    "TradingController",
    "AnalysisController",
    "DashboardController",
    "IDashboardController",
    "ExecutionMixin",
    "SignalMixin",
]
