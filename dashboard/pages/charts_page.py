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
        cc = st.columns([2, 2, 2, 1.5], vertical_alignment="bottom")
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
        data = st.session_state.get("_last_data")
        if data is not None:
            # Compact title and candle selector bar
            ch_col1, ch_col2 = st.columns([3, 1], vertical_alignment="bottom")
            with ch_col1:
                st.markdown("<h4 style='margin:0 0 10px 0; font-size:1.05rem; font-weight:700; color:#a5b4fc;'>📊 Interactive Market Chart</h4>", unsafe_allow_html=True)
            with ch_col2:
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
            fig.update_layout(height=450,
                              font=dict(family="Outfit, sans-serif", size=11),
                              xaxis=dict(
                                  rangeslider=dict(visible=True, thickness=0.06), 
                                  type="date", 
                                  gridcolor="rgba(255,255,255,0.04)",
                                  zerolinecolor="rgba(255,255,255,0.04)"
                              ),
                              yaxis=dict(
                                  title="Price ($)", 
                                  domain=[0.25, 1.0], 
                                  gridcolor="rgba(255,255,255,0.04)",
                                  zerolinecolor="rgba(255,255,255,0.04)"
                              ),
                              yaxis2=dict(
                                  title="Volume", 
                                  domain=[0.0, 0.2], 
                                  showgrid=False,
                                  zerolinecolor="rgba(255,255,255,0.04)"
                              ),
                              legend=dict(
                                  orientation="h", 
                                  y=1.05, 
                                  x=0.5, 
                                  xanchor="center",
                                  bgcolor="rgba(0,0,0,0)"
                              ),
                              margin=dict(l=40, r=10, t=10, b=10), 
                              hovermode="x unified",
                              template="plotly_dark", 
                              dragmode="zoom",
                              paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

            # Clean HTML/CSS metrics bar
            last_close = chart_data["close"].iloc[-1]
            prev_close = chart_data["close"].iloc[-2]
            change = last_close - prev_close
            chg_pct = change / prev_close * 100
            change_color = "#10b981" if change >= 0 else "#ef4444"
            change_sign = "+" if change >= 0 else ""
            open_val = chart_data['open'].iloc[-1]
            high_val = chart_data['high'].iloc[-1]
            low_val = chart_data['low'].iloc[-1]
            vol_val = chart_data["close"].pct_change().std() * 100

            html_metrics = f"""
            <div style="font-family: 'Outfit', sans-serif; display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.02); padding: 10px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); margin-top: 10px;">
                <div style="flex: 1; text-align: center;">
                    <div style="font-size: 0.62rem; opacity: 0.5; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;">CURRENT</div>
                    <div style="font-size: 0.85rem; font-weight: 800; color: {change_color};">${last_close:.2f} <span style="font-size: 0.7rem; font-weight: 600; margin-left: 2px;">{change_sign}${change:.2f} ({change_sign}{chg_pct:.2f}%)</span></div>
                </div>
                <div style="width: 1px; height: 20px; background: rgba(255,255,255,0.08);"></div>
                <div style="flex: 1; text-align: center;">
                    <div style="font-size: 0.62rem; opacity: 0.5; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;">OPEN</div>
                    <div style="font-size: 0.85rem; font-weight: 700; color: #ffffff;">${open_val:.2f}</div>
                </div>
                <div style="width: 1px; height: 20px; background: rgba(255,255,255,0.08);"></div>
                <div style="flex: 1; text-align: center;">
                    <div style="font-size: 0.62rem; opacity: 0.5; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;">HIGH</div>
                    <div style="font-size: 0.85rem; font-weight: 700; color: #10b981;">${high_val:.2f}</div>
                </div>
                <div style="width: 1px; height: 20px; background: rgba(255,255,255,0.08);"></div>
                <div style="flex: 1; text-align: center;">
                    <div style="font-size: 0.62rem; opacity: 0.5; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;">LOW</div>
                    <div style="font-size: 0.85rem; font-weight: 700; color: #ef4444;">${low_val:.2f}</div>
                </div>
                <div style="width: 1px; height: 20px; background: rgba(255,255,255,0.08);"></div>
                <div style="flex: 1; text-align: center;">
                    <div style="font-size: 0.62rem; opacity: 0.5; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;">VOLATILITY</div>
                    <div style="font-size: 0.85rem; font-weight: 700; color: #a5b4fc;">{vol_val:.3f}%</div>
                </div>
            </div>
            """
            st.markdown(html_metrics, unsafe_allow_html=True)
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
                
                st.markdown(f"""
                <div style="font-family: 'Outfit', sans-serif; background: {c_bg}; border: 1px solid {c_border}; border-radius: 12px; padding: 1.1rem; display: flex; align-items: center; gap: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
                    <div style="font-size: 2.2rem;">🔍</div>
                    <div>
                        <div style="font-size: 0.65rem; opacity: 0.55; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;">MARKET REGIME</div>
                        <div style="font-size: 1.15rem; font-weight: 800; color: {c_text}; text-transform: uppercase; margin-top: 2px;">{regime}</div>
                        <div style="font-size: 0.7rem; opacity: 0.7; margin-top: 4px; line-height: 1.4;">Detects trending, ranging or choppy market conditions.</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with cb:
                with st.spinner("Running backtest..."):
                    results = robot.run_backtest_all(data)
                    st.session_state.backtest_results = results
                name = robot.best_strategy.name if robot.best_strategy else "N/A"
                set_shared("best_strategy", name)
                
                st.markdown(f"""
                <div style="font-family: 'Outfit', sans-serif; background: rgba(99, 102, 241, 0.05); border: 1px solid rgba(99, 102, 241, 0.18); border-radius: 12px; padding: 1.1rem; display: flex; align-items: center; gap: 16px; box-shadow: 0 4px 15px rgba(99, 102, 241, 0.05);">
                    <div style="font-size: 2.2rem; filter: drop-shadow(0 0 10px rgba(99,102,241,0.25));">🏆</div>
                    <div>
                        <div style="font-size: 0.65rem; opacity: 0.55; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; color: #a5b4fc;">RECOMMENDED STRATEGY</div>
                        <div style="font-size: 1.15rem; font-weight: 800; color: #ffffff; margin-top: 2px;">{name}</div>
                        <div style="font-size: 0.7rem; opacity: 0.7; margin-top: 4px; color: #c7d2fe; line-height: 1.4;">Optimized best performer based on walk-forward backtest.</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Fetch data to see market analysis")
