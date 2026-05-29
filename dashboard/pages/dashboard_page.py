"""Dashboard overview page — bot status, risk summary, strategy signals, MT5 status."""

import streamlit as st
import pandas as pd

from streamlit_autorefresh import st_autorefresh
from src.rpc.websocket import get_shared
from dashboard.components import render_auto_trade_controls
from dashboard.helpers import ensure_mt5, get_available_symbols


def render():
    st.title("📊 Dashboard Overview")
    
    # Auto-refresh every 3 detik untuk update Streamlit-native components
    st_autorefresh(interval=3000, key="dashboard_autorefresh")
    
    ensure_mt5()
    robot = st.session_state.robot

    # ── Handle Close Position Action from URL query params ──
    query_params = st.query_params
    if "close_ticket" in query_params:
        ticket = query_params["close_ticket"]
        try:
            ticket_int = int(ticket)
            with st.spinner(f"Closing position {ticket_int}..."):
                result = robot.close_position(ticket_int)
                if result.get("success"):
                    st.success(f"✅ Position {ticket_int} closed successfully!")
                else:
                    st.error(f"❌ Failed to close position: {result.get('error', 'Unknown error')}")
        except Exception as e:
            st.error(f"⚠️ Error closing position: {e}")
        if "close_ticket" in st.query_params:
            del st.query_params["close_ticket"]
        st.rerun()

    # Get ports dynamically from shared state
    ws_port = get_shared("ws_port", 8765)
    static_port = get_shared("static_port", 8767)

    # ── Real-Time Panel via iframe (served from static HTTP server) ──
    # HTML served from http://localhost:{static_port}/panel.html
    # This avoids the deprecated st.components.v1.html() and uses a proper
    # http:// origin so WebSocket can connect from the iframe.
    # ws_port is passed as query param so the JS knows where to connect.
    st.iframe(f"http://localhost:{static_port}/panel.html?ws_port={ws_port}", height=500)

    # ── Trading & Execution Controls ──
    st.subheader("💱 Trading & Execution")
    config = st.session_state.config
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 8px 0; font-size:1.05rem; font-weight:700; color:#a5b4fc;'>🤖 Auto Trading Controls</h4>", unsafe_allow_html=True)
            
            # Real-time Auto Trading Controls iframe
            # Served from static HTTP server — avoids deprecated st.components.v1.html
            st.iframe(f"http://localhost:{static_port}/controls.html?ws_port={ws_port}", height=190)
            
    with col2:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 8px 0; font-size:1.05rem; font-weight:700; color:#a5b4fc;'>💱 Manual Order Execution</h4>", unsafe_allow_html=True)
            mc1, mc2 = st.columns(2)
            with mc1:
                avail_symbols = get_available_symbols()
                current_sym = config.get("general", "symbol")
                if avail_symbols:
                    sym_idx = avail_symbols.index(current_sym) if current_sym in avail_symbols else 0
                    manual_symbol = st.selectbox("Symbol", avail_symbols, index=sym_idx, key="manual_symbol")
                else:
                    manual_symbol = st.text_input("Symbol", value=current_sym, key="manual_symbol")
                    st.caption("MT5 tidak terhubung — ketik manual")
            with mc2:
                manual_volume = st.number_input("Volume", min_value=0.01, max_value=100.0, value=0.1, step=0.01, key="manual_vol")
            
            mb1, mb2 = st.columns(2)
            with mb1:
                if st.button("BUY", type="primary", width='stretch'):
                    try:
                        result = robot.open_trade(manual_symbol, "buy", manual_volume)
                        if result.get("success"):
                            st.success(f"BUY order placed! Ticket: {result.get('ticket')}")
                            st.rerun()
                        else:
                            st.error(f"BUY failed: {result.get('error')}")
                    except Exception as e:
                        st.error(f"Error: {e}")
            with mb2:
                if st.button("SELL", type="secondary", width='stretch'):
                    try:
                        result = robot.open_trade(manual_symbol, "sell", manual_volume)
                        if result.get("success"):
                            st.success(f"SELL order placed! Ticket: {result.get('ticket')}")
                            st.rerun()
                        else:
                            st.error(f"SELL failed: {result.get('error')}")
                    except Exception as e:
                        st.error(f"Error: {e}")

    # ── Recent Trades (Static history component, perfect for manual reviews) ──
    st.subheader("📜 Recent Trades (History)")
    with st.container(border=True):
        dc = st.session_state.get("dashboard_ctrl")
        if dc:
            try:
                trades = dc.get_trade_history(limit=10)
                if trades:
                    df = pd.DataFrame(trades)
                    st.dataframe(df, width='stretch', hide_index=True)
                else:
                    st.info("No recent trades in database")
            except Exception as e:
                st.info(f"Could not load trades: {e}")
        else:
            st.info("Dashboard controller not available")
