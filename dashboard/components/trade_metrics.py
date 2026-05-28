"""Reusable component: Trade metrics (Total P&L, Win Rate, Avg Trade) + P&L chart."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_trade_metrics(df: pd.DataFrame, profit_col: str = "profit"):
    """Render 4-column trade metrics (Trades, P&L, Win Rate, Avg Trade) + P&L bar chart.

    Parameters
    ----------
    df : pd.DataFrame
        Trade dataframe. Must contain profit_col.
    profit_col : str
        Column name for profit values.
    """
    cols = st.columns(4)
    with cols[0]:
        st.metric("Trades", len(df))

    if profit_col in df.columns:
        df[profit_col] = pd.to_numeric(df[profit_col], errors='coerce').fillna(0)
        total = df[profit_col].sum()
        with cols[1]:
            st.metric("Total P&L", f"${total:.2f}", delta=f"{total:.2f}")
        with cols[2]:
            wins = (df[profit_col] > 0).sum()
            rate = wins / len(df) * 100 if len(df) > 0 else 0
            st.metric("Win Rate", f"{rate:.1f}%")
        with cols[3]:
            st.metric("Avg Trade", f"${df[profit_col].mean():.2f}")

        # P&L bar chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df[profit_col],
            name='P&L',
            marker_color=df[profit_col].apply(lambda x: '#00b894' if x > 0 else '#ff6b6b'),
        ))
        fig.update_layout(height=350, xaxis_title="Trade #", yaxis_title="P&L ($)")
        st.plotly_chart(fig, use_container_width=True)
