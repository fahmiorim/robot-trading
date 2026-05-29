import streamlit as st

from dashboard.helpers import refresh_robot

from dashboard.pages.settings.general_tab import render as render_general
from dashboard.pages.settings.strategies_tab import render as render_strategies
from dashboard.pages.settings.risk_tab import render as render_risk
from dashboard.pages.settings.health_tab import render as render_health
from dashboard.pages.settings.ml_tab import render as render_ml
from dashboard.pages.settings.trading_tab import render as render_trading
from dashboard.pages.settings.backtest_tab import render as render_backtest
from dashboard.pages.settings.agent_tab import render as render_agent
from dashboard.pages.settings.rpc_tab import render as render_rpc


def render():
    st.title("\u2699\ufe0f Settings Editor")
    config = st.session_state.config
    edited = False

    config_warnings = config.validate()

    tab_labels = [
        "\U0001f4cb General",
        "\U0001f4c8 Strategies",
        "\U0001f6e1\ufe0f Risk & Protection",
        "\U0001f3e5 Health",
        "\U0001f9e0 ML",
        "\U0001f4b9 Trading, DCA & Order",
        "\U0001f4ca Backtest",
        "\U0001f916 Signals & Agent",
        "\U0001f4e1 RPC & API",
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
        edited |= render_trading(config)
    with tabs[6]:
        edited |= render_backtest(config)
    with tabs[7]:
        edited |= render_agent(config)
    with tabs[8]:
        edited |= render_rpc(config)

    # ── CONFIG WARNINGS ──────────────────────────────────────
    if config_warnings:
        with st.expander("\u26a0\ufe0f Config Warnings", expanded=True):
            for w in config_warnings:
                st.warning(w)

    # ── SAVE / RESET ─────────────────────────────────────────
    st.markdown("---")
    cs1, cs2, cs3 = st.columns([1, 1, 3])
    with cs1:
        if st.button("\U0001f4be Save Config", width='stretch', type="primary"):
            if config.save():
                refresh_robot(config)
                st.success("Saved & robot reloaded!")
            else:
                st.error("Save failed!")
    with cs2:
        if st.button("\U0001f504 Reset Defaults", width='stretch'):
            config.reset_to_defaults()
            config.save()
            refresh_robot(config)
            st.rerun()
    with cs3:
        if edited:
            st.info("\u26a1 Changes detected \u2014 click Save Config")
