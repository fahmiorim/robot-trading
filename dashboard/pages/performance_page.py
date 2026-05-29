"""Performance Analytics page — premium glass-card design."""
import streamlit as st

from dashboard.pages.performance.trade_history_tab import render as render_trade_history
from dashboard.pages.performance.backtest_tab import render as render_backtest
from dashboard.pages.performance.advanced_analyzers_tab import render as render_advanced_analyzers
from dashboard.pages.performance.hyperopt_tab import render as render_hyperopt


def render():
    st.title("📊 Performance & Analytics")
    config = st.session_state.config

    tab_labels = ["📜 Trade History", "▶️ Backtest Simulation", "📊 Advanced Analyzers", "🧬 Parameter Hyperopt"]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        render_trade_history(config)

    with tabs[1]:
        render_backtest(config)

    with tabs[2]:
        render_advanced_analyzers(config)

    with tabs[3]:
        render_hyperopt(config)
