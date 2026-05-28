"""Reusable Streamlit dashboard components.

Each component is a render function that takes explicit parameters
and reads only from streamlit's session state when necessary.
"""

from dashboard.components.account_info import render_account_info
from dashboard.components.strategy_signals import render_strategy_signals
from dashboard.components.risk_metrics import render_risk_metrics
from dashboard.components.trade_metrics import render_trade_metrics
from dashboard.components.auto_trade_panel import render_auto_trade_controls

__all__ = [
    "render_account_info",
    "render_strategy_signals",
    "render_risk_metrics",
    "render_trade_metrics",
    "render_auto_trade_controls",
]
