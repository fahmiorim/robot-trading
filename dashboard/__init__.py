"""AI Trading Robot Dashboard — Streamlit multi-page app.

Usage:
    streamlit run dashboard.py

Startup flow:
  1. Quick DB connectivity check
  2. If DB unavailable → show setup wizard (``setup_wizard.py``)
  3. If DB available → init session state → render dashboard
"""

import os
import time
import atexit
from datetime import datetime

import streamlit as st

from src.controllers.trading_controller import TradingController
from src.controllers.dashboard_controller import DashboardController
from src.configuration import ConfigManager
from src.worker import Worker
from src.utils.logging import get_logger
from src.utils.env import load_env
from src.rpc.websocket import set_shared

from dashboard.styles import inject_css
from dashboard.helpers import cleanup_mt5
from dashboard.components import render_auto_trade_controls

logger = get_logger("dashboard")


def _init_session_state():
    """Initialize Streamlit session state variables."""
    if "config" not in st.session_state:
        st.session_state.config = ConfigManager()

    config = st.session_state.config

    if "robot" not in st.session_state:
        st.session_state.robot = TradingController(config=config)

    if "dashboard_ctrl" not in st.session_state:
        st.session_state.dashboard_ctrl = DashboardController(config=config)

    if "worker" not in st.session_state:
        st.session_state.worker = Worker(config)

    defaults = {
        "mt5_initialized": False,
        "auto_trading_enabled": False,
        "last_refresh": 0.0,
        "last_auto_cycle_time": time.time(),
        "backtest_results": {},
        "_last_data": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _render_sidebar():
    """Render the premium sidebar with navigation and status."""
    config = st.session_state.config

    with st.sidebar:
        # Brand header — glassmorphism premium
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01)); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 1.2rem 1rem; margin-bottom: 0.8rem;">
            <div style="font-size: 2.2rem; line-height: 1; margin-bottom: 0.4rem;">🤖</div>
            <div style="font-size: 1.1rem; font-weight: 800; letter-spacing: -0.02em; background: linear-gradient(135deg, #667eea, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">AI Trading Robot</div>
            <div style="font-size: 0.6rem; opacity: 0.35; letter-spacing: 0.1em; text-transform: uppercase; margin-top: 0.25rem;">v2.0 • Automated Trading System</div>
        </div>
        """, unsafe_allow_html=True)

        # Navigation
        page_labels = ["📊 Dashboard", "📈 Charts", "💱 Trading", "⚙️ Settings",
                       "📈 Backtest", "📜 Trade History", "ℹ️ About"]

        selected = st.radio(
            "Navigation", page_labels,
            index=0, label_visibility="collapsed", key="nav_radio"
        )
        page = selected

        # Auto-trading status panel (reusable component — compact mode)
        render_auto_trade_controls(compact=True)

        # Quick actions
        if st.button("🔄 Refresh Data", width='stretch'):
            st.cache_data.clear()
            st.rerun()

        st.checkbox("🔄 Live Refresh (10s)", value=False, key="live_refresh")

        # System info footer
        st.markdown(f"""
        <div style="margin-top: 1rem; padding: 0.6rem 0.8rem; background: rgba(255,255,255,0.02); border-radius: 8px; border: 1px solid rgba(255,255,255,0.03);">
            <div style="font-size: 0.6rem; opacity: 0.35; line-height: 1.8;">
                <div>🕐 {datetime.now().strftime('%H:%M:%S')} UTC</div>
                <div>⚙️ Database config</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    return page


def _check_db_accessible() -> bool:
    """Quick, lightweight check if MySQL is reachable with current .env settings.

    Returns True if we can connect to MySQL server (any database).
    Returns False if MySQL is unreachable or credentials are wrong.
    """
    load_env()
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            connect_timeout=3,
        )
        conn.close()
        return True
    except Exception:
        return False


def run():
    """Main dashboard entry point."""
    st.set_page_config(page_title="AI Trading Robot", layout="wide", page_icon="🤖")

    # Inject premium CSS
    inject_css()

    # ═══════════════════════════════════════════════════════════
    # DB Availability Check → redirect to setup wizard if needed
    # ═══════════════════════════════════════════════════════════
    if not _check_db_accessible():
        from dashboard.setup_wizard import render_setup_wizard
        render_setup_wizard()
        return

    # Initialize session state
    _init_session_state()

    # Register cleanup (only once)
    if "_cleanup_registered" not in st.session_state:
        atexit.register(cleanup_mt5)
        st.session_state["_cleanup_registered"] = True

    # Render sidebar and get selected page
    page = _render_sidebar()

    # Route to the appropriate page
    from dashboard.pages import dashboard_page, charts_page, trading_page, \
        settings_page, backtest_page, trade_history_page, about_page

    if page == "📊 Dashboard":
        dashboard_page.render()
    elif page == "📈 Charts":
        charts_page.render()
    elif page == "💱 Trading":
        trading_page.render()
    elif page == "⚙️ Settings":
        settings_page.render()
    elif page == "📈 Backtest":
        backtest_page.render()
    elif page == "📜 Trade History":
        trade_history_page.render()
    elif page == "ℹ️ About":
        about_page.render()

    # Non-blocking auto-refresh via st.rerun() — avoids full page reload
    if st.session_state.get("live_refresh"):
        if "last_rerun_time" not in st.session_state:
            st.session_state.last_rerun_time = time.time()
        elapsed = time.time() - st.session_state.last_rerun_time
        if elapsed >= 10:
            st.session_state.last_rerun_time = time.time()
            st.rerun()
