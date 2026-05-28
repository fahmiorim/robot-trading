"""Trading Controls page — auto trading, manual trading, positions, risk."""

import streamlit as st
import pandas as pd

from dashboard.helpers import ensure_mt5
from dashboard.components import render_auto_trade_controls, render_risk_metrics


def render():
    st.title("💱 Trading Controls")
    config = st.session_state.config
    robot = st.session_state.robot
    mt5_ok = ensure_mt5()

    # ── Auto Trading Controls (reusable component) ──
    st.subheader("Auto Trading")
    with st.container(border=True):
        render_auto_trade_controls()

    # ── Manual Trading ──
    st.subheader("Manual Trading")
    with st.container(border=True):
        mc = st.columns([1, 1, 2])
        with mc[0]:
            symbol = st.text_input("Symbol", value=config.get("general", "symbol"), key="trade_symbol")
        with mc[1]:
            volume = st.number_input("Volume", min_value=0.01, max_value=100.0, value=0.1, step=0.01, key="trade_vol")
        with mc[2]:
            st.caption("")

        if st.button("BUY", type="primary", width='stretch'):
            if ensure_mt5():
                try:
                    result = robot.open_trade(symbol, "buy", volume)
                    if result.get("success"):
                        st.success(f"BUY order placed! Ticket: {result.get('ticket', 'N/A')}")
                    else:
                        st.error(f"BUY failed: {result.get('error', 'Unknown')}")
                except Exception as e:
                    st.error(f"Error: {e}")

        if st.button("SELL", type="secondary", width='stretch'):
            if ensure_mt5():
                try:
                    result = robot.open_trade(symbol, "sell", volume)
                    if result.get("success"):
                        st.success(f"SELL order placed! Ticket: {result.get('ticket', 'N/A')}")
                    else:
                        st.error(f"SELL failed: {result.get('error', 'Unknown')}")
                except Exception as e:
                    st.error(f"Error: {e}")

    # ── Open Positions ──
    st.subheader("Open Positions")
    with st.container(border=True):
        if robot.paper_trading or mt5_ok:
            try:
                if robot.paper_trading:
                    try:
                        robot.update_paper_positions()
                    except Exception:
                        pass
                    positions = robot.paper_positions
                    st.metric("Paper Balance", f"${robot.paper_balance:.2f}")
                else:
                    positions = robot.exchange.get_open_positions()

                if positions:
                    pdf = pd.DataFrame(positions)
                    st.dataframe(pdf, width='stretch', hide_index=True)
                    total_pnl = sum(p.get("profit", 0) for p in positions)
                    st.metric("Total Unrealized P&L", f"${total_pnl:.2f}", delta=f"{total_pnl:.2f}")
                    cols = st.columns(min(len(positions), 5))
                    for i, pos in enumerate(positions[:5]):
                        with cols[i]:
                            ticket = pos.get("ticket", "")
                            ptype = pos.get("type", pos.get("action", ""))
                            vol = pos.get("volume", 0)
                            if st.button(f"Close {ptype} {vol}", key=f"close_{ticket}"):
                                if robot.paper_trading or ensure_mt5():
                                    result = robot.close_position(ticket)
                                    if result.get("success"):
                                        st.success(f"Position {ticket} closed!")
                                        st.rerun()
                                    else:
                                        st.error(f"Close failed: {result.get('error', 'Unknown')}")
                else:
                    st.info("No open positions")
            except Exception as e:
                st.info(f"Could not fetch positions: {e}")

    # ── Risk Management (reusable component with extended mode) ──
    st.subheader("Risk Management")
    with st.container(border=True):
        risk_summary = robot.risk.get_status_summary()
        render_risk_metrics(risk_summary, config, extended=True, robot=robot)
