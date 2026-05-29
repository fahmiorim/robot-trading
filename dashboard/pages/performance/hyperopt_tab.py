"""Hyperopt tab for Performance Analytics page."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dashboard.helpers import refresh_robot
from src.controllers.dashboard_controller import DashboardController
from dashboard.pages.performance.helpers import _clean_html, _info_banner, _metrics_bar

def render(config):
    _info_banner("🧬 Parameter Hyperopt",
                 "Optimasi parameter strategi otomatis — random search + refinement untuk "
                 "menemukan kombinasi parameter terbaik tiap strategi.")

    if "hyperopt_running" not in st.session_state:
        st.session_state.hyperopt_running = False
    if "hyperopt_results" not in st.session_state:
        st.session_state.hyperopt_results = {}

    with st.container(border=True):
        col1, col2, col3, col4, col5 = st.columns([1.2, 1.2, 1.0, 1.2, 1.2])
        with col1:
            ho_strategy = st.selectbox(
                "🎯 Strategy", ["All", "MA_Crossover", "RSI", "MACD", "Bollinger", "Breakout"],
                key="ho_strategy",
            )
        with col2:
            from src.constants.timeframes import TIMEFRAME_MAP
            tf_keys = list(TIMEFRAME_MAP.keys())
            default_tf = st.session_state.robot.timeframe
            default_idx = tf_keys.index(default_tf) if default_tf in tf_keys else 1
            ho_tf_label = st.selectbox(
                "⏱️ Timeframe", tf_keys,
                index=default_idx,
                key="ho_timeframe",
                help="Timeframe lilin yang akan diuji."
            )
        with col3:
            ho_candles = st.number_input(
                "🕯️ Candles Count", 500, 50000, 10000, 500,
                key="ho_candles",
                help="Jumlah lilin data historis yang akan digunakan untuk optimasi."
            )
        with col4:
            ho_trials = st.number_input(
                "🔄 Trials", 20, 500, 100, 20, key="ho_trials",
                help="Lebih banyak trials = hasil lebih akurat tetapi lebih lambat",
            )
        with col5:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            ho_opt_risk = st.checkbox(
                "🛡️ Optimasi SL & TP",
                value=False,
                key="ho_opt_risk",
                help="Ikut sertakan Stop Loss dan Take Profit dalam pencarian parameter terbaik"
            )
            disabled = st.session_state.hyperopt_running
            if st.button("🧬 RUN HYPEROPT", width='stretch', type="primary", disabled=disabled):
                st.session_state.hyperopt_running = True
                st.rerun()

    if st.session_state.hyperopt_running:
        from src.data.provider import DataProvider
        ho_tf = st.session_state.get("ho_timeframe", "TIMEFRAME_M5")
        ho_c_count = int(st.session_state.get("ho_candles", 10000))

        with st.spinner(f"🔄 Mengunduh {ho_c_count} candle data market {ho_tf} dari MetaTrader 5..."):
            try:
                local_provider = DataProvider(
                    exchange=st.session_state.robot.exchange,
                    symbol=st.session_state.robot.symbol,
                    timeframe=ho_tf,
                    default_count=ho_c_count
                )
                data = local_provider.fetch(force_refresh=True)
                st.toast(f"✅ Data market {ho_tf} ({len(data)} candle) berhasil diambil!", icon="✅")
            except Exception as e:
                st.error(f"❌ Gagal mengambil data market: {e}")
                st.session_state.hyperopt_running = False
                st.rerun()

        from src.backtesting.hyperopt import HyperoptEngine
        from src.strategy.interface import IStrategy as BaseStrategy
        from src.backtesting.engine import Backtester

        engine = HyperoptEngine(config, Backtester(config))
        ho_results = {}

        if ho_strategy == "All":
            registry = BaseStrategy.get_registry()
            progress_bar = st.progress(0)
            status_text = st.empty()
            realtime_placeholder = st.empty()
            plotly_placeholder = st.empty()

            for idx, (sid, strat_cls) in enumerate(registry.items()):
                if not hasattr(strat_cls, 'param_space') or not strat_cls.param_space:
                    continue
                status_text.info(f"🧬 Mengoptimasi {sid}... ({idx + 1}/{len(registry)})")
                
                def make_callback(strategy_name):
                    history = []
                    def update_ui(current, total, best_score, best_params, current_score=0.0, current_params=None):
                        pct = int((current / total) * 100)
                        
                        history.append({
                            "Trial": current,
                            "Best Score": best_score,
                            "Current Score": current_score
                        })
                        
                        # Format best params
                        best_rows = []
                        for k, v in best_params.items():
                            v_clean = v.item() if hasattr(v, 'item') else v
                            val_str = f"{v_clean:.4f}" if isinstance(v_clean, float) else str(v_clean)
                            best_rows.append(
                                f"<div style='background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.15); padding: 6px; border-radius: 6px; text-align: center;'>"
                                f"<div style='font-size: 0.6rem; opacity: 0.5; text-transform: uppercase;'>{k}</div>"
                                f"<div style='font-size: 0.82rem; font-weight: 700; color: #10b981;'>{val_str}</div>"
                                f"</div>"
                            )
                        best_params_html = "".join(best_rows)
                        
                        # Format current params
                        current_params = current_params or best_params
                        current_rows = []
                        for k, v in current_params.items():
                            v_clean = v.item() if hasattr(v, 'item') else v
                            val_str = f"{v_clean:.4f}" if isinstance(v_clean, float) else str(v_clean)
                            current_rows.append(
                                f"<div style='background: rgba(99, 102, 241, 0.05); border: 1px solid rgba(99, 102, 241, 0.15); padding: 6px; border-radius: 6px; text-align: center;'>"
                                f"<div style='font-size: 0.6rem; opacity: 0.5; text-transform: uppercase;'>{k}</div>"
                                f"<div style='font-size: 0.82rem; font-weight: 700; color: #a5b4fc;'>{val_str}</div>"
                                f"</div>"
                            )
                        current_params_html = "".join(current_rows)
                        
                        html = f"""
                        <div style="
                            background: rgba(17, 25, 40, 0.75);
                            backdrop-filter: blur(12px);
                            -webkit-backdrop-filter: blur(12px);
                            border: 1px solid rgba(255, 255, 255, 0.1);
                            border-radius: 16px;
                            padding: 20px;
                            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                            margin-bottom: 20px;
                            background-image: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(168, 85, 247, 0.05) 100%);
                            font-family: 'Outfit', sans-serif;
                        ">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: #a855f7; box-shadow: 0 0 10px #a855f7;"></span>
                                    <span style="font-size: 0.95rem; font-weight: 800; color: #e0e7ff; letter-spacing: 0.05em; text-transform: uppercase;">
                                        🧬 OPTIMIZING {strategy_name}
                                    </span>
                                </div>
                                <span style="font-size: 0.75rem; font-weight: 700; color: #fbbf24; background: rgba(251, 191, 36, 0.1); padding: 4px 10px; border-radius: 20px; border: 1px solid rgba(251, 191, 36, 0.2);">
                                    Trial {current} / {total}
                                </span>
                            </div>
                            
                            <!-- Glowing Progress Bar -->
                            <div style="width: 100%; background-color: rgba(255, 255, 255, 0.05); border-radius: 10px; height: 6px; margin-bottom: 16px; overflow: hidden; border: 1px solid rgba(255,255,255,0.05);">
                                <div style="width: {pct}%; background: linear-gradient(90deg, #6366f1 0%, #a855f7 100%); height: 100%; border-radius: 10px; box-shadow: 0 0 12px #a855f7;"></div>
                            </div>
                            
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                                <!-- Left Column: Best So Far -->
                                <div style="background: rgba(16, 185, 129, 0.02); border: 1px solid rgba(16, 185, 129, 0.1); border-radius: 10px; padding: 12px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <span style="font-size: 0.68rem; color: #9ca3af; font-weight: 700; text-transform: uppercase;">🏆 Best So Far</span>
                                        <span style="font-size: 0.85rem; font-weight: 800; color: #10b981;">{best_score:.4f}</span>
                                    </div>
                                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(70px, 1fr)); gap: 6px;">
                                        {best_params_html}
                                    </div>
                                </div>
                                
                                <!-- Right Column: Current Trial -->
                                <div style="background: rgba(99, 102, 241, 0.02); border: 1px solid rgba(99, 102, 241, 0.1); border-radius: 10px; padding: 12px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <span style="font-size: 0.68rem; color: #9ca3af; font-weight: 700; text-transform: uppercase;">⚡ Testing Current</span>
                                        <span style="font-size: 0.85rem; font-weight: 800; color: #a5b4fc;">{current_score:.4f}</span>
                                    </div>
                                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(70px, 1fr)); gap: 6px;">
                                        {current_params_html}
                                    </div>
                                </div>
                            </div>
                        </div>
                        """
                        realtime_placeholder.markdown(_clean_html(html), unsafe_allow_html=True)
                        
                        # Plot convergence
                        trials = [h["Trial"] for h in history]
                        best_scores = [h["Best Score"] for h in history]
                        current_scores = [h["Current Score"] for h in history]
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=trials, y=current_scores,
                            name="Trial Score",
                            mode="markers",
                            marker=dict(color="rgba(165, 180, 252, 0.5)", size=6)
                        ))
                        fig.add_trace(go.Scatter(
                            x=trials, y=best_scores,
                            name="Best Score (Convergence)",
                            mode="lines+markers",
                            line=dict(color="#10b981", width=2),
                            marker=dict(color="#10b981", size=6)
                        ))
                        fig.update_layout(
                            height=240,
                            margin=dict(l=40, r=20, t=15, b=30),
                            template="plotly_dark",
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            xaxis=dict(title="Trial", gridcolor="rgba(255,255,255,0.05)"),
                            yaxis=dict(title="Score", gridcolor="rgba(255,255,255,0.05)")
                        )
                        plotly_placeholder.plotly_chart(fig, width='stretch')
                        
                    return update_ui

                try:
                    trials_for_strat = max(20, ho_trials // len(registry))
                    result = engine.optimize(
                        strat_cls, data, 
                        n_trials=trials_for_strat,
                        callback=make_callback(sid),
                        optimize_risk=st.session_state.get("ho_opt_risk", False)
                    )
                    ho_results[sid] = {
                        'params': result.best_params,
                        'score': result.best_score,
                        'metrics': result.best_results,
                        'n_trials': len(result.trials),
                        'elapsed': result.total_elapsed,
                    }
                except Exception as e:
                    st.error(f"{sid} hyperopt gagal: {e}")
                progress_bar.progress((idx + 1) / len(registry))

            status_text.success("✅ Semua strategi selesai dioptimasi!")
            realtime_placeholder.empty()
            plotly_placeholder.empty()
        else:
            registry = BaseStrategy.get_registry()
            if ho_strategy in registry:
                strat_cls = registry[ho_strategy]
                if hasattr(strat_cls, 'param_space') and strat_cls.param_space:
                    realtime_placeholder = st.empty()
                    plotly_placeholder = st.empty()
                    history = []
                    
                    def update_ui(current, total, best_score, best_params, current_score=0.0, current_params=None):
                        pct = int((current / total) * 100)
                        
                        history.append({
                            "Trial": current,
                            "Best Score": best_score,
                            "Current Score": current_score
                        })
                        
                        # Format best params
                        best_rows = []
                        for k, v in best_params.items():
                            v_clean = v.item() if hasattr(v, 'item') else v
                            val_str = f"{v_clean:.4f}" if isinstance(v_clean, float) else str(v_clean)
                            best_rows.append(
                                f"<div style='background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.15); padding: 6px; border-radius: 6px; text-align: center;'>"
                                f"<div style='font-size: 0.6rem; opacity: 0.5; text-transform: uppercase;'>{k}</div>"
                                f"<div style='font-size: 0.82rem; font-weight: 700; color: #10b981;'>{val_str}</div>"
                                f"</div>"
                            )
                        best_params_html = "".join(best_rows)
                        
                        # Format current params
                        current_params = current_params or best_params
                        current_rows = []
                        for k, v in current_params.items():
                            v_clean = v.item() if hasattr(v, 'item') else v
                            val_str = f"{v_clean:.4f}" if isinstance(v_clean, float) else str(v_clean)
                            current_rows.append(
                                f"<div style='background: rgba(99, 102, 241, 0.05); border: 1px solid rgba(99, 102, 241, 0.15); padding: 6px; border-radius: 6px; text-align: center;'>"
                                f"<div style='font-size: 0.6rem; opacity: 0.5; text-transform: uppercase;'>{k}</div>"
                                f"<div style='font-size: 0.82rem; font-weight: 700; color: #a5b4fc;'>{val_str}</div>"
                                f"</div>"
                            )
                        current_params_html = "".join(current_rows)
                        
                        html = f"""
                        <div style="
                            background: rgba(17, 25, 40, 0.75);
                            backdrop-filter: blur(12px);
                            -webkit-backdrop-filter: blur(12px);
                            border: 1px solid rgba(255, 255, 255, 0.1);
                            border-radius: 16px;
                            padding: 20px;
                            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                            margin-bottom: 20px;
                            background-image: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(168, 85, 247, 0.05) 100%);
                            font-family: 'Outfit', sans-serif;
                        ">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: #a855f7; box-shadow: 0 0 10px #a855f7;"></span>
                                    <span style="font-size: 0.95rem; font-weight: 800; color: #e0e7ff; letter-spacing: 0.05em; text-transform: uppercase;">
                                        🧬 OPTIMIZING {ho_strategy}
                                    </span>
                                </div>
                                <span style="font-size: 0.75rem; font-weight: 700; color: #fbbf24; background: rgba(251, 191, 36, 0.1); padding: 4px 10px; border-radius: 20px; border: 1px solid rgba(251, 191, 36, 0.2);">
                                    Trial {current} / {total}
                                </span>
                            </div>
                            
                            <!-- Glowing Progress Bar -->
                            <div style="width: 100%; background-color: rgba(255, 255, 255, 0.05); border-radius: 10px; height: 6px; margin-bottom: 16px; overflow: hidden; border: 1px solid rgba(255,255,255,0.05);">
                                <div style="width: {pct}%; background: linear-gradient(90deg, #6366f1 0%, #a855f7 100%); height: 100%; border-radius: 10px; box-shadow: 0 0 12px #a855f7;"></div>
                            </div>
                            
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                                <!-- Left Column: Best So Far -->
                                <div style="background: rgba(16, 185, 129, 0.02); border: 1px solid rgba(16, 185, 129, 0.1); border-radius: 10px; padding: 12px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <span style="font-size: 0.68rem; color: #9ca3af; font-weight: 700; text-transform: uppercase;">🏆 Best So Far</span>
                                        <span style="font-size: 0.85rem; font-weight: 800; color: #10b981;">{best_score:.4f}</span>
                                    </div>
                                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(70px, 1fr)); gap: 6px;">
                                        {best_params_html}
                                    </div>
                                </div>
                                
                                <!-- Right Column: Current Trial -->
                                <div style="background: rgba(99, 102, 241, 0.02); border: 1px solid rgba(99, 102, 241, 0.1); border-radius: 10px; padding: 12px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <span style="font-size: 0.68rem; color: #9ca3af; font-weight: 700; text-transform: uppercase;">⚡ Testing Current</span>
                                        <span style="font-size: 0.85rem; font-weight: 800; color: #a5b4fc;">{current_score:.4f}</span>
                                    </div>
                                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(70px, 1fr)); gap: 6px;">
                                        {current_params_html}
                                    </div>
                                </div>
                            </div>
                        </div>
                        """
                        realtime_placeholder.markdown(_clean_html(html), unsafe_allow_html=True)
                        
                        # Plot convergence
                        trials = [h["Trial"] for h in history]
                        best_scores = [h["Best Score"] for h in history]
                        current_scores = [h["Current Score"] for h in history]
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=trials, y=current_scores,
                            name="Trial Score",
                            mode="markers",
                            marker=dict(color="rgba(165, 180, 252, 0.5)", size=6)
                        ))
                        fig.add_trace(go.Scatter(
                            x=trials, y=best_scores,
                            name="Best Score (Convergence)",
                            mode="lines+markers",
                            line=dict(color="#10b981", width=2),
                            marker=dict(color="#10b981", size=6)
                        ))
                        fig.update_layout(
                            height=240,
                            margin=dict(l=40, r=20, t=15, b=30),
                            template="plotly_dark",
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            xaxis=dict(title="Trial", gridcolor="rgba(255,255,255,0.05)"),
                            yaxis=dict(title="Score", gridcolor="rgba(255,255,255,0.05)")
                        )
                        plotly_placeholder.plotly_chart(fig, width='stretch')
                                
                    result = engine.optimize(
                        strat_cls, data, 
                        n_trials=ho_trials, 
                        callback=update_ui,
                        optimize_risk=st.session_state.get("ho_opt_risk", False)
                    )
                    ho_results[ho_strategy] = {
                        'params': result.best_params,
                        'score': result.best_score,
                        'metrics': result.best_results,
                        'n_trials': len(result.trials),
                        'elapsed': result.total_elapsed,
                    }
                    realtime_placeholder.empty()
                    plotly_placeholder.empty()
                else:
                    st.error(f"{ho_strategy} tidak memiliki param_space")
            else:
                st.error(f"Strategy '{ho_strategy}' tidak ditemukan di registry")

        st.session_state.ho_results = ho_results
        st.session_state.hyperopt_running = False
        st.rerun()

    ho_results = st.session_state.get("ho_results", {})
    if ho_results:
        st.markdown("---")
        st.markdown("### 🏆 Hyperopt Results")
        st.caption("Hasil optimasi parameter dari semua strategi. Score berdasarkan loss function (Sortino/Sharpe/Calmar). Klik expand untuk detail params & metrics, lalu apply langsung ke config.")

        best_sid = min(ho_results.keys(), key=lambda k: ho_results[k]['score'])
        best_score = -ho_results[best_sid]['score']
        total_trials = sum(r['n_trials'] for r in ho_results.values())
        total_time = sum(r['elapsed'] for r in ho_results.values())

        _metrics_bar(
            ("Best Strategy", best_sid, "#ffffff"),
            ("Best Score", f"{best_score:.2f}", "#10b981"),
            ("Total Trials", str(total_trials), "#a5b4fc"),
            ("Total Time", f"{total_time:.1f}s", "#f59e0b"),
        )

        for sid, hresult in ho_results.items():
            is_best = (sid == best_sid)
            with st.expander(f"🧬 {sid} — Score: {-hresult['score']:.2f}", expanded=is_best):
                col1, col2 = st.columns([1.5, 3.5])
                with col1:
                    st.markdown("**Best Params:**")
                    params_cols_html = []
                    for k, v in hresult['params'].items():
                        v_clean = v.item() if hasattr(v, 'item') else v
                        val_str = f"{v_clean:.4f}" if isinstance(v_clean, float) else str(v_clean)
                        params_cols_html.append(
                            f"<div style='background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 8px; border-radius: 6px; text-align: center;'>"
                            f"<div style='font-size: 0.65rem; opacity: 0.5; text-transform: uppercase; font-weight: 600; letter-spacing: 0.02em;'>{k}</div>"
                            f"<div style='font-size: 0.85rem; font-weight: 700; color: #38bdf8; margin-top: 2px;'>{val_str}</div>"
                            f"</div>"
                        )
                    params_html = f"""
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(90px, 1fr)); gap: 6px; font-family: 'Outfit', sans-serif;">
                        {"".join(params_cols_html)}
                    </div>
                    """
                    st.markdown(_clean_html(params_html), unsafe_allow_html=True)
                    
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    if st.button(f"📥 Apply {sid} Params", key=f"ho_apply_{sid}", width='stretch'):
                        for k, v in hresult['params'].items():
                            v_clean = v.item() if hasattr(v, 'item') else v
                            if k in ['stop_loss_pct', 'take_profit_pct']:
                                config.set('risk_management', k, float(v_clean))
                            else:
                                config.set('strategies', sid, k, v_clean)
                        config.save()
                        refresh_robot(config)
                        st.success(f"✅ {sid} params applied!")
                        st.rerun()

                with col2:
                    st.markdown("**Metrics:**")
                    m = hresult.get('metrics', {})
                    metrics_labels = {
                        'total_return': ('Total Return', '%', '#10b981'),
                        'sharpe_ratio': ('Sharpe Ratio', '', '#a5b4fc'),
                        'sortino_ratio': ('Sortino Ratio', '', '#818cf8'),
                        'calmar_ratio': ('Calmar Ratio', '', '#f59e0b'),
                        'profit_factor': ('Profit Factor', '', '#10b981'),
                        'win_rate': ('Win Rate', '%', '#fbbf24'),
                        'max_drawdown': ('Max Drawdown', '%', '#ef4444')
                    }
                    metrics_cols_html = []
                    for k in ['total_return', 'sharpe_ratio', 'sortino_ratio',
                               'calmar_ratio', 'profit_factor', 'win_rate', 'max_drawdown']:
                        v = m.get(k, 0)
                        label, suffix, color = metrics_labels.get(k, (k, '', '#ffffff'))
                        val_str = f"{v:.2f}{suffix}"
                        metrics_cols_html.append(
                            f"<div style='background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 8px; border-radius: 6px; text-align: center;'>"
                            f"<div style='font-size: 0.62rem; opacity: 0.5; text-transform: uppercase; font-weight: 600; letter-spacing: 0.02em;'>{label}</div>"
                            f"<div style='font-size: 0.85rem; font-weight: 700; color: {color}; margin-top: 2px;'>{val_str}</div>"
                            f"</div>"
                        )
                    metrics_html = f"""
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; font-family: 'Outfit', sans-serif;">
                        {"".join(metrics_cols_html)}
                    </div>
                    """
                    st.markdown(_clean_html(metrics_html), unsafe_allow_html=True)

        st.markdown("---")
        if st.button("📥 Apply ALL Best Params to Config", width='stretch', type="primary"):
            for sid, hresult in ho_results.items():
                for k, v in hresult['params'].items():
                    v_clean = v.item() if hasattr(v, 'item') else v
                    if k in ['stop_loss_pct', 'take_profit_pct']:
                        config.set('risk_management', k, float(v_clean))
                    else:
                        config.set('strategies', sid, k, v_clean)
            config.save()
            refresh_robot(config)
            st.success("✅ Semua params diterapkan!")
            st.rerun()
    else:
        if not st.session_state.hyperopt_running:
            st.info("💡 Klik **RUN HYPEROPT** untuk memulai optimasi parameter")

    st.markdown("---")
    with st.expander("📚 Riwayat Hyperopt Sebelumnya (dari Database)"):
        try:
            dc = st.session_state.get("dashboard_ctrl", DashboardController())
            prev_runs = dc.get_all_hyperopt_results()
            if prev_runs:
                for row in prev_runs:
                    params_dict = getattr(row, 'best_params', {})
                    if params_dict:
                        if isinstance(params_dict, str):
                            import json
                            try:
                                params_dict = json.loads(params_dict)
                            except Exception:
                                params_dict = {}
                    else:
                        params_dict = {}
                        
                    params_badges = []
                    if isinstance(params_dict, dict):
                        for k, v in params_dict.items():
                            v_clean = v.item() if hasattr(v, 'item') else v
                            val_str = f"{v_clean:.4f}" if isinstance(v_clean, float) else str(v_clean)
                            params_badges.append(
                                f"<div style='background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.2); padding: 4px 8px; border-radius: 4px; font-size: 0.72rem; display: inline-block; color: #a5b4fc; margin-right: 4px; margin-top: 4px;'>"
                                f"<span style='opacity: 0.6;'>{k}:</span> <strong style='color: #38bdf8;'>{val_str}</strong>"
                                f"</div>"
                            )
                    badges_html = "".join(params_badges)
                    
                    card_html = f"""
                    <div style="
                        background: rgba(255, 255, 255, 0.02);
                        border: 1px solid rgba(255, 255, 255, 0.05);
                        border-radius: 12px;
                        padding: 12px 16px;
                        margin-bottom: 12px;
                        font-family: 'Outfit', sans-serif;
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 6px;">
                            <span style="font-size: 0.95rem; font-weight: 700; color: #ffffff;">🧬 {getattr(row, 'strategy_name', 'unknown')}</span>
                            <span style="font-size: 0.85rem; font-weight: 700; color: #10b981; background: rgba(16, 185, 129, 0.1); padding: 2px 8px; border-radius: 20px;">
                                Score: {getattr(row, 'best_score', 0.0):.2f}
                            </span>
                        </div>
                        <div style="display: flex; gap: 15px; font-size: 0.75rem; color: #9ca3af; margin-top: 6px;">
                            <span>🔄 Trials: <strong>{getattr(row, 'n_trials', 0)}</strong></span>
                            <span>⏱️ Time: <strong>{getattr(row, 'elapsed_seconds', 0.0):.1f}s</strong></span>
                        </div>
                        <div style="margin-top: 8px; display: flex; flex-wrap: wrap; gap: 4px;">
                            {badges_html}
                        </div>
                    </div>
                    """
                    st.markdown(_clean_html(card_html), unsafe_allow_html=True)
            else:
                st.info("Belum ada riwayat hyperopt di database")
        except Exception as e:
            st.info(f"Tidak dapat memuat dari DB: {e}")
