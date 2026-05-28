import streamlit as st


def render():
    st.title("ℹ️ About AI Trading Robot")
    st.markdown("""
    ### 🤖 AI Trading Robot v2.0

    **Features:**
    - 5 strategies: MA Crossover, RSI, MACD, Bollinger Bands, Breakout
    - ML: Random Forest / Gradient Boosting / LSTM
    - Market Regime Detection (ADX-based)
    - Swarm Intelligence ensemble voting
    - Realistic backtesting (slippage, commission, SL/TP)
    - Risk management (drawdown, daily loss, cooldown, trailing stop)
    - Streamlit dashboard with full config editor
    - Telegram notifications

    **Stack:** Python, MetaTrader5, pandas, numpy, scikit-learn, Streamlit, Plotly
    """)

    st.markdown("---")
    c = st.session_state.config
    st.json({
        "config_source": "MySQL database (settings table)",
        "symbol": c.get("general", "symbol"),
        "timeframe": c.get("general", "timeframe"),
        "auto_trade": c.get("general", "auto_trade"),
        "strategies_enabled": sum(1 for s in ["MA_Crossover", "RSI", "MACD", "Bollinger", "Breakout"]
                                   if c.is_strategy_enabled(s)),
        "ml_model": c.get("ml", "model_type"),
        "risk_limits": {
            "position_size": f"{c.get('risk_management', 'position_size_pct')}%",
            "max_daily_loss": f"{c.get('risk_management', 'max_daily_loss_pct')}%",
            "max_drawdown": f"{c.get('risk_management', 'max_drawdown_pct')}%"
        }
    })

    # Note: live_refresh auto-reload is handled globally in dashboard/__init__.py run()

