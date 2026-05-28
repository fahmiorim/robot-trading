import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from dashboard.helpers import ensure_mt5, refresh_robot
from src.controllers.dashboard_controller import DashboardController


def render():
    st.title("📈 Backtest & Hyperopt")
    config = st.session_state.config
    robot = st.session_state.robot
    results = st.session_state.backtest_results or {}

    # ── Controls ──
    tab_backtest, tab_hyperopt, tab_advanced = st.tabs(["▶️ Backtest", "🧬 Hyperopt", "📊 Advanced Analyzers"])

    with tab_backtest:
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
            st.subheader("📊 Performance Summary")
            best_name = max(results.keys(), key=lambda k: results[k]['total_return'])
            best = results[best_name]
            m1, m2, m3, m4, m5 = st.columns(5)
            with m1:
                st.metric("Best Strategy", best_name)
            with m2:
                st.metric("Return", f"{best['total_return']:.2f}%")
            with m3:
                st.metric("Trades", sum(r['num_trades'] for r in results.values()))
            with m4:
                st.metric("Avg Return", f"{sum(r['total_return'] for r in results.values()) / len(results):.2f}%")
            with m5:
                avg_sharpe = sum(r.get('sharpe_ratio', 0) for r in results.values()) / len(results)
                st.metric("Avg Sharpe", f"{avg_sharpe:.2f}")

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

    # ═══ TAB: ADVANCED ANALYZERS (inspired by Backtrader) ═══
    with tab_advanced:
        if not results:
            st.info("💡 Run a backtest first to see advanced analytics.")
        else:
            st.markdown("""
            <div class="info-banner" style="border-color: rgba(139,92,246,0.15);">
                <div class="title">🧠 Advanced Analyzers</div>
                <div class="desc">Sortino Ratio • Calmar Ratio • Profit Factor • Streaks • Time in Market • Monthly Returns</div>
            </div>
            """, unsafe_allow_html=True)

            selected_strat = st.selectbox("Pilih Strategy", list(results.keys()), key="adv_strat_select")
            r = results[selected_strat]

            # ── Ratios & Annualised Metrics ──
            aa1, aa2, aa3, aa4, aa5, aa6 = st.columns(6)
            with aa1:
                sortino = r.get('sortino_ratio', 0)
                sharpe = r.get('sharpe_ratio', 0)
                st.metric("Sortino Ratio", f"{sortino:.2f}", delta=f"Sharpe: {sharpe:.2f}", delta_color="normal")
            with aa2:
                calmar = r.get('calmar_ratio', 0)
                st.metric("Calmar Ratio", f"{calmar:.2f}", help="Annualised return / Max Drawdown")
            with aa3:
                pf = r.get('profit_factor', 0)
                st.metric("Profit Factor", f"{pf:.2f}", delta="Good > 1.5" if pf > 1.5 else "Poor < 1.0" if pf < 1.0 else "OK",
                         delta_color="normal" if pf > 1.0 else "inverse")
            with aa4:
                cagr = r.get('cagr_pct', 0)
                st.metric("CAGR %", f"{cagr:.2f}%", help="Compound Annual Growth Rate")
            with aa5:
                sqn = r.get('sqn', 0)
                sqn_qual = "Excellent" if sqn > 3 else "Good" if sqn > 2 else "Poor"
                st.metric("SQN", f"{sqn:.2f}", delta=sqn_qual, delta_color="normal" if sqn > 2 else "inverse")
            with aa6:
                exp_pct = r.get('expectancy_pct', 0)
                st.metric("Expectancy %", f"{exp_pct:.3f}%", help="Expected return per trade as % of balance")

            # ── Streaks, Expectancy Ratio & Averages ──
            aa7, aa8, aa9, aa10, aa11, aa12 = st.columns(6)
            with aa7:
                _aw = r.get('avg_win_pct', 0)
                _al = r.get('avg_loss_pct', 0)
                awr = _aw / abs(_al) if _al != 0 else 0
                st.metric("Avg Win/Loss", f"{awr:.2f}", help="Average winning trade % / Average losing trade %")
            with aa8:
                exp_ratio = r.get('expectancy_ratio', 0)
                st.metric("Expectancy Ratio", f"{exp_ratio:.2f}", help="Avg Win / |Avg Loss| — > 1 = good")
            with aa9:
                st.metric("Longest Win Streak", f"{r.get('longest_win_streak', 0)}")
            with aa10:
                st.metric("Longest Loss Streak", f"{r.get('longest_loss_streak', 0)}")
            with aa11:
                st.metric("Avg Win %", f"{r.get('avg_win_pct', 0):.1f}%")
            with aa12:
                st.metric("Avg Loss %", f"{r.get('avg_loss_pct', 0):.1f}%")

            # ── Current Streaks (smaller, info row) ──
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
                mdf['color'] = mdf['return'].apply(lambda x: '#26a69a' if x > 0 else '#ef5350')
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
            st.markdown("### 📊 Trade Statistics")
            trades_list = r.get('trades', [])
            if trades_list:
                tdf = pd.DataFrame(trades_list)
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Total Trades", f"{r.get('num_trades', 0)}")
                    wins = sum(1 for t in trades_list if t.get('profit_pct', 0) > 0)
                    losses = sum(1 for t in trades_list if t.get('profit_pct', 0) < 0)
                    st.metric("Winning Trades", f"{wins}")
                    st.metric("Losing Trades", f"{losses}")
                with c2:
                    st.metric("Win Rate", f"{r.get('win_rate', 0):.1f}%")
                    st.metric("Max Drawdown", f"{r.get('max_drawdown', 0):.2f}%")
                    st.metric("Time in Market", f"{r.get('time_in_market_pct', 0):.1f}%")

            # ── Radar Chart ──
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
                    radialaxis=dict(visible=True, range=[0, 10],
                                    gridcolor='rgba(255,255,255,0.1)'),
                    bgcolor='rgba(0,0,0,0)',
                ),
                height=400,
                template='plotly_dark',
                margin=dict(l=60, r=30, t=10, b=30),
            )
            st.plotly_chart(fig_radar, width='stretch')

    # ═══ TAB: HYPEROPT ═══
    with tab_hyperopt:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(255,167,38,0.08), rgba(255,167,38,0.02)); border: 1px solid rgba(255,167,38,0.12); border-radius: 12px; padding: 0.8rem 1rem; margin-bottom: 1rem;">
            <div style="font-size: 0.8rem; font-weight: 600; color: #ffa726;">🧬 Hyperopt Engine</div>
            <div style="font-size: 0.7rem; opacity: 0.5;">Automatic parameter optimization — random search → TPE-inspired refinement</div>
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
                    # Single strategy
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

                st.session_state.hyperopt_results = ho_results
                st.session_state.hyperopt_running = False
                st.rerun()

            # ── Display Hyperopt Results ──
            ho_results = st.session_state.hyperopt_results
            if ho_results:
                st.markdown("---")
                st.subheader("🏆 Hyperopt Results")

                # Summary row
                ho_summary_cols = st.columns(4)
                with ho_summary_cols[0]:
                    best_sid = max(ho_results.keys(), key=lambda k: ho_results[k]['score'])
                    st.metric("Best Strategy", best_sid)
                with ho_summary_cols[1]:
                    best_score = ho_results[best_sid]['score']
                    st.metric("Best Score", f"{best_score:.2f}")
                with ho_summary_cols[2]:
                    total_trials = sum(r['n_trials'] for r in ho_results.values())
                    st.metric("Total Trials", f"{total_trials}")
                with ho_summary_cols[3]:
                    total_time = sum(r['elapsed'] for r in ho_results.values())
                    st.metric("Total Time", f"{total_time:.1f}s")

                # Per-strategy detail
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

                        # Apply to config button
                        if st.button(f"📥 Apply {sid} Params to Config", key=f"ho_apply_{sid}"):
                            for k, v in hresult['params'].items():
                                config.set('strategies', sid, k, v)
                            config.save()
                            refresh_robot(config)
                            st.success(f"✅ {sid} params applied to config and robot reloaded!")
                            st.rerun()

                # Apply all button
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

            # Previous runs from DB
            st.markdown("---")
            with st.expander("📚 Previous Hyperopt Runs (from Database)"):
                try:
                    dc = st.session_state.get("dashboard_ctrl", DashboardController())
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

