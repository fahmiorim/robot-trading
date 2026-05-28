"""Reusable component: Strategy Signals row (4 badges)."""

import streamlit as st

from dashboard.helpers import map_sig


def render_strategy_signals(robot, data):
    """Render 4-column signal badges (Strategy, ML, Agent, Swarm).

    Parameters
    ----------
    robot : TradingController
    data : pd.DataFrame
        Market data with OHLCV structure.
    """
    if data is None:
        st.info("💡 Fetch market data to see signals")
        return

    try:
        s1, s2, s3, s4 = st.columns(4)
        _render_signal_badge(s1, "Strategy", robot.get_signal(data))
        _render_signal_badge(s2, "ML", robot.get_signal(data, use_ml=True))
        _render_signal_badge(s3, "Agent", robot.get_signal(data, use_agent=True))
        _render_signal_badge(s4, "Swarm", robot.get_signal(data, use_swarm=True))
    except Exception as e:
        st.info(f"Signals unavailable: {e}")


def _render_signal_badge(column, label: str, signal: int):
    """Render a single signal badge inside a Streamlit column."""
    txt = map_sig(signal)
    color = {"BUY": "green", "SELL": "red", "HOLD": "gray"}.get(txt, "gray")
    column.markdown(
        f"**{label}:** <span style='color:{color};font-weight:700'>{txt}</span>",
        unsafe_allow_html=True,
    )
