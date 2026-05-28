"""Charts & Market Analysis page — price chart, market analysis, signals."""

import time
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from dashboard.helpers import ensure_mt5, refresh_robot, map_sig

from src.configuration import TIMEFRAME_MAP
from src.rpc.websocket import set_shared


def render():
    st.title("📈 Charts & Market Analysis")
    config = st.session_state.config
    robot = st.session_state.robot

    # ── Auto-fetch: load data automatically if none cached or stale ──
    data = st.session_state.get("_last_data")
    now = time.time()
    data_age = now - st.session_state.get("_last_fetch_time", 0) if data is not None else 9999
    should_auto_fetch = data is None or data_age > 120  # 2 min stale

    last_attempt = st.session_state.get("_last_auto_fetch_attempt", 0)
    if should_auto_fetch and (now - last_attempt) > 60:
        if ensure_mt5():
            try:
                with st.spinner("Loading market data..."):
                    data = robot.fetch_data()
                    st.session_state["_last_data"] = data
                    st.session_state["_last_fetch_time"] = now
            except Exception as e:
                st.caption(f"Auto-fetch unavailable: {e}")
        st.session_state["_last_auto_fetch_attempt"] = now

    # ── Market Controls ──
    with st.container(border=True):
        st.markdown('', unsafe_allow_html=True)
        cc = st.columns([2, 2, 2, 1.5])
        with cc[0]:
            symbol = st.text_input("Symbol", value=config.get("general", "symbol"), key="chart_symbol")
            if symbol != config.get("general", "symbol"):
                config.set("general", "symbol", symbol)
                config.save()
                refresh_robot(config)
                st.rerun()
        with cc[1]:
            tf_opts = list(TIMEFRAME_MAP.keys())
            cur_tf = config.get("general", "timeframe")
            tf_idx = tf_opts.index(cur_tf) if cur_tf in tf_opts else 0
            timeframe = st.selectbox("Timeframe", tf_opts, index=tf_idx, key="chart_tf")
            if timeframe != cur_tf:
                config.set("general", "timeframe", timeframe)
                config.save()
                refresh_robot(config)
                st.rerun()
        with cc[2]:
            data_count = st.number_input("Data Points", min_value=100, max_value=100000,
                                         value=config.get("general", "data_count"), step=1000, key="chart_count")
            saved = config.get("general", "data_count")
            if data_count != saved:
                config.set("general", "data_count", data_count)
                config.save()
        with cc[3]:
            st.markdown("<br>", unsafe_allow_html=True)
            fetch_now = st.button("Refresh Data", use_container_width=True, type="primary")
            if fetch_now:
                with st.spinner("Fetching..."):
                    try:
                        if not ensure_mt5():
                            st.stop()
                        data = robot.fetch_data(data_count)
                        st.success(f"Loaded {len(data)} candles")
                        st.session_state["_last_data"] = data
                        st.session_state["_last_fetch_time"] = time.time()
                    except Exception as e:
                        st.error(f"Fetch error: {e}")



    # ── Price Chart ──
    st.subheader("Price Chart")
    with st.container(border=True):
        st.markdown('', unsafe_allow_html=True)
        data = st.session_state.get("_last_data")
        if data is not None:
            candle_opts = [50, 100, 200, 500, 1000, len(data)]
            candle_labels = ["50", "100", "200", "500", "1000", f"All ({len(data)})"]
            show_candles = st.selectbox("Candles", options=list(range(len(candle_opts))),
                                        format_func=lambda i: candle_labels[i], index=2, key="chart_candles")
            limit = candle_opts[show_candles]
            chart_data = data.iloc[-limit:] if limit < len(data) else data

            sma20 = chart_data["close"].rolling(20).mean()
            sma50 = chart_data["close"].rolling(50).mean()
            vol_col = "tick_volume" if "tick_volume" in chart_data.columns else "volume"
            colors = ["#26a69a" if chart_data["close"].iloc[i] >= chart_data["open"].iloc[i] else "#ef5350"
                      for i in range(len(chart_data))]

            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=chart_data.index, open=chart_data["open"], high=chart_data["high"],
                                         low=chart_data["low"], close=chart_data["close"], name="OHLC",
                                         increasing_line_color="#26a69a", decreasing_line_color="#ef5350", showlegend=False))
            fig.add_trace(go.Scatter(x=chart_data.index, y=sma20, name="SMA 20", line=dict(color="#ffa726", width=1.5)))
            fig.add_trace(go.Scatter(x=chart_data.index, y=sma50, name="SMA 50", line=dict(color="#42a5f5", width=1.5)))
            fig.add_trace(go.Bar(x=chart_data.index, y=chart_data[vol_col], name="Volume",
                                 marker_color=colors, opacity=0.4, yaxis="y2", showlegend=False))
            fig.update_layout(height=500,
                              xaxis=dict(rangeslider=dict(visible=True, thickness=0.08), type="date"),
                              yaxis=dict(title="Price ($)", domain=[0.25, 1.0]),
                              yaxis2=dict(title="Volume", domain=[0.0, 0.2], showgrid=False),
                              legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center"),
                              margin=dict(l=50, r=20, t=30, b=50), hovermode="x unified",
                              template="plotly_dark", dragmode="zoom")
            st.plotly_chart(fig, use_container_width=True)

            qs = st.columns(5)
            last_close = chart_data["close"].iloc[-1]
            prev_close = chart_data["close"].iloc[-2]
            change = last_close - prev_close
            chg_pct = change / prev_close * 100
            with qs[0]:
                st.metric("Current", f"${last_close:.2f}", delta=f"{change:.2f} ({chg_pct:.2f}%)")
            with qs[1]:
                st.metric("Open", f"${chart_data['open'].iloc[-1]:.2f}")
            with qs[2]:
                st.metric("High", f"${chart_data['high'].iloc[-1]:.2f}")
            with qs[3]:
                st.metric("Low", f"${chart_data['low'].iloc[-1]:.2f}")
            with qs[4]:
                vol_val = chart_data["close"].pct_change().std() * 100
                st.metric("Volatility", f"{vol_val:.3f}%")
        else:
            st.info("Click 'Refresh Data' to load market data")

    # ── Market Analysis ──
    st.subheader("Market Analysis")
    with st.container(border=True):
        st.markdown('', unsafe_allow_html=True)
        if data is not None:
            ca, cb = st.columns(2)
            with ca:
                regime = robot.detect_regime(data)
                robot.current_regime = regime
                set_shared("regime", regime)
                colors_map = {"trending": "green", "ranging": "orange", "choppy": "red"}
                c = colors_map.get(regime.lower(), "gray")
                st.markdown(f"### Regime: <span style='color:{c}'>{regime.upper()}</span>", unsafe_allow_html=True)
            with cb:
                with st.spinner("Running backtest..."):
                    results = robot.run_backtest_all(data)
                    st.session_state.backtest_results = results
                name = robot.best_strategy.name if robot.best_strategy else "N/A"
                set_shared("best_strategy", name)
                st.markdown(f"### Best Strategy: **{name}**")


        else:
            st.info("Fetch data to see market analysis")
