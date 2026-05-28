"""Helper functions for the dashboard — MT5 connection, symbol cache, robot lifecycle."""

import time
from datetime import datetime
from typing import List, Optional
import streamlit as st
import MetaTrader5 as mt5
from src.configuration.manager import ConfigManager

logger = None  # lazy init

_SYMBOL_CACHE: List[str] = []
_SYMBOL_CACHE_TIME: float = 0
_SYMBOL_CACHE_TTL = 60  # seconds


def _get_logger():
    global logger
    if logger is None:
        from src.utils.logging import get_logger
        logger = get_logger("dashboard.helpers")
    return logger


def ensure_mt5() -> bool:
    """Ensure MT5 is initialized; returns True if ready."""
    if mt5.initialize():
        st.session_state.mt5_initialized = True
        return True
    st.session_state.mt5_initialized = False
    _get_logger().warning("MT5 initialization failed")
    return False


def cleanup_mt5():
    """Shutdown MT5 connection."""
    try:
        mt5.shutdown()
    except Exception:
        pass
    st.session_state.mt5_initialized = False


def get_available_symbols() -> List[str]:
    """Return available symbols from MT5 with caching."""
    global _SYMBOL_CACHE, _SYMBOL_CACHE_TIME

    now = time.time()
    if _SYMBOL_CACHE and (now - _SYMBOL_CACHE_TIME) < _SYMBOL_CACHE_TTL:
        return _SYMBOL_CACHE

    try:
        if mt5.initialize():
            symbols = mt5.symbols_get()
            if symbols is not None and len(symbols) > 0:
                result = sorted([s.name for s in symbols])
                _SYMBOL_CACHE = result
                _SYMBOL_CACHE_TIME = now
                _get_logger().info(f"Fetched {len(result)} symbols from MT5")
                return result
    except Exception as e:
        _get_logger().warning(f"Could not fetch symbols from MT5: {e}")

    _SYMBOL_CACHE = []
    _SYMBOL_CACHE_TIME = now
    return []


def refresh_robot(config: ConfigManager):
    """Re-create the robot instance in session state."""
    from src.controllers.trading_controller import TradingController
    from src.controllers.dashboard_controller import DashboardController
    st.session_state.robot = TradingController(config=config)
    st.session_state.dashboard_ctrl = DashboardController(config=config)
    st.session_state.last_refresh = time.time()


def map_sig(val: int) -> str:
    """Map numeric signal to human-readable string."""
    return "BUY" if val == 1 else "SELL" if val == -1 else "HOLD"
