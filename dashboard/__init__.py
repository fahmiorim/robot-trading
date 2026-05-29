"""AI Trading Robot Dashboard — Streamlit multi-page app.

Usage:
    streamlit run dashboard/__init__.py
    python -m dashboard

Startup flow:
  1. Quick DB connectivity check
  2. If DB unavailable → show setup wizard (``setup_wizard.py``)
  3. If DB available → init session state → render dashboard
"""

import os
import time
import atexit
import threading
import textwrap
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

logger = get_logger("dashboard")


import sys

class SharedState:
    @property
    def robot(self):
        return getattr(sys, "_global_robot", None)
    
    @robot.setter
    def robot(self, value):
        sys._global_robot = value
        
    @property
    def worker(self):
        return getattr(sys, "_global_worker", None)
        
    @worker.setter
    def worker(self, value):
        sys._global_worker = value

    @property
    def lock(self):
        if not hasattr(sys, "_global_lock"):
            sys._global_lock = threading.Lock()
        return sys._global_lock

shared_state = SharedState()


def _init_session_state():
    """Initialize Streamlit session state variables."""
    if "config" not in st.session_state:
        st.session_state.config = ConfigManager()

    config = st.session_state.config

    with shared_state.lock:
        if shared_state.robot is None:
            logger.info("Initializing global TradingController...")
            shared_state.robot = TradingController(config=config)
        
        if shared_state.worker is None:
            logger.info("Initializing global Worker...")
            shared_state.worker = Worker(shared_state.robot)
            shared_state.robot.worker = shared_state.worker

    st.session_state.robot = shared_state.robot
    st.session_state.worker = shared_state.worker

    if "dashboard_ctrl" not in st.session_state:
        st.session_state.dashboard_ctrl = DashboardController(config=config)

    defaults = {
        "mt5_initialized": False,
        "auto_trading_enabled": config.get("general", "auto_trade"),
        "last_refresh": 0.0,
        "last_auto_cycle_time": time.time(),
        "backtest_results": {},
        "_last_data": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Start worker only after session state is fully initialized
    with shared_state.lock:
        if shared_state.worker is not None and config.get("general", "auto_trade"):
            shared_state.worker.start()


def _render_sidebar():
    """Render the premium sidebar with navigation and status."""
    config = st.session_state.config

    with st.sidebar:
        # Brand header — glassmorphism premium
        st.markdown(textwrap.dedent("""
        <div style="font-family: 'Outfit', sans-serif; background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(139, 92, 246, 0.03)); backdrop-filter: blur(10px); border: 1px solid rgba(99, 102, 241, 0.18); border-radius: 14px; padding: 1.2rem 1.1rem; margin-bottom: 1rem; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
            <div style="font-size: 2.3rem; line-height: 1; margin-bottom: 0.5rem; filter: drop-shadow(0 0 12px rgba(99, 102, 241, 0.5));">🤖</div>
            <div style="font-size: 1.15rem; font-weight: 800; letter-spacing: -0.02em; background: linear-gradient(135deg, #ffffff 40%, #a5b4fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">AI Trading Robot</div>
            <div style="font-size: 0.62rem; opacity: 0.45; letter-spacing: 0.1em; text-transform: uppercase; margin-top: 0.3rem; font-weight: 600; color: #a5b4fc;">v2.0 • Automated Swarm System</div>
        </div>
        """), unsafe_allow_html=True)

        # Navigation
        page_labels = ["📊 Dashboard", "📈 Charts", "📊 Performance", "⚙️ Settings", "ℹ️ About"]

        selected = st.radio(
            "Navigation", page_labels,
            index=0, label_visibility="collapsed", key="nav_radio"
        )
        page = selected

        # Concept drift alert banner (visible only when active)
        try:
            robot = st.session_state.get("robot")
            if robot and getattr(robot, 'ml_service', None) and robot.ml_service.trainer.concept_drifted:
                st.markdown(textwrap.dedent("""
                <div style="font-family: 'Outfit', sans-serif; background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 12px; padding: 0.7rem 1rem; margin-top: 0.5rem; margin-bottom: 0.5rem; box-shadow: 0 0 20px rgba(239, 68, 68, 0.08);">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 1.2rem;">🚨</span>
                        <div>
                            <div style="font-size: 0.7rem; font-weight: 800; color: #fca5a5; letter-spacing: 0.05em; text-transform: uppercase;">Concept Drift</div>
                            <div style="font-size: 0.6rem; opacity: 0.8; color: #fef2f2; margin-top: 2px;">Akurasi ML turun drastis — retrain otomatis.</div>
                        </div>
                    </div>
                </div>
                """), unsafe_allow_html=True)
        except Exception:
            pass

        # System info footer
        st.markdown(textwrap.dedent(f"""
        <div style="margin-top: 0.5rem; padding: 0.6rem 0.8rem; background: rgba(255,255,255,0.02); border-radius: 8px; border: 1px solid rgba(255,255,255,0.03);">
            <div style="font-size: 0.6rem; opacity: 0.35; line-height: 1.8;">
                <div>🕐 {datetime.now().strftime('%H:%M:%S')} UTC</div>
                <div>⚙️ Database config</div>
            </div>
        </div>
        """), unsafe_allow_html=True)

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
    from dashboard.pages import dashboard_page, charts_page, performance_page, settings_page, about_page

    if page == "📊 Dashboard":
        dashboard_page.render()
    elif page == "📈 Charts":
        charts_page.render()
    elif page == "📊 Performance":
        performance_page.render()
    elif page == "⚙️ Settings":
        settings_page.render()
    elif page == "ℹ️ About":
        about_page.render()


