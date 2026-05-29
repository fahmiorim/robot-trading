"""Charts & Market Analysis page — price chart, market analysis, signals."""

import time
import textwrap
import os
import json
import urllib.parse
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# Gentle auto-refresh (15 seconds) to update indicators and recommendations
st_autorefresh(interval=15000, limit=None, key="chart_autorefresh")

from dashboard.helpers import ensure_mt5, refresh_robot, map_sig, get_available_symbols

from src.configuration import TIMEFRAME_MAP
from src.rpc.websocket import set_shared, get_shared

def format_mt5_price(price: float, digits: int = 2) -> tuple:
    """Format a price MT5-style: split into a small part and the last two large digits."""
    if not price or price <= 0:
        return "0.", "00"
    price_str = f"{price:.{digits}f}"
    if len(price_str) >= 2:
        return price_str[:-2], price_str[-2:]
    return price_str, ""



def render():
    st.title("📈 Charts & Market Analysis")
    config = st.session_state.config
    robot = st.session_state.robot

    # ── Quick Trade Execution via Query Parameters ──
    query_params = st.query_params
    if "trade_action" in query_params:
        action = query_params["trade_action"]
        volume_str = query_params.get("trade_volume", "0.1")
        try:
            volume = float(volume_str)
        except ValueError:
            volume = 0.10

        st.session_state["mt5_lot_value"] = volume

        if "trade_action" in st.query_params:
            del st.query_params["trade_action"]
        if "trade_volume" in st.query_params:
            del st.query_params["trade_volume"]

        if not ensure_mt5():
            st.error("MT5 terminal not connected. Cannot execute trade.")
        else:
            with st.spinner(f"Executing {action.upper()} trade of {volume:.2f} lots..."):
                try:
                    sig = 1 if action.lower() == "buy" else -1
                    res = robot.execute_trade(sig, volume=volume)
                    if res.get("success"):
                        st.success(f"Successfully executed {action.upper()} {volume:.2f} lots! Ticket: {res.get('order_id', res.get('order', 'N/A'))}")
                    else:
                        st.error(f"Execution failed: {res.get('error', 'Unknown error')}")
                except Exception as ex:
                    st.error(f"Error executing trade: {ex}")
                time.sleep(2)
                st.rerun()

    # ── Market Data Auto-fetch (realtime) ──
    if ensure_mt5():
        try:
            current_sym = config.get("general", "symbol")
            current_tf = config.get("general", "timeframe")
            data = robot.exchange.fetch_ohlcv(current_sym, current_tf, 200)  # Direct fetch from MT5 API (no DB writing)
            st.session_state["_last_data"] = data
            st.session_state["_last_fetch_time"] = time.time()
        except Exception as e:
            st.caption(f"Realtime fetch error: {e}")

    # ── Market Controls ──
    with st.container(border=True):
        cc = st.columns([2, 2, 2, 1.5], vertical_alignment="bottom")
        with cc[0]:
            avail_sym = get_available_symbols()
            current_sym = config.get("general", "symbol")
            if avail_sym:
                sym_idx = avail_sym.index(current_sym) if current_sym in avail_sym else 0
                symbol = st.selectbox("Symbol", avail_sym, index=sym_idx, key="chart_symbol")
            else:
                symbol = st.text_input("Symbol", value=current_sym, key="chart_symbol")
            if symbol != config.get("general", "symbol"):
                config.set_global("general", "symbol", symbol)
                refresh_robot(config)
                st.rerun()
        with cc[1]:
            tf_opts = list(TIMEFRAME_MAP.keys())
            cur_tf = config.get("general", "timeframe")
            tf_idx = tf_opts.index(cur_tf) if cur_tf in tf_opts else 0
            timeframe = st.selectbox("Timeframe", tf_opts, index=tf_idx, key="chart_tf")
            if timeframe != cur_tf:
                config.set_global("general", "timeframe", timeframe)
                from src.constants.timeframes import TIMEFRAME_MINUTES
                tf_minutes = TIMEFRAME_MINUTES.get(timeframe, 15)
                config.set_global("general", "cycle_interval_minutes", tf_minutes)
                refresh_robot(config)
                st.rerun()
        # Data count & candle selection removed for pure realtime mode
        # Fixed window of last 200 candles will be displayed
        with cc[3]:
            fetch_now = st.button("Refresh Data", width='stretch', type="primary")
            if fetch_now:
                with st.spinner("Fetching..."):
                    try:
                        if not ensure_mt5():
                            st.stop()
                        data = robot.fetch_data(200)
                        st.success(f"Loaded {len(data)} candles")
                        st.session_state["_last_data"] = data
                        st.session_state["_last_fetch_time"] = time.time()
                    except Exception as e:
                        st.error(f"Fetch error: {e}")

    # ── Price Chart ──
    st.subheader("Price Chart")
    with st.container(border=True):
        data = st.session_state.get("_last_data")
        if data is not None:
            # Fixed display of last 200 candles for realtime view
            limit = 200
            chart_data = data.tail(limit) if len(data) > limit else data

            # Reset index to get time column
            df_json = chart_data.reset_index()
            # Convert datetime to Unix epoch integer seconds
            df_json['time'] = df_json['time'].astype('int64') // 10**9
            
            # Convert to list of dicts
            records = df_json[['time', 'open', 'high', 'low', 'close']].to_dict(orient='records')
            
            # Write to dashboard/static/chart_data.json
            static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
            json_path = os.path.join(static_dir, "chart_data.json")
            try:
                with open(json_path, "w") as f:
                    json.dump(records, f)
            except Exception as e:
                st.caption(f"Error saving chart data json: {e}")

            # Get symbol info & current bid/ask
            sym_info = robot.exchange.get_symbol_info(symbol)
            symbol_desc = sym_info.get("description", "Spot Gold 100 Troy Oz")
            digits = sym_info.get("digits", 2)

            ws_port = get_shared("ws_port", 8765)
            static_port = get_shared("static_port", 8767)

            # Let's url encode the parameters
            params = urllib.parse.urlencode({
                "ws_port": ws_port,
                "symbol": symbol,
                "timeframe": timeframe,
                "digits": digits,
                "desc": symbol_desc
            })

            iframe_url = f"http://localhost:{static_port}/chart_panel.html?{params}"
            st.iframe(iframe_url, height=520)
        else:
            st.info("Click 'Refresh Data' to load market data")

    # ── Market Analysis ──
    st.subheader("Market Analysis")
    with st.container(border=True):
        if data is not None:
            ca, cb = st.columns(2)
            with ca:
                regime = robot.detect_regime(data)
                robot.current_regime = regime
                set_shared("regime", regime)
                
                # Colors map for Glass Cards
                colors_text = {"trending": "#10b981", "ranging": "#f59e0b", "choppy": "#ef4444"}
                colors_bg = {"trending": "rgba(16, 185, 129, 0.06)", "ranging": "rgba(245, 158, 11, 0.06)", "choppy": "rgba(239, 68, 68, 0.06)"}
                colors_border = {"trending": "rgba(16, 185, 129, 0.18)", "ranging": "rgba(245, 158, 11, 0.18)", "choppy": "rgba(239, 68, 68, 0.18)"}
                
                regime_lower = regime.lower()
                c_text = colors_text.get(regime_lower, "#9ca3af")
                c_bg = colors_bg.get(regime_lower, "rgba(255, 255, 255, 0.02)")
                c_border = colors_border.get(regime_lower, "rgba(255, 255, 255, 0.05)")
                
                st.markdown(textwrap.dedent(f"""
                <div style="font-family: 'Outfit', sans-serif; background: {c_bg}; border: 1px solid {c_border}; border-radius: 12px; padding: 1.1rem; display: flex; align-items: center; gap: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
                    <div style="font-size: 2.2rem;">🔍</div>
                    <div>
                        <div style="font-size: 0.65rem; opacity: 0.55; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;">MARKET REGIME</div>
                        <div style="font-size: 1.15rem; font-weight: 800; color: {c_text}; text-transform: uppercase; margin-top: 2px;">{regime}</div>
                        <div style="font-size: 0.7rem; opacity: 0.7; margin-top: 4px; line-height: 1.4;">Detects trending, ranging or choppy market conditions.</div>
                    </div>
                </div>
                """), unsafe_allow_html=True)
                
            with cb:
                now = time.time()
                last_backtest_time = st.session_state.get("_last_backtest_time", 0.0)
                if now - last_backtest_time > 30.0 or "backtest_results" not in st.session_state:
                    with st.spinner("Running backtest..."):
                        try:
                            results = robot.run_backtest_all(data)
                            st.session_state.backtest_results = results
                            st.session_state["_last_backtest_time"] = now
                        except Exception as e:
                            st.caption(f"Backtest error: {e}")
                
                results = st.session_state.get("backtest_results", {})
                name = robot.best_strategy.name if robot.best_strategy else "N/A"
                set_shared("best_strategy", name)
                
                st.markdown(textwrap.dedent(f"""
                <div style="font-family: 'Outfit', sans-serif; background: rgba(99, 102, 241, 0.05); border: 1px solid rgba(99, 102, 241, 0.18); border-radius: 12px; padding: 1.1rem; display: flex; align-items: center; gap: 16px; box-shadow: 0 4px 15px rgba(99, 102, 241, 0.05);">
                    <div style="font-size: 2.2rem; filter: drop-shadow(0 0 10px rgba(99,102,241,0.25));">🏆</div>
                    <div>
                        <div style="font-size: 0.65rem; opacity: 0.55; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; color: #a5b4fc;">RECOMMENDED STRATEGY</div>
                        <div style="font-size: 1.15rem; font-weight: 800; color: #ffffff; margin-top: 2px;">{name}</div>
                        <div style="font-size: 0.7rem; opacity: 0.7; margin-top: 4px; color: #c7d2fe; line-height: 1.4;">Optimized best performer based on walk-forward backtest.</div>
                    </div>
                </div>
                """), unsafe_allow_html=True)
        else:
            st.info("Fetch data to see market analysis")
