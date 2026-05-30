"""Trade History tab for Performance Analytics page."""
import streamlit as st
import pandas as pd
from dashboard.helpers import ensure_mt5
from dashboard.components import render_trade_metrics
from src.exchange.helpers import get_trade_history
from src.controllers.dashboard_interface import IDashboardController
from dashboard.pages.performance.helpers import _info_banner, _metrics_bar

def render(config):
    _info_banner("📜 Real Trade History", "Riwayat trading dari database robot atau MT5 — filter berdasarkan rentang waktu dan sumber data.")

    col1, col2 = st.columns([1, 2])
    with col1:
        days = st.slider("📅 Rentang Waktu (Hari)", 1, 365, 30, key="th_days")
    with col2:
        source = st.radio("📡 Sumber Data", ["🤖 Robot Database", "📊 MT5 Platform"], horizontal=True, key="th_source")

    dc: IDashboardController = st.session_state.get("dashboard_ctrl")

    try:
        if source == "🤖 Robot Database":
            history = dc.get_trade_history(limit=500)
            if history:
                df = pd.DataFrame(history)
                st.dataframe(df, width='stretch', hide_index=True)
                render_trade_metrics(df, profit_col="profit")

                summary = dc.get_trade_summary(days)
                if summary:
                    st.markdown("### 📊 Aggregate Stats")
                    st.caption("Rekap performa keseluruhan — total trade, posisi terbuka, total P&L, dan win rate dari database robot.")
                    tot = int(summary.get('total_trades', 0))
                    opn = int(summary.get('open_trades', 0))
                    pnl = float(summary.get('total_profit', 0))
                    wr = float(summary.get('win_rate', 0))
                    pnl_color = "#10b981" if pnl >= 0 else "#ef4444"
                    pnl_sign = "+" if pnl >= 0 else ""
                    _metrics_bar(
                        ("Total Trades", str(tot), "#ffffff"),
                        ("Open Trades", str(opn), "#a5b4fc"),
                        ("Total P&L", f"{pnl_sign}${pnl:.2f}", pnl_color),
                        ("Win Rate", f"{wr:.1f}%", "#f59e0b"),
                    )
            else:
                st.info("Belum ada riwayat trading di database")
        else:
            if ensure_mt5():
                history_raw = get_trade_history(days, limit=500)
                if history_raw is not None and len(history_raw) > 0:
                    history = pd.DataFrame(history_raw) if isinstance(history_raw, list) else history_raw
                    st.dataframe(history, width='stretch')
                    profit_col = next((c for c in ['profit', 'Profit', 'pnl', 'P&L'] if c in history.columns), None)
                    if profit_col:
                        render_trade_metrics(history, profit_col=profit_col)
                    else:
                        st.info("Kolom profit tidak ditemukan di data MT5")
                else:
                    st.info("Tidak ada riwayat trading dari MT5")
            else:
                st.warning("MT5 tidak terhubung")
    except Exception as e:
        st.error(f"Gagal memuat riwayat trading: {e}")
