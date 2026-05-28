"""Reusable component: Auto Trading start / stop controls."""

import time

import streamlit as st

from dashboard.helpers import ensure_mt5
from src.rpc.websocket import set_shared


def render_auto_trade_controls(*, compact: bool = False):
    """Render auto-trading status panel with start/stop buttons.

    Parameters
    ----------
    compact : bool
        If True, render a minimal status badge + start/stop button
        suitable for the sidebar.
    """
    config = st.session_state.config

    if compact:
        _render_compact(config)
    else:
        _render_full(config)


def _render_compact(config):
    """Compact sidebar version — minimal status + start/stop."""
    if st.session_state.auto_trading_enabled:
        cycles = st.session_state.robot.cycle_count
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01)); backdrop-filter: blur(10px); border: 1px solid rgba(239,68,68,0.3); border-radius: 14px; padding: 0.8rem 1rem; margin-bottom: 0.5rem;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span class="live-dot red"></span>
                <span style="font-weight: 700; font-size: 0.85rem; color: #f87171;">AUTO TRADING ACTIVE</span>
            </div>
            <div style="font-size: 0.7rem; opacity: 0.5; margin-top: 6px; display: flex; gap: 16px;">
                <span>&#x1F504; Cycles: {cycles}</span>
                <span>&#x26A1; Running</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("⏹ STOP Auto Trading", width='stretch', type="primary"):
            st.session_state.worker.stop()
            config.set("general", "auto_trade", False)
            config.save()
            st.session_state.auto_trading_enabled = False
            set_shared("auto_trading", False)
            st.session_state.last_auto_cycle_time = time.time()
            st.rerun()
    else:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01)); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 0.8rem 1rem; margin-bottom: 0.5rem; opacity: 0.7;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span class="live-dot" style="background: rgba(255,255,255,0.15); box-shadow: none; animation: none;"></span>
                <span style="font-weight: 600; font-size: 0.85rem; opacity: 0.7;">Auto Trading OFF</span>
            </div>
            <div style="font-size: 0.7rem; opacity: 0.45; margin-top: 4px;">Use Trading page to start</div>
        </div>
        """, unsafe_allow_html=True)
        auto_trade = config.get("general", "auto_trade")
        auto_trade_new = st.toggle("Enable Auto Trade", value=auto_trade)
        if auto_trade_new != auto_trade:
            config.set("general", "auto_trade", auto_trade_new)
            config.save()
            if auto_trade_new:
                st.session_state.worker.start()
                st.session_state.auto_trading_enabled = True
            else:
                st.session_state.worker.stop()
                st.session_state.auto_trading_enabled = False
            st.rerun()


def _render_full(config):
    """Full page version — metrics columns + prominent start/stop buttons.
    Cycle interval is auto-derived from the selected timeframe.
    """
    from src.constants.timeframes import TIMEFRAME_MAP

    at1, at2, at3, at4 = st.columns(4)
    with at1:
        if st.session_state.auto_trading_enabled:
            st.markdown("### 🔴 RUNNING")
            st.caption("Auto trading active — do not close this page!")
        else:
            st.markdown("### ⚪ OFF")
    with at2:
        cycles = st.session_state.robot.cycle_count
        st.metric("Cycles Completed", f"{cycles}")
    with at3:
        last_cycle = st.session_state.last_auto_cycle_time
        sec_ago = int(time.time() - last_cycle)
        st.metric("Last Cycle", f"{sec_ago}s ago" if sec_ago < 3600 else f"{sec_ago // 60}m ago")
    with at4:
        tf = config.get("general", "timeframe")
        ci = TIMEFRAME_MAP.get(tf, 15)
        st.metric("Interval", f"{ci} min", help=f"Auto-syncs to {tf} timeframe")

    at_row = st.columns([1, 1])
    with at_row[0]:
        if not st.session_state.auto_trading_enabled:
            if st.button("▶️ START AUTO TRADING", type="primary", width='stretch'):
                if ensure_mt5():
                    st.session_state.worker.start()
                    st.session_state.config.set("general", "auto_trade", True)
                    st.session_state.config.save()
                    st.session_state.auto_trading_enabled = True
                    set_shared("auto_trading", True)
                    st.session_state.last_auto_cycle_time = time.time()
                    st.success("Auto Trading started in background worker thread.")
                    st.rerun()
                else:
                    st.error("MT5 not connected!")
        else:
            if st.button("⏹ STOP AUTO TRADING", type="primary", width='stretch'):
                st.session_state.worker.stop()
                st.session_state.config.set("general", "auto_trade", False)
                st.session_state.config.save()
                st.session_state.auto_trading_enabled = False
                set_shared("auto_trading", False)
                st.session_state.last_auto_cycle_time = time.time()
                st.success("Auto Trading stopped.")
                st.rerun()
