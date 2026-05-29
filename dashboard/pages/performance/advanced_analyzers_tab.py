"""Advanced Analyzers tab for Performance Analytics page."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dashboard.pages.performance.helpers import _glass_card, _info_banner, _metrics_bar

def render(config):
    results = st.session_state.backtest_results or {}
    if not results:
        st.info("💡 Jalankan backtest terlebih dahulu di tab Backtest untuk melihat analisis lanjutan.")
        return

    _info_banner("🧠 Advanced Analyzers",
                 "Sortino Ratio · Calmar Ratio · Profit Factor · CAGR · SQN · Winning/Loss Streaks · "
                 "Time in Market · Monthly Returns · Strategy Quality Radar")

    selected_strat = st.selectbox("🎯 Pilih Strategy", list(results.keys()), key="adv_strat_select")
    r = results[selected_strat]

    sortino = r.get('sortino_ratio', 0)
    sharpe = r.get('sharpe_ratio', 0)
    calmar = r.get('calmar_ratio', 0)
    pf = r.get('profit_factor', 0)
    cagr = r.get('cagr_pct', 0)
    sqn = r.get('sqn', 0)
    exp_pct = r.get('expectancy_pct', 0)
    _aw = r.get('avg_win_pct', 0)
    _al = r.get('avg_loss_pct', 0)
    awr = _aw / abs(_al) if _al != 0 else 0
    exp_ratio = r.get('expectancy_ratio', 0)

    st.markdown("### 📊 Risk-Adjusted Metrics")
    st.caption("Metrik yang sudah disesuaikan dengan risiko: Sortino (hanya downside risk), Sharpe (total risk), Calmar (vs drawdown), Profit Factor (gross win/loss), CAGR (pertumbuhan tahunan), SQN (>2 = bagus).")
    _metrics_bar(
        ("Sortino", f"{sortino:.2f}", '#10b981' if sortino > 1 else '#ef4444'),
        ("Sharpe", f"{sharpe:.2f}", '#10b981' if sharpe > 1 else '#ef4444'),
        ("Calmar", f"{calmar:.2f}", '#10b981' if calmar > 0.5 else '#f59e0b'),
        ("Profit Factor", f"{pf:.2f}", '#10b981' if pf > 1.5 else '#ef4444' if pf < 1.0 else '#f59e0b'),
        ("CAGR %", f"{cagr:.2f}%", '#10b981' if cagr > 0 else '#ef4444'),
        ("SQN", f"{sqn:.2f}", '#10b981' if sqn > 2 else '#ef4444'),
        ("Expectancy %", f"{exp_pct:.3f}%", '#a5b4fc'),
    )

    st.markdown("### 📊 Trade Quality Metrics")
    st.caption("Kualitas eksekusi trade rata-rata: rasio avg win/loss (>1 = win lebih besar dari loss), expectancy ratio, streak terpanjang, dan rata-rata % win/loss.")
    _metrics_bar(
        ("Avg Win/Loss", f"{awr:.2f}", '#10b981' if awr > 1 else '#ef4444'),
        ("Expectancy Ratio", f"{exp_ratio:.2f}", '#10b981' if exp_ratio > 1 else '#f59e0b'),
        ("Win Streak", str(r.get('longest_win_streak', 0)), '#10b981'),
        ("Loss Streak", str(r.get('longest_loss_streak', 0)), '#ef4444'),
        ("Avg Win %", f"{r.get('avg_win_pct', 0):.1f}%", '#10b981'),
        ("Avg Loss %", f"{r.get('avg_loss_pct', 0):.1f}%", '#ef4444'),
    )

    cur_w = r.get('current_win_streak', 0)
    cur_l = r.get('current_loss_streak', 0)
    if cur_w > 0 or cur_l > 0:
        st.caption(f"📌 Current streaks: 🟢 {cur_w} win / 🔴 {cur_l} loss")

    st.markdown("---")
    st.markdown("### 📅 Monthly Returns")
    st.caption("Return bulanan dalam bentuk bar chart — hijau = profit, merah = loss. Lihat tren konsistensi performa dari bulan ke bulan.")
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
            height=300, title="Monthly Return %", yaxis_title="Return %",
            hovermode='x unified', template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        )
        st.markdown(_glass_card(""), unsafe_allow_html=True)
        st.plotly_chart(fig_m, width='stretch')
    else:
        st.info("Data bulanan tidak tersedia (tidak ada datetime index atau tidak ada trade)")

    st.markdown("---")
    st.markdown("### 🎯 Strategy Quality Radar")
    st.caption("Radar chart 6 dimensi — Return, Sharpe, Sortino, Win Rate, Profit Factor, Calmar. Semakin luas area, semakin baik kualitas strategi secara keseluruhan. Idealnya semua sumbu > 5.")
    radar_categories = ['Return', 'Sharpe', 'Sortino', 'Win Rate', 'Profit Factor', 'Calmar']
    radar_values = [
        min(r.get('total_return', 0) / 20, 10),
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
        height=400, template='plotly_dark',
        margin=dict(l=60, r=30, t=10, b=30),
    )
    st.plotly_chart(fig_radar, width='stretch')
