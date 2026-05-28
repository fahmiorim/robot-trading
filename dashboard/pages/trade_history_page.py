"""Trade History page — browse trades from DB or MT5."""

import streamlit as st
import pandas as pd

from dashboard.helpers import ensure_mt5
from dashboard.components import render_trade_metrics
from src.exchange.helpers import get_trade_history
from src.controllers.dashboard_controller import DashboardController


def render():
    st.title("📜 Trade History")
    dc = st.session_state.get("dashboard_ctrl", DashboardController())

    days = st.slider("Days", 1, 365, 30)
    source = st.radio("Source", ["🤖 Robot Database", "📊 MT5 Platform"], horizontal=True)

    with st.spinner("Loading..."):
        try:
            if source == "🤖 Robot Database":
                history = dc.get_trade_history(limit=500)
                if history:
                    df = pd.DataFrame(history)
                    st.dataframe(df, width='stretch', hide_index=True)
                    render_trade_metrics(df, profit_col="profit")

                    summary = dc.get_trade_summary(days)
                    if summary:
                        st.subheader("📊 Aggregate Stats")
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            st.metric("Total Trades", int(summary.get('total_trades', 0)))
                        with c2:
                            st.metric("Open Trades", int(summary.get('open_trades', 0)))
                        with c3:
                            st.metric("Total P&L", f"${summary.get('total_profit', 0):.2f}")
                        with c4:
                            st.metric("Win Rate", f"{summary.get('win_rate', 0):.1f}%")
                else:
                    st.info("No trade history in database")

            else:  # MT5 Platform
                if ensure_mt5():
                    history = get_trade_history(days)
                    if history is not None and len(history) > 0:
                        st.dataframe(history, width='stretch')
                        profit_col = next((c for c in ['profit', 'Profit', 'pnl', 'P&L']
                                          if c in history.columns), None)
                        if profit_col:
                            render_trade_metrics(history, profit_col=profit_col)
                        else:
                            st.info("No profit column found in MT5 data")
                    else:
                        st.info("No trade history found from MT5")
                else:
                    st.warning("MT5 not connected")
        except Exception as e:
            st.error(f"Error: {e}")
