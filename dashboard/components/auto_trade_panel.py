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
        <div style="font-family: 'Outfit', sans-serif; background: linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(15, 15, 26, 0.2)); backdrop-filter: blur(10px); border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 14px; padding: 0.8rem 1.1rem; margin-bottom: 0.8rem; box-shadow: 0 4px 15px rgba(239, 68, 68, 0.08);">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span class="live-dot red"></span>
                <span style="font-weight: 800; font-size: 0.85rem; color: #f87171; letter-spacing: 0.02em;">AUTO TRADING ACTIVE</span>
            </div>
            <div style="font-size: 0.72rem; opacity: 0.6; margin-top: 8px; display: flex; gap: 16px; font-weight: 500;">
                <span>🔄 Cycles: {cycles}</span>
                <span>⚡ Running</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("⏹ STOP Auto Trading", use_container_width=True, type="primary"):
            st.session_state.worker.stop()
            config.set("general", "auto_trade", False)
            config.save()
            st.session_state.auto_trading_enabled = False
            set_shared("auto_trading", False)
            st.session_state.last_auto_cycle_time = time.time()
            st.rerun()
    else:
        st.markdown("""
        <div style="font-family: 'Outfit', sans-serif; background: rgba(255, 255, 255, 0.01); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 14px; padding: 0.8rem 1.1rem; margin-bottom: 0.8rem; opacity: 0.7;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span class="live-dot" style="background: rgba(255,255,255,0.15); box-shadow: none; animation: none;"></span>
                <span style="font-weight: 600; font-size: 0.85rem; opacity: 0.7; color: #ffffff;">Auto Trading OFF</span>
            </div>
            <div style="font-size: 0.7rem; opacity: 0.45; margin-top: 6px; font-weight: 500;">Use Trading page to start</div>
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
    """Full page version — custom clean HTML/CSS status bar + start/stop buttons."""
    from src.constants.timeframes import TIMEFRAME_MAP
    import time

    # Gather data
    is_running = st.session_state.auto_trading_enabled
    cycles = st.session_state.robot.cycle_count
    last_cycle = st.session_state.last_auto_cycle_time
    sec_ago = int(time.time() - last_cycle)
    
    if sec_ago < 60:
        last_cycle_str = f"{sec_ago}s ago"
    elif sec_ago < 3600:
        last_cycle_str = f"{sec_ago // 60}m ago"
    else:
        last_cycle_str = f"{sec_ago // 3600}h ago"
        
    tf = config.get("general", "timeframe")
    ci = TIMEFRAME_MAP.get(tf, 15)
    
    status_text = "🔴 RUNNING" if is_running else "⚪ OFF"
    status_color = "#f87171" if is_running else "#9ca3af"
    
    # Styled HTML status bar
    html_metrics = f"""
    <div style="font-family: 'Outfit', sans-serif; display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.02); padding: 10px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 12px; margin-top: 8px;">
        <div style="flex: 1; text-align: center;">
            <div style="font-size: 0.62rem; opacity: 0.5; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;">STATUS</div>
            <div style="font-size: 0.85rem; font-weight: 800; color: {status_color};">{status_text}</div>
        </div>
        <div style="width: 1px; height: 20px; background: rgba(255,255,255,0.08);"></div>
        <div style="flex: 1; text-align: center;">
            <div style="font-size: 0.62rem; opacity: 0.5; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;">CYCLES</div>
            <div style="font-size: 0.85rem; font-weight: 700; color: #ffffff;">{cycles}</div>
        </div>
        <div style="width: 1px; height: 20px; background: rgba(255,255,255,0.08);"></div>
        <div style="flex: 1; text-align: center;">
            <div style="font-size: 0.62rem; opacity: 0.5; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;">LAST CYCLE</div>
            <div style="font-size: 0.85rem; font-weight: 700; color: #ffffff;">{last_cycle_str}</div>
        </div>
        <div style="width: 1px; height: 20px; background: rgba(255,255,255,0.08);"></div>
        <div style="flex: 1; text-align: center;">
            <div style="font-size: 0.62rem; opacity: 0.5; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;">INTERVAL</div>
            <div style="font-size: 0.85rem; font-weight: 700; color: #a5b4fc;">{ci} min</div>
        </div>
    </div>
    """
    st.markdown(html_metrics, unsafe_allow_html=True)
    
    if is_running:
        st.caption("Auto trading active — do not close this page!")

    # Start/Stop Button
    if not is_running:
        if st.button("▶️ START AUTO TRADING", type="primary", use_container_width=True):
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
        if st.button("⏹ STOP AUTO TRADING", type="primary", use_container_width=True):
            st.session_state.worker.stop()
            st.session_state.config.set("general", "auto_trade", False)
            st.session_state.config.save()
            st.session_state.auto_trading_enabled = False
            set_shared("auto_trading", False)
            st.session_state.last_auto_cycle_time = time.time()
            st.success("Auto Trading stopped.")
            st.rerun()
