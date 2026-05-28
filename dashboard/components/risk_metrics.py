"""Reusable component: Risk metrics grid."""

from typing import Any, Dict

import streamlit as st


def render_risk_metrics(
    risk_summary: Dict[str, Any],
    config,
    *,
    extended: bool = False,
    robot=None,
):
    """Render a 6-column risk metrics grid.

    Parameters
    ----------
    risk_summary : dict
        Output of RiskManager.get_status_summary().
    config : ConfigManager
    extended : bool
        If True, also render Consecutive Losses, Window Loss, Mode, and
        error warnings below the main grid.
    robot : TradingController, optional
        Needed for extended mode (consecutive_errors, paper_trading).
    """
    can_trade = risk_summary.get("can_trade", True)
    if isinstance(can_trade, tuple):
        can_trade = can_trade[0]
    reason = risk_summary.get("can_trade_reason", "")
    cb_active = risk_summary.get("circuit_breaker_active", False)
    cb_reason = risk_summary.get("circuit_breaker_reason", "")

    r1, r2, r3, r4, r5, r6 = st.columns(6)
    with r1:
        dd = risk_summary.get("drawdown_pct", 0)
        max_dd = config.get("risk_management", "max_drawdown_pct")
        st.metric("Drawdown", f"{dd:.2f}%", delta=f"Limit: {max_dd:.0f}%", delta_color="inverse")
    with r2:
        dl = risk_summary.get("daily_loss_pct", 0)
        max_dl = config.get("risk_management", "max_daily_loss_pct")
        st.metric("Daily Loss", f"{dl:.2f}%", delta=f"Limit: {max_dl:.0f}%", delta_color="inverse")
    with r3:
        st.metric("Daily Trades", f"{risk_summary.get('daily_trades', 0)}")
    with r4:
        st.metric("Open Positions", f"{risk_summary.get('open_positions', 0)}")
    with r5:
        st.metric("Can Trade", "✅" if can_trade else "❌", help=reason if not can_trade else "")
    with r6:
        if cb_active:
            st.metric("Circuit Breaker", "🔴 ACTIVE", help=cb_reason, delta_color="inverse")
        else:
            st.metric("Circuit Breaker", "✅ OK")

    if extended and robot is not None:
        er1, er2, er3 = st.columns(3)
        with er1:
            consec_loss = risk_summary.get("consecutive_losses", 0)
            max_cl = config.get("trading", "max_consecutive_losses")
            st.metric("Consec. Losses", f"{consec_loss}", delta=f"Max: {max_cl}", delta_color="inverse")
        with er2:
            window_loss = risk_summary.get("window_loss_pct", 0)
            cb_thresh = config.get("risk_management", "circuit_breaker_loss_pct")
            st.metric("Window Loss", f"{window_loss:.1f}%", delta=f"CB: {cb_thresh:.0f}%", delta_color="inverse")
        with er3:
            mode = "📝 Paper" if robot.paper_trading else "💵 Real"
            st.metric("Mode", mode)

        consec_err = robot.consecutive_errors
        max_err = config.get("health_check", "max_consecutive_errors")
        if consec_err > 0:
            st.warning(f"⚠️ {consec_err}/{max_err} consecutive errors — health check will restart automatically")
