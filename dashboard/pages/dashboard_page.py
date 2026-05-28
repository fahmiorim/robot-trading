"""Dashboard overview page — bot status, risk summary, strategy signals, MT5 status."""

import streamlit as st
import pandas as pd

from dashboard.components import render_account_info, render_strategy_signals, render_risk_metrics


def render():
    st.title("📊 Dashboard Overview")
    config = st.session_state.config
    robot = st.session_state.robot

    # ── Bot Status ──
    st.subheader("🤖 Bot Status")
    with st.container(border=True):
        status = robot.status() if hasattr(robot, "status") else {}

        s1, s2, s3, s4, s5 = st.columns(5)
        with s1:
            st.metric("Symbol", status.get("symbol", config.get("general", "symbol")))
        with s2:
            st.metric("Timeframe", status.get("timeframe", config.get("general", "timeframe")))
        with s3:
            mode = "📝 Paper" if status.get("paper_trading", True) else "💵 Real"
            st.metric("Mode", mode)
        with s4:
            cycles = status.get("cycle_count", robot.cycle_count)
            st.metric("Cycles", f"{cycles}")
        with s5:
            errors = status.get("consecutive_errors", robot.consecutive_errors)
            st.metric("Errors", f"{errors}", delta_color="inverse")

        s6, s7, s8, s9 = st.columns(4)
        with s6:
            regime = status.get("current_regime", robot.current_regime if hasattr(robot, "current_regime") else "unknown")
            colors = {"trending": "green", "ranging": "orange", "choppy": "red"}
            c = colors.get(regime.lower(), "gray")
            st.markdown(f"**Regime:** <span style='color:{c};font-weight:700'>{regime.upper()}</span>", unsafe_allow_html=True)
        with s7:
            best = status.get("best_strategy", "")
            st.markdown(f"**Best Strategy:** {best if best else '—'}")
        with s8:
            ml_acc = status.get("ml_accuracy", None)
            st.markdown(f"**ML Accuracy:** {ml_acc:.1%}" if ml_acc is not None else "**ML:** Not trained")
        with s9:
            pairs = status.get("pairlist_count", 0)
            st.markdown(f"**Pairs Tracked:** {pairs}")

    # ── MT5 Account Info (reusable component) ──
    st.subheader("🏦 Account Info")
    with st.container(border=True):
        render_account_info()

    # ── Risk Snapshot (reusable component) ──
    st.subheader("🛡️ Risk Snapshot")
    with st.container(border=True):
        try:
            risk_summary = robot.risk.get_status_summary()
            render_risk_metrics(risk_summary, config)
        except Exception as e:
            st.info(f"Risk data unavailable: {e}")

    # ── Strategy Signals (reusable component) ──
    st.subheader("📡 Strategy Signals")
    with st.container(border=True):
        data = st.session_state.get("_last_data")
        render_strategy_signals(robot, data)

    # ── Recent Trades ──
    st.subheader("📜 Recent Trades")
    with st.container(border=True):
        dc = st.session_state.get("dashboard_ctrl")
        if dc:
            try:
                trades = dc.get_trade_history(limit=10)
                if trades:
                    df = pd.DataFrame(trades)
                    st.dataframe(df, width='stretch', hide_index=True)
                else:
                    st.info("No recent trades")
            except Exception as e:
                st.info(f"Could not load trades: {e}")
        else:
            st.info("Dashboard controller not available")
