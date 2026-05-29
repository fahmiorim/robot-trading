"""Performance Analytics page — actual trade history, backtesting, advanced stats, hyperopt."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import time

from dashboard.helpers import ensure_mt5, refresh_robot
from dashboard.components import render_trade_metrics
from src.exchange.helpers import get_trade_history
from src.controllers.dashboard_controller import DashboardController


def render():
    st.title("📊 Performance & Analytics")
    config = st.session_state.config
    robot = st.session_state.robot
    results = st.session_state.backtest_results or {}
    dc = st.session_state.get("dashboard_ctrl", DashboardController())

    tab_labels = ["📜 Trade History", "▶️ Backtest Simulation", "📊 Advanced Analyzers", "🧬 Parameter Hyperopt"]
    tabs = st.tabs(tab_labels)

    # ── TAB 1: TRADE HISTORY ──
    with tabs[0]:
        st.markdown("### 📜 Real Trade History")
        days = st.slider("Select History Range (Days)", 1, 365, 30)
        source = st.radio("History Source", ["🤖 Robot Database", "📊 MT5 Platform"], horizontal=True)

        try:
            if source == "🤖 Robot Database":
                history = dc.get_trade_history(limit=500)
                if history:
                    df = pd.DataFrame(history)
                    st.dataframe(df, width='stretch', hide_index=True)
                    render_trade_metrics(df, profit_col="profit")

                    summary = dc.get_trade_summary(days)
                    if summary:
                        st.markdown("<h4 style='margin:12px 0 4px; font-size:1rem; font-weight:700; color:#a5b4fc;'>📊 Aggregate Stats</h4>", unsafe_allow_html=True)
                        tot = int(summary.get('total_trades', 0))
                        opn = int(summary.get('open_trades', 0))
                        pnl = float(summary.get('total_profit', 0))
                        wr  = float(summary.get('win_rate', 0))
                        pnl_color = "#10b981" if pnl >= 0 else "#ef4444"
                        pnl_sign  = "+" if pnl >= 0 else ""
                        st.markdown(f"""
                        <div style="font-family:'Outfit',sans-serif; display:flex; justify-content:space-between;
                             align-items:center; background:rgba(255,255,255,0.02); padding:10px 16px;
                             border-radius:8px; border:1px solid rgba(255,255,255,0.05); margin:4px 0 12px;">
                            <div style="flex:1; text-align:center;">
                                <div style="font-size:0.62rem; opacity:0.5; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">TOTAL TRADES</div>
                                <div style="font-size:0.9rem; font-weight:800; color:#ffffff;">{tot}</div>
                            </div>
                            <div style="width:1px; height:22px; background:rgba(255,255,255,0.08);"></div>
                            <div style="flex:1; text-align:center;">
                                <div style="font-size:0.62rem; opacity:0.5; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">OPEN TRADES</div>
                                <div style="font-size:0.9rem; font-weight:800; color:#a5b4fc;">{opn}</div>
                            </div>
                            <div style="width:1px; height:22px; background:rgba(255,255,255,0.08);"></div>
                            <div style="flex:1; text-align:center;">
                                <div style="font-size:0.62rem; opacity:0.5; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">TOTAL P&L</div>
                                <div style="font-size:0.9rem; font-weight:800; color:{pnl_color};">{pnl_sign}${pnl:.2f}</div>
                            </div>
                            <div style="width:1px; height:22px; background:rgba(255,255,255,0.08);"></div>
                            <div style="flex:1; text-align:center;">
                                <div style="font-size:0.62rem; opacity:0.5; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">WIN RATE</div>
                                <div style="font-size:0.9rem; font-weight:800; color:#f59e0b;">{wr:.1f}%</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No trade history in database")
            else:
                if ensure_mt5():
                    history_raw = get_trade_history(days)
                    if history_raw is not None and len(history_raw) > 0:
                        # history_raw is List[Dict] — konversi ke DataFrame
                        history = pd.DataFrame(history_raw) if isinstance(history_raw, list) else history_raw
                        st.dataframe(history, width='stretch')
                        profit_col = next((c for c in ['profit', 'Profit', 'pnl', 'P&L'] if c in history.columns), None)
                        if profit_col:
                            render_trade_metrics(history, profit_col=profit_col)
                        else:
                            st.info("No profit column found in MT5 data")
                    else:
                        st.info("No trade history found from MT5")
                else:
                    st.warning("MT5 not connected")
        except Exception as e:
            st.error(f"Error loading trade history: {e}")

    # ── TAB 2: BACKTEST SIMULATION ──
    with tabs[1]:
        st.markdown("### ▶️ Historical Backtester")
        bt1, bt2 = st.columns([1, 3])
        with bt1:
            if st.button("▶️ Run Full Backtest", width='stretch', type="primary"):
                with st.spinner("Running backtest..."):
                    try:
                        data = st.session_state.get("_last_data")
                        if data is None:
                            if not ensure_mt5():
                                st.stop()
                            data = robot.fetch_data()
                        results = robot.run_backtest_all(data)
                        st.session_state.backtest_results = results
                        st.success("Complete!")
                    except Exception as e:
                        st.error(f"Backtest error: {e}")
        with bt2:
            if st.button("📥 Fetch & Backtest", width='stretch'):
                with st.spinner("Fetching & backtesting..."):
                    try:
                        if not ensure_mt5():
                            st.stop()
                        data = robot.fetch_data()
                        st.session_state["_last_data"] = data
                        results = robot.run_backtest_all(data)
                        st.session_state.backtest_results = results
                        st.success(f"Loaded {len(data)} candles, backtest done!")
                    except Exception as e:
                        st.error(f"Error: {e}")

        if not results:
            st.info("💡 No results yet. Click **Run Full Backtest** or **Fetch & Backtest**.")
        else:
            st.markdown("<h4 style='margin:8px 0 4px; font-size:1rem; font-weight:700; color:#a5b4fc;'>📊 Performance Summary</h4>", unsafe_allow_html=True)
            best_name = max(results.keys(), key=lambda k: results[k]['total_return'])
            best = results[best_name]
            _tot_trades = sum(r['num_trades'] for r in results.values())
            _avg_ret = sum(r['total_return'] for r in results.values()) / len(results)
            avg_sharpe = sum(r.get('sharpe_ratio', 0) for r in results.values()) / len(results)
            _ret_color = '#10b981' if best['total_return'] >= 0 else '#ef4444'
            _avg_color = '#10b981' if _avg_ret >= 0 else '#ef4444'
            st.markdown(f"""
            <div style="font-family:'Outfit',sans-serif; display:flex; justify-content:space-between;
                 align-items:center; background:rgba(255,255,255,0.02); padding:10px 16px;
                 border-radius:8px; border:1px solid rgba(255,255,255,0.05); margin:4px 0 12px;">
                <div style="flex:2; text-align:center;">
                    <div style="font-size:0.62rem; opacity:0.5; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">BEST STRATEGY</div>
                    <div style="font-size:0.85rem; font-weight:800; color:#ffffff;">{best_name}</div>
                </div>
                <div style="width:1px; height:22px; background:rgba(255,255,255,0.08);"></div>
                <div style="flex:1; text-align:center;">
                    <div style="font-size:0.62rem; opacity:0.5; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">RETURN</div>
                    <div style="font-size:0.85rem; font-weight:800; color:{_ret_color};">{best['total_return']:.2f}%</div>
                </div>
                <div style="width:1px; height:22px; background:rgba(255,255,255,0.08);"></div>
                <div style="flex:1; text-align:center;">
                    <div style="font-size:0.62rem; opacity:0.5; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">TRADES</div>
                    <div style="font-size:0.85rem; font-weight:800; color:#ffffff;">{_tot_trades}</div>
                </div>
                <div style="width:1px; height:22px; background:rgba(255,255,255,0.08);"></div>
                <div style="flex:1; text-align:center;">
                    <div style="font-size:0.62rem; opacity:0.5; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">AVG RETURN</div>
                    <div style="font-size:0.85rem; font-weight:800; color:{_avg_color};">{_avg_ret:.2f}%</div>
                </div>
                <div style="width:1px; height:22px; background:rgba(255,255,255,0.08);"></div>
                <div style="flex:1; text-align:center;">
                    <div style="font-size:0.62rem; opacity:0.5; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">AVG SHARPE</div>
                    <div style="font-size:0.85rem; font-weight:800; color:#a5b4fc;">{avg_sharpe:.2f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.subheader("📋 Strategy Comparison")
            rows = []
            for n, r in results.items():
                rows.append({
                    "Strategy": n, "Return %": f"{r['total_return']:.2f}%",
                    "Final": f"${r['final_balance']:,.2f}", "Trades": r['num_trades'],
                    "Win Rate": f"{r.get('win_rate', 0):.1f}%",
                    "Max DD": f"{r.get('max_drawdown', 0):.2f}%",
                    "Sharpe": f"{r.get('sharpe_ratio', 0):.2f}",
                    "Sortino": f"{r.get('sortino_ratio', 0):.2f}",
                    "Calmar": f"{r.get('calmar_ratio', 0):.2f}",
                    "Profit Factor": f"{r.get('profit_factor', 1):.2f}",
                })
            st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

            st.subheader("📈 Equity Curves")
            fig = go.Figure()
            for name, r in results.items():
                eq = r.get('equity_curve', [])
                if eq:
                    fig.add_trace(go.Scatter(y=eq, name=name, mode='lines', line=dict(width=1.5)))
            fig.update_layout(height=400, xaxis_title="Step", yaxis_title="Equity ($)", hovermode='x unified')
            st.plotly_chart(fig, width='stretch')

            st.subheader(f"📝 Trades: {best_name}")
            trades = best.get('trades', [])
            if trades:
                tdf = pd.DataFrame(trades)
                st.dataframe(tdf, width='stretch', hide_index=True)
                if 'profit_pct' in tdf.columns:
                    fig2 = px.histogram(tdf, x='profit_pct', nbins=30, title="P&L Distribution",
                                        labels={'profit_pct': 'Profit %'})
                    st.plotly_chart(fig2, width='stretch')
            else:
                st.info("No trades recorded")

    # ── TAB 3: ADVANCED ANALYZERS ──
    with tabs[2]:
        if not results:
            st.info("💡 Run a backtest first in the Backtest tab to see advanced analytics.")
        else:
            st.markdown("""
            <div class="info-banner" style="border-color: rgba(99,102,241,0.15);">
                <div class="title">🧠 Advanced Analyzers</div>
                <div class="desc">Sortino Ratio • Calmar Ratio • Profit Factor • Streaks • Time in Market • Monthly Returns</div>
            </div>
            """, unsafe_allow_html=True)

            selected_strat = st.selectbox("Pilih Strategy", list(results.keys()), key="adv_strat_select")
            r = results[selected_strat]

            # Ratios & Annualised Metrics
            sortino = r.get('sortino_ratio', 0)
            sharpe  = r.get('sharpe_ratio', 0)
            calmar  = r.get('calmar_ratio', 0)
            pf      = r.get('profit_factor', 0)
            cagr    = r.get('cagr_pct', 0)
            sqn     = r.get('sqn', 0)
            exp_pct = r.get('expectancy_pct', 0)
            _aw = r.get('avg_win_pct', 0)
            _al = r.get('avg_loss_pct', 0)
            awr = _aw / abs(_al) if _al != 0 else 0
            exp_ratio = r.get('expectancy_ratio', 0)
            pf_color  = '#10b981' if pf > 1.5 else '#ef4444' if pf < 1.0 else '#f59e0b'
            sqn_color = '#10b981' if sqn > 2 else '#ef4444'

            def _mbar(*items):
                """Render a horizontal HTML metrics bar from list of (label, value, color) tuples."""
                sep = '<div style="width:1px; height:22px; background:rgba(255,255,255,0.08);"></div>'
                cells = sep.join(f'''
                    <div style="flex:1; text-align:center;">
                        <div style="font-size:0.6rem; opacity:0.5; font-weight:700; text-transform:uppercase;
                             letter-spacing:0.05em; margin-bottom:2px;">{lbl}</div>
                        <div style="font-size:0.85rem; font-weight:800; color:{col};">{val}</div>
                    </div>''' for lbl, val, col in items)
                st.markdown(f'<div style="font-family:\'Outfit\',sans-serif; display:flex; align-items:center; '
                            f'background:rgba(255,255,255,0.02); padding:10px 14px; border-radius:8px; '
                            f'border:1px solid rgba(255,255,255,0.05); margin:4px 0 8px;">{cells}</div>',
                            unsafe_allow_html=True)

            _mbar(
                ("SORTINO",      f"{sortino:.2f}",   '#10b981' if sortino > 1 else '#ef4444'),
                ("SHARPE",       f"{sharpe:.2f}",    '#10b981' if sharpe > 1 else '#ef4444'),
                ("CALMAR",       f"{calmar:.2f}",    '#10b981' if calmar > 0.5 else '#f59e0b'),
                ("PROFIT FACTOR",f"{pf:.2f}",        pf_color),
                ("CAGR %",       f"{cagr:.2f}%",     '#10b981' if cagr > 0 else '#ef4444'),
                ("SQN",          f"{sqn:.2f}",        sqn_color),
                ("EXPECTANCY %", f"{exp_pct:.3f}%",  '#a5b4fc'),
            )
            _mbar(
                ("AVG WIN/LOSS",      f"{awr:.2f}",                           '#10b981' if awr > 1 else '#ef4444'),
                ("EXPECTANCY RATIO",  f"{exp_ratio:.2f}",                     '#10b981' if exp_ratio > 1 else '#f59e0b'),
                ("WIN STREAK",        f"{r.get('longest_win_streak', 0)}",    '#10b981'),
                ("LOSS STREAK",       f"{r.get('longest_loss_streak', 0)}",   '#ef4444'),
                ("AVG WIN %",         f"{r.get('avg_win_pct', 0):.1f}%",      '#10b981'),
                ("AVG LOSS %",        f"{r.get('avg_loss_pct', 0):.1f}%",     '#ef4444'),
            )

            cur_w = r.get('current_win_streak', 0)
            cur_l = r.get('current_loss_streak', 0)
            if cur_w > 0 or cur_l > 0:
                st.caption(f"📌 Current streaks: 🟢 {cur_w} win / 🔴 {cur_l} loss")

            st.markdown("---")
            st.markdown("### 📅 Monthly Returns")
            monthly = r.get('monthly_returns', [])
            is_df = isinstance(monthly, pd.DataFrame)
            if monthly is not None and (not monthly.empty if is_df else len(monthly) > 0):
                mdf = pd.DataFrame(monthly)
                if 'profit' in mdf.columns and 'return' not in mdf.columns:
                    init_bal = r.get('initial_balance', config.get('backtest', 'initial_balance'))
                    mdf['return'] = (mdf['profit'] / init_bal) * 100
                elif 'return' not in mdf.columns:
                    mdf['return'] = 0.0
                mdf['color'] = mdf['return'].apply(lambda x: '#10b981' if x > 0 else '#ef4444')
                fig_m = go.Figure()
                fig_m.add_trace(go.Bar(
                    x=mdf['month'], y=mdf['return'],
                    marker_color=mdf['color'],
                    text=mdf['return'].apply(lambda x: f"{x:.1f}%"),
                    textposition='outside',
                ))
                fig_m.update_layout(
                    height=300,
                    title="Monthly Return %",
                    yaxis_title="Return %",
                    hovermode='x unified',
                    template='plotly_dark',
                )
                st.plotly_chart(fig_m, width='stretch')
            else:
                st.info("Monthly data not available (no datetime index or no trades)")

            st.markdown("---")
            st.markdown("### 🎯 Strategy Quality Radar")
            radar_categories = ['Return', 'Sharpe', 'Sortino', 'Win Rate', 'Profit Factor', 'Calmar']
            radar_values = [
                min(r.get('total_return', 0) / 20, 10),  # normalized to 0-10
                min(max(r.get('sharpe_ratio', 0) + 2, 0), 10),
                min(max(r.get('sortino_ratio', 0) + 2, 0), 10),
                r.get('win_rate', 0) / 10,
                min(r.get('profit_factor', 0) * 2, 10),
                min(max(r.get('calmar_ratio', 0), 0), 10),
            ]
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=radar_values + [radar_values[0]],
                theta=radar_categories + [radar_categories[0]],
                fill='toself',
                name=selected_strat,
                line=dict(color='#b388ff', width=2),
                fillcolor='rgba(179,136,255,0.15)',
            ))
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 10], gridcolor='rgba(255,255,255,0.1)'),
                    bgcolor='rgba(0,0,0,0)',
                ),
                height=400,
                template='plotly_dark',
                margin=dict(l=60, r=30, t=10, b=30),
            )
            st.plotly_chart(fig_radar, width='stretch')

    # ── TAB 4: PARAMETER OPTIMIZER ──
    with tabs[3]:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(99,102,241,0.08), rgba(99,102,241,0.02)); border: 1px solid rgba(99,102,241,0.12); border-radius: 12px; padding: 0.8rem 1rem; margin-bottom: 1rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #a5b4fc;">🧬 Hyperopt Engine</div>
            <div style="font-size: 0.72rem; opacity: 0.55;">Automatic parameter optimization — random search → refinement</div>
        </div>
        """, unsafe_allow_html=True)

        if "hyperopt_running" not in st.session_state:
            st.session_state.hyperopt_running = False
        if "hyperopt_results" not in st.session_state:
            st.session_state.hyperopt_results = {}

        data = st.session_state.get("_last_data")
        if data is None:
            st.warning("⚠️ Fetch market data first on the Dashboard page")
        else:
            ho1, ho2, ho3 = st.columns([1, 1, 2])
            with ho1:
                ho_strategy = st.selectbox(
                    "🎯 Strategy",
                    ["All", "MA_Crossover", "RSI", "MACD", "Bollinger", "Breakout"],
                    key="ho_strategy"
                )
            with ho2:
                ho_trials = st.number_input(
                    "🔄 Trials", 20, 500, 100, 20,
                    key="ho_trials",
                    help="More trials = better results but slower"
                )
            with ho3:
                st.markdown("<br>", unsafe_allow_html=True)
                disabled = st.session_state.hyperopt_running
                if st.button("🧬 RUN HYPEROPT", width='stretch', type="primary", disabled=disabled):
                    st.session_state.hyperopt_running = True
                    st.rerun()

            if st.session_state.hyperopt_running:
                from src.backtesting.hyperopt import HyperoptEngine
                from src.strategy.interface import IStrategy as BaseStrategy
                from src.backtesting.engine import Backtester

                engine = HyperoptEngine(config, Backtester(config))
                ho_results = {}

                if ho_strategy == "All":
                    registry = BaseStrategy.get_registry()
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    for idx, (sid, strat_cls) in enumerate(registry.items()):
                        if not hasattr(strat_cls, 'param_space') or not strat_cls.param_space:
                            continue
                        status_text.info(f"🧬 Optimizing {sid}... ({idx + 1}/{len(registry)})")
                        try:
                            result = engine.optimize(strat_cls, data, n_trials=max(20, ho_trials // len(registry)))
                            ho_results[sid] = {
                                'params': result.best_params,
                                'score': result.best_score,
                                'metrics': result.best_results,
                                'n_trials': len(result.trials),
                                'elapsed': result.total_elapsed,
                            }
                        except Exception as e:
                            st.error(f"{sid} hyperopt failed: {e}")
                        progress_bar.progress((idx + 1) / len(registry))

                    status_text.success("✅ All strategies optimized!")
                else:
                    registry = BaseStrategy.get_registry()
                    if ho_strategy in registry:
                        strat_cls = registry[ho_strategy]
                        if hasattr(strat_cls, 'param_space') and strat_cls.param_space:
                            with st.spinner(f"🧬 Optimizing {ho_strategy}..."):
                                result = engine.optimize(strat_cls, data, n_trials=ho_trials)
                                ho_results[ho_strategy] = {
                                    'params': result.best_params,
                                    'score': result.best_score,
                                    'metrics': result.best_results,
                                    'n_trials': len(result.trials),
                                    'elapsed': result.total_elapsed,
                                }
                        else:
                            st.error(f"{ho_strategy} has no param_space defined")
                    else:
                        st.error(f"Strategy '{ho_strategy}' not found in registry")

                st.session_state.ho_results = ho_results
                st.session_state.hyperopt_running = False
                st.rerun()

            ho_results = st.session_state.get("ho_results", {})
            if ho_results:
                st.markdown("---")
                st.subheader("🏆 Hyperopt Results")

                best_sid     = max(ho_results.keys(), key=lambda k: ho_results[k]['score'])
                best_score   = ho_results[best_sid]['score']
                total_trials = sum(r['n_trials'] for r in ho_results.values())
                total_time   = sum(r['elapsed'] for r in ho_results.values())
                st.markdown(f"""
                <div style="font-family:'Outfit',sans-serif; display:flex; align-items:center;
                     background:rgba(255,255,255,0.02); padding:10px 16px; border-radius:8px;
                     border:1px solid rgba(255,255,255,0.05); margin:4px 0 12px;">
                    <div style="flex:2; text-align:center;">
                        <div style="font-size:0.62rem; opacity:0.5; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">BEST STRATEGY</div>
                        <div style="font-size:0.85rem; font-weight:800; color:#ffffff;">{best_sid}</div>
                    </div>
                    <div style="width:1px; height:22px; background:rgba(255,255,255,0.08);"></div>
                    <div style="flex:1; text-align:center;">
                        <div style="font-size:0.62rem; opacity:0.5; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">BEST SCORE</div>
                        <div style="font-size:0.85rem; font-weight:800; color:#10b981;">{best_score:.2f}</div>
                    </div>
                    <div style="width:1px; height:22px; background:rgba(255,255,255,0.08);"></div>
                    <div style="flex:1; text-align:center;">
                        <div style="font-size:0.62rem; opacity:0.5; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">TOTAL TRIALS</div>
                        <div style="font-size:0.85rem; font-weight:800; color:#a5b4fc;">{total_trials}</div>
                    </div>
                    <div style="width:1px; height:22px; background:rgba(255,255,255,0.08);"></div>
                    <div style="flex:1; text-align:center;">
                        <div style="font-size:0.62rem; opacity:0.5; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">TOTAL TIME</div>
                        <div style="font-size:0.85rem; font-weight:800; color:#f59e0b;">{total_time:.1f}s</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                for sid, hresult in ho_results.items():
                    with st.expander(f"🧬 {sid} — Score: {hresult['score']:.2f}", expanded=True):
                        cols = st.columns([1, 1])
                        with cols[0]:
                            st.markdown("**Best Params:**")
                            st.json(hresult['params'])
                        with cols[1]:
                            st.markdown("**Metrics:**")
                            m = hresult.get('metrics', {})
                            for k in ['total_return', 'sharpe_ratio', 'sortino_ratio',
                                       'calmar_ratio', 'profit_factor', 'win_rate', 'max_drawdown']:
                                v = m.get(k, 0)
                                st.markdown(f"- **{k}:** {v:.2f}")

                        if st.button(f"📥 Apply {sid} Params to Config", key=f"ho_apply_{sid}"):
                            for k, v in hresult['params'].items():
                                config.set('strategies', sid, k, v)
                            config.save()
                            refresh_robot(config)
                            st.success(f"✅ {sid} params applied to config and robot reloaded!")
                            st.rerun()

                st.markdown("---")
                if st.button("📥 Apply ALL Best Params to Config", width='stretch', type="primary"):
                    for sid, hresult in ho_results.items():
                        for k, v in hresult['params'].items():
                            config.set('strategies', sid, k, v)
                    config.save()
                    refresh_robot(config)
                    st.success("✅ All params applied!")
                    st.rerun()
            else:
                if not st.session_state.hyperopt_running:
                    st.info("💡 Click **RUN HYPEROPT** to start parameter optimization")

            st.markdown("---")
            with st.expander("📚 Previous Hyperopt Runs (from Database)"):
                try:
                    prev_runs = dc.get_all_hyperopt_results()
                    if prev_runs:
                        for row in prev_runs:
                            st.markdown(f"**{row['strategy_name']}** — Score: {row['best_score']:.2f}, "
                                       f"Trials: {row['n_trials']}, "
                                       f"Time: {row.get('elapsed_seconds', 0):.1f}s")
                            if row.get('best_params'):
                                st.json(row['best_params'])
                            st.markdown("---")
                    else:
                        st.info("No previous hyperopt runs found in DB")
                except Exception as e:
                    st.info(f"Could not load from DB: {e}")
