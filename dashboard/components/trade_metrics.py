"""Reusable component: Trade metrics (Total P&L, Win Rate, Avg Trade) + P&L chart."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_trade_metrics(df: pd.DataFrame, profit_col: str = "profit"):
    """Render compact HTML metrics bar (Trades, P&L, Win Rate, Avg Trade) + P&L bar chart.

    Parameters
    ----------
    df : pd.DataFrame
        Trade dataframe. Must contain profit_col.
    profit_col : str
        Column name for profit values.
    """
    n_trades = len(df)
    total = 0.0
    win_rate = 0.0
    avg_trade = 0.0

    if profit_col in df.columns:
        df[profit_col] = pd.to_numeric(df[profit_col], errors='coerce').fillna(0)
        total = df[profit_col].sum()
        wins = (df[profit_col] > 0).sum()
        win_rate = wins / n_trades * 100 if n_trades > 0 else 0
        avg_trade = df[profit_col].mean()

    pnl_color = "#10b981" if total >= 0 else "#ef4444"
    avg_color = "#10b981" if avg_trade >= 0 else "#ef4444"
    pnl_sign = "+" if total >= 0 else ""
    avg_sign = "+" if avg_trade >= 0 else ""

    html = f"""
    <div style="font-family: 'Outfit', sans-serif; display: flex; justify-content: space-between;
         align-items: center; background: rgba(255,255,255,0.02); padding: 10px 16px;
         border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); margin: 10px 0;">
        <div style="flex: 1; text-align: center;">
            <div style="font-size: 0.62rem; opacity: 0.5; font-weight: 700;
                 text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;">TRADES</div>
            <div style="font-size: 0.9rem; font-weight: 800; color: #ffffff;">{n_trades}</div>
        </div>
        <div style="width: 1px; height: 22px; background: rgba(255,255,255,0.08);"></div>
        <div style="flex: 1; text-align: center;">
            <div style="font-size: 0.62rem; opacity: 0.5; font-weight: 700;
                 text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;">TOTAL P&L</div>
            <div style="font-size: 0.9rem; font-weight: 800; color: {pnl_color};">
                {pnl_sign}${total:.2f}
            </div>
        </div>
        <div style="width: 1px; height: 22px; background: rgba(255,255,255,0.08);"></div>
        <div style="flex: 1; text-align: center;">
            <div style="font-size: 0.62rem; opacity: 0.5; font-weight: 700;
                 text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;">WIN RATE</div>
            <div style="font-size: 0.9rem; font-weight: 800; color: #a5b4fc;">{win_rate:.1f}%</div>
        </div>
        <div style="width: 1px; height: 22px; background: rgba(255,255,255,0.08);"></div>
        <div style="flex: 1; text-align: center;">
            <div style="font-size: 0.62rem; opacity: 0.5; font-weight: 700;
                 text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;">AVG TRADE</div>
            <div style="font-size: 0.9rem; font-weight: 800; color: {avg_color};">
                {avg_sign}${avg_trade:.2f}
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    if profit_col in df.columns:
        # P&L bar chart — transparent background, premium style
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df[profit_col],
            name='P&L',
            marker_color=df[profit_col].apply(lambda x: '#10b981' if x > 0 else '#ef4444'),
        ))
        fig.update_layout(
            height=280,
            font=dict(family="Outfit, sans-serif", size=11),
            xaxis_title="Trade #",
            yaxis_title="P&L ($)",
            xaxis=dict(gridcolor="rgba(255,255,255,0.04)", zerolinecolor="rgba(255,255,255,0.06)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.04)", zerolinecolor="rgba(255,255,255,0.1)"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=40, r=10, t=10, b=30),
            template="plotly_dark",
        )
        st.plotly_chart(fig, width='stretch')
