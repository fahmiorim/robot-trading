"""Backtest tab for Performance Analytics page."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dashboard.helpers import ensure_mt5
from dashboard.pages.performance.helpers import _clean_html, _glass_card, _info_banner, _metrics_bar

def render(config):
    _info_banner("▶️ Historical Backtester", "Simulasi strategi dengan data historis — lihat equity curve, perbandingan strategi, dan distribusi P&L.")

    robot = st.session_state.robot
    results = st.session_state.backtest_results or {}

    col1, col2 = st.columns([1, 1])
    with col1:
        with st.container(border=True):
            st.markdown("<h3 style='margin:0 0 10px 0; font-size:0.9rem; color:#a5b4fc;'>⚡ Actions</h3>", unsafe_allow_html=True)
            run_btn = st.button("▶️ Run Full Backtest", width='stretch', type="primary")
    with col2:
        with st.container(border=True):
            st.markdown("<h3 style='margin:0 0 10px 0; font-size:0.9rem; color:#a5b4fc;'>📥 Data</h3>", unsafe_allow_html=True)
            fetch_btn = st.button("📥 Fetch & Backtest", width='stretch')

    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    realtime_table_placeholder = st.empty()

    completed_strats = []

    def backtest_callback(strategy_name, current, total, result):
        pct = int((current / total) * 100)
        progress_placeholder.progress(current / total)
        status_placeholder.info(f"📊 Running Backtest for {strategy_name}... ({current}/{total})")

        ret = result.get('total_return', 0.0)
        trades_count = result.get('num_trades', 0)
        win_rate = result.get('win_rate', 0.0)

        ret_color = '#10b981' if ret >= 0 else '#ef4444'
        ret_sign = '+' if ret >= 0 else ''

        completed_strats.append({
            'name': strategy_name,
            'return': f"<span style='color: {ret_color}; font-weight: 700;'>{ret_sign}{ret:.2f}%</span>",
            'trades': str(trades_count),
            'win_rate': f"{win_rate:.1f}%"
        })

        rows_html = "".join(
            f"<tr style='border-bottom: 1px solid rgba(255,255,255,0.05);'>"
            f"<td style='padding: 8px; font-weight: 600; color: #a5b4fc;'>{item['name']}</td>"
            f"<td style='padding: 8px; text-align: right;'>{item['return']}</td>"
            f"<td style='padding: 8px; text-align: center; color: #e2e8f0;'>{item['trades']}</td>"
            f"<td style='padding: 8px; text-align: center; color: #fbbf24;'>{item['win_rate']}</td>"
            f"</tr>"
            for item in completed_strats
        )

        html = f"""
        <div style="
            background: rgba(17, 25, 40, 0.75);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            margin-top: 15px;
            margin-bottom: 20px;
            background-image: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(168, 85, 247, 0.05) 100%);
            font-family: 'Outfit', sans-serif;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: #10b981; box-shadow: 0 0 10px #10b981;"></span>
                    <span style="font-size: 0.95rem; font-weight: 800; color: #e0e7ff; letter-spacing: 0.05em; text-transform: uppercase;">
                        📊 Live Backtest Progress
                    </span>
                </div>
                <span style="font-size: 0.75rem; font-weight: 700; color: #fbbf24; background: rgba(251, 191, 36, 0.1); padding: 4px 10px; border-radius: 20px; border: 1px solid rgba(251, 191, 36, 0.2);">
                    {current} / {total} Strategies
                </span>
            </div>

            <table style="width: 100%; border-collapse: collapse; font-size: 0.82rem; margin-top: 10px;">
                <thead>
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.1); text-transform: uppercase; font-size: 0.65rem; color: #9ca3af; letter-spacing: 0.05em;">
                        <th style="padding: 8px; text-align: left;">Strategy</th>
                        <th style="padding: 8px; text-align: right;">Return</th>
                        <th style="padding: 8px; text-align: center;">Trades</th>
                        <th style="padding: 8px; text-align: center;">Win Rate</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """
        realtime_table_placeholder.markdown(_clean_html(html), unsafe_allow_html=True)

    if run_btn:
        try:
            data = st.session_state.get("_last_data")
            if data is None:
                if not ensure_mt5():
                    st.stop()
                data = robot.fetch_data()
            results = robot.run_backtest_all(data, callback=backtest_callback)
            st.session_state.backtest_results = results
            progress_placeholder.empty()
            status_placeholder.empty()
            realtime_table_placeholder.empty()
            st.success("Selesai!")
            st.rerun()
        except Exception as e:
            st.error(f"Backtest error: {e}")

    if fetch_btn:
        try:
            if not ensure_mt5():
                st.stop()
            data = robot.fetch_data()
            st.session_state["_last_data"] = data
            results = robot.run_backtest_all(data, callback=backtest_callback)
            st.session_state.backtest_results = results
            progress_placeholder.empty()
            status_placeholder.empty()
            realtime_table_placeholder.empty()
            st.success(f"Loaded {len(data)} candles, backtest done!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    if not results:
        st.info("💡 Belum ada hasil. Klik **Run Full Backtest** atau **Fetch & Backtest**.")
        return

    st.markdown("### 📊 Performance Summary")
    st.caption("Ringkasan performa backtest — strategi terbaik berdasarkan bobot regime, return rata-rata, dan Sharpe ratio dari semua strategi.")
    best_name = robot.best_strategy_name if robot.best_strategy_name else max(results.keys(), key=lambda k: results[k]['total_return'])
    best = results[best_name]
    _tot_trades = sum(r['num_trades'] for r in results.values())
    _avg_ret = sum(r['total_return'] for r in results.values()) / len(results)
    avg_sharpe = sum(r.get('sharpe_ratio', 0) for r in results.values()) / len(results)
    _ret_color = '#10b981' if best['total_return'] >= 0 else '#ef4444'
    _avg_color = '#10b981' if _avg_ret >= 0 else '#ef4444'
    _metrics_bar(
        ("Best Strategy", best_name, "#ffffff"),
        ("Return", f"{best['total_return']:.2f}%", _ret_color),
        ("Trades", str(_tot_trades), "#ffffff"),
        ("Avg Return", f"{_avg_ret:.2f}%", _avg_color),
        ("Avg Sharpe", f"{avg_sharpe:.2f}", "#a5b4fc"),
    )

    st.markdown("### 📋 Strategy Comparison")
    st.caption("Perbandingan semua strategi secara berdampingan — return, win rate, max drawdown, Sharpe, Sortino, Calmar, dan Profit Factor.")
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
    st.markdown(_glass_card(""), unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

    st.markdown("### 📈 Equity Curves")
    st.caption("Grafik pertumbuhan modal setiap strategi dari awal sampai akhir backtest — garis naik = profit, turun = drawdown. Strategi stabil ditandai dengan kurva mulus naik.")
    fig = go.Figure()
    for name, r in results.items():
        eq = r.get('equity_curve', [])
        if eq:
            fig.add_trace(go.Scatter(y=eq, name=name, mode='lines', line=dict(width=1.5)))
    fig.update_layout(
        height=400, xaxis_title="Step", yaxis_title="Equity ($)",
        hovermode='x unified', template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(fig, width='stretch')

    st.markdown(f"### 📝 Trades: {best_name}")
    st.caption(f"Daftar kronologis semua trade untuk **{best_name}** — harga entry/exit, profit %, dan P&L. Histogram distribusi P&L menunjukkan konsistensi: bentuk lonceng di kanan = profit konsisten.")
    trades = best.get('trades', [])
    if trades:
        tdf = pd.DataFrame(trades)
        st.dataframe(tdf, width='stretch', hide_index=True)
        if 'profit_pct' in tdf.columns:
            fig2 = px.histogram(tdf, x='profit_pct', nbins=30, title="P&L Distribution",
                                labels={'profit_pct': 'Profit %'})
            fig2.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            )
            st.plotly_chart(fig2, width='stretch')
    else:
        st.info("Tidak ada trade tercatat")
