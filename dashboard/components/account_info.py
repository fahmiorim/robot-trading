"""Reusable component: MT5 Account Info card."""

import streamlit as st

from dashboard.helpers import ensure_mt5
from src.exchange.helpers import get_account_info


def render_account_info():
    """Render a 5-column MT5 Account Info card (Balance, Equity, Margin, P&L).

    Must be called inside a Streamlit container. Returns True if data was
    displayed, False if MT5 is not connected.
    """
    if ensure_mt5():
        try:
            info = get_account_info()
            a1, a2, a3, a4, a5 = st.columns(5)
            with a1:
                st.metric("Balance", f"${info.get('balance', 0):.2f}")
            with a2:
                st.metric("Equity", f"${info.get('equity', 0):.2f}")
            with a3:
                st.metric("Free Margin", f"${info.get('free_margin', 0):.2f}")
            with a4:
                st.metric("Margin Level", f"{info.get('margin_level', 0):.2f}%")
            with a5:
                profit_val = info.get('profit', 0)
                st.metric("Daily P&L", f"${profit_val:.2f}", delta=f"{profit_val:.2f}")
            return True
        except Exception as e:
            st.info(f"Could not fetch account info: {e}")
            return False
    else:
        st.warning("⚠️ MT5 not connected")
        return False
