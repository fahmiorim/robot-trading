import streamlit as st

from dashboard.helpers import refresh_robot

from dashboard.pages.settings.general_tab import render as render_general
from dashboard.pages.settings.strategies_tab import render as render_strategies
from dashboard.pages.settings.risk_tab import render as render_risk
from dashboard.pages.settings.health_tab import render as render_health
from dashboard.pages.settings.ml_tab import render as render_ml
from dashboard.pages.settings.signals_tab import render as render_signals
from dashboard.pages.settings.trading_tab import render as render_trading
from dashboard.pages.settings.backtest_tab import render as render_backtest


def render():
    st.title("\u2699\ufe0f Settings Editor")
    config = st.session_state.config
    edited = False

    config_warnings = config.validate()

    tab_labels = [
        "\U0001f4cb General",
        "\U0001f4c8 Strategies",
        "\U0001f6e1\ufe0f Risk",
        "\U0001f3e5 Health",
        "\U0001f9e0 ML",
        "\U0001f4e1 Signals",
        "\U0001f4b9 Trading",
        "\U0001f4ca Backtest",
    ]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        edited |= render_general(config)
    with tabs[1]:
        edited |= render_strategies(config)
    with tabs[2]:
        edited |= render_risk(config)
    with tabs[3]:
        edited |= render_health(config)
    with tabs[4]:
        edited |= render_ml(config)
    with tabs[5]:
        edited |= render_signals(config)
    with tabs[6]:
        edited |= render_trading(config)
    with tabs[7]:
        edited |= render_backtest(config)

    # ── CONFIG WARNINGS ──────────────────────────────────────
    if config_warnings:
        with st.expander("\u26a0\ufe0f Config Warnings", expanded=True):
            for w in config_warnings:
                st.warning(w)

    # ── SAVE / RESET ─────────────────────────────────────────
    st.markdown("---")
    cs1, cs2, cs3 = st.columns([1, 1, 3])
    with cs1:
        if st.button("\U0001f4be Save Config", use_container_width=True, type="primary"):
            if config.save():
                refresh_robot(config)
                st.success("Saved & robot reloaded!")
            else:
                st.error("Save failed!")
    with cs2:
        if st.button("\U0001f504 Reset Defaults", use_container_width=True):
            config.reset_to_defaults()
            config.save()
            refresh_robot(config)
            st.rerun()
    with cs3:
        if edited:
            st.info("\u26a1 Changes detected \u2014 click Save Config")

    # ── ABOUT SYSTEM INFO ────────────────────────────────────
    st.markdown("---")
    with st.expander("ℹ️ About AI Trading Robot v2.0", expanded=False):
        st.markdown("""
        ### 🤖 AI Trading Robot v2.0
        
        **Features:**
        - **Multi-Strategy Core**: 5 technical strategies (MA Crossover, RSI, MACD, Bollinger Bands, Breakout)
        - **ML Integration**: Random Forest / Gradient Boosting / LSTM single-step prediction
        - **Market Regime Filter**: ADX-based regime classifier (Trending, Ranging, Choppy)
        - **Swarm Intelligence**: Weighted ensemble voting for trading consensus
        - **Backtester**: Tick-accurate historical simulation (slippage, spread, commission)
        - **Risk Controller**: Circuit breaker, daily drawdown, daily loss, cooldown timer
        - **Notification RPC**: Telegram alerts and real-time WebSocket dashboard
        
        **Tech Stack:** Python, MetaTrader 5, pandas, numpy, scikit-learn, Streamlit, Plotly
        """)
