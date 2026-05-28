"""Thin controllers — bridge between services and views with no business logic.

Usage:
    from src.controllers.trading_controller import TradingController
    from src.controllers.analysis_controller import AnalysisController
    from src.controllers.dashboard_controller import DashboardController
"""

from src.controllers.trading_controller import TradingController
from src.controllers.analysis_controller import AnalysisController
from src.controllers.dashboard_controller import DashboardController

__all__ = [
    "TradingController",
    "AnalysisController",
    "DashboardController",
]
