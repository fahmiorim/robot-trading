"""About page — system info, architecture overview, tech stack."""

import sys
import platform
from datetime import datetime

import streamlit as st


def render():
    st.title("ℹ️ About")

    # Hero card
    st.markdown("""
    <div style="font-family: 'Outfit', sans-serif; background: linear-gradient(135deg, rgba(99,102,241,0.08), rgba(139,92,246,0.04));
         border: 1px solid rgba(99,102,241,0.18); border-radius: 14px; padding: 2rem 2.2rem;
         box-shadow: 0 8px 30px rgba(0,0,0,0.25); margin-bottom: 1.5rem;">
        <div style="display: flex; align-items: center; gap: 18px;">
            <div style="font-size: 3.5rem; filter: drop-shadow(0 0 18px rgba(99,102,241,0.5));">🤖</div>
            <div>
                <div style="font-size: 1.6rem; font-weight: 800; letter-spacing: -0.02em;
                     background: linear-gradient(135deg, #ffffff 40%, #a5b4fc 100%);
                     -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    AI Trading Robot
                </div>
                <div style="font-size: 0.75rem; opacity: 0.5; letter-spacing: 0.08em;
                     text-transform: uppercase; margin-top: 4px; font-weight: 600; color: #a5b4fc;">
                    v2.0 — Automated Swarm Intelligence Trading System
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Feature cards — 2 columns
    col1, col2 = st.columns(2)

    features_left = [
        ("🧠", "Multi-Strategy Core",
         "5 technical strategies: MA Crossover, RSI Momentum, MACD Histogram, Bollinger Bands, Breakout Detection"),
        ("🤖", "ML Integration",
         "Random Forest, Gradient Boosting & LSTM single-step prediction with automatic retraining"),
        ("🔍", "Market Regime Filter",
         "ADX-based regime classifier detects Trending, Ranging, or Choppy conditions in real-time"),
        ("🐝", "Swarm Intelligence",
         "Weighted ensemble voting aggregates all signals for consensus-based trading decisions"),
    ]
    features_right = [
        ("📊", "Walk-Forward Backtester",
         "Tick-accurate historical simulation with realistic slippage, spread, and commission modelling"),
        ("🛡️", "Risk Controller",
         "Circuit breaker, daily drawdown limit, daily loss cap, consecutive loss tracker, cooldown timer"),
        ("📡", "Notification RPC",
         "Telegram alerts, real-time WebSocket dashboard, and push notification support"),
        ("⚡", "HyperOpt Engine",
         "Automated hyperparameter optimisation using Bayesian search per strategy"),
    ]

    def _feature_card(emoji, title, desc):
        return f"""
        <div style="font-family: 'Outfit', sans-serif; background: rgba(255,255,255,0.02);
             border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 1rem 1.1rem;
             margin-bottom: 10px; transition: border-color 0.2s;">
            <div style="display: flex; align-items: flex-start; gap: 12px;">
                <div style="font-size: 1.5rem; flex-shrink: 0;">{emoji}</div>
                <div>
                    <div style="font-size: 0.82rem; font-weight: 700; color: #e2e8f0; margin-bottom: 3px;">{title}</div>
                    <div style="font-size: 0.7rem; opacity: 0.55; line-height: 1.5;">{desc}</div>
                </div>
            </div>
        </div>
        """

    with col1:
        for emoji, title, desc in features_left:
            st.markdown(_feature_card(emoji, title, desc), unsafe_allow_html=True)

    with col2:
        for emoji, title, desc in features_right:
            st.markdown(_feature_card(emoji, title, desc), unsafe_allow_html=True)

    # Tech Stack bar
    st.markdown("<h4 style='margin:1.2rem 0 8px; font-size:0.95rem; font-weight:700; color:#a5b4fc;'>🛠️ Tech Stack</h4>", unsafe_allow_html=True)

    techs = [
        ("Python", "#3776ab"),
        ("MetaTrader 5", "#0066cc"),
        ("pandas", "#150458"),
        ("numpy", "#013243"),
        ("scikit-learn", "#f7931e"),
        ("Streamlit", "#ff4b4b"),
        ("Plotly", "#636efa"),
        ("MySQL", "#4479a1"),
        ("WebSocket", "#10b981"),
    ]

    badges = "".join(
        f'<span style="display:inline-block; padding:4px 10px; margin:3px 4px; border-radius:6px; '
        f'font-size:0.68rem; font-weight:700; color:#fff; background:{color}; '
        f'letter-spacing:0.02em;">{name}</span>'
        for name, color in techs
    )
    st.markdown(
        f'<div style="font-family:\'Outfit\',sans-serif; margin-bottom:1.2rem;">{badges}</div>',
        unsafe_allow_html=True,
    )

    # System Info
    st.markdown("<h4 style='margin:0.8rem 0 8px; font-size:0.95rem; font-weight:700; color:#a5b4fc;'>💻 System Info</h4>", unsafe_allow_html=True)

    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    os_info = f"{platform.system()} {platform.release()}"
    arch = platform.machine()

    items = [
        ("PYTHON", py_ver, "#3776ab"),
        ("OS", os_info, "#6366f1"),
        ("ARCH", arch, "#8b5cf6"),
        ("TIME", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "#f59e0b"),
    ]

    sep = '<div style="width:1px; height:22px; background:rgba(255,255,255,0.08);"></div>'
    cells = sep.join(
        f'<div style="flex:1; text-align:center;">'
        f'<div style="font-size:0.6rem; opacity:0.5; font-weight:700; text-transform:uppercase; '
        f'letter-spacing:0.05em; margin-bottom:2px;">{lbl}</div>'
        f'<div style="font-size:0.82rem; font-weight:800; color:{col};">{val}</div></div>'
        for lbl, val, col in items
    )
    st.markdown(
        f'<div style="font-family:\'Outfit\',sans-serif; display:flex; align-items:center; '
        f'background:rgba(255,255,255,0.02); padding:10px 16px; border-radius:8px; '
        f'border:1px solid rgba(255,255,255,0.05); margin:4px 0;">{cells}</div>',
        unsafe_allow_html=True,
    )
