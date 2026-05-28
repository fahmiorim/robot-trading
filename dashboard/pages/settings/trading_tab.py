import streamlit as st


def render(config) -> bool:
    edited = False

    st.subheader("💹 Trading Mode")
    tm1, tm2 = st.columns(2)
    with tm1:
        paper = config.get("trading", "paper_trading")
        nv = st.checkbox("📝 Paper Trading Mode", paper, help="Simulate trades without real money")
        if nv != paper:
            config.set("trading", "paper_trading", nv)
            config.set("trading", "mode", "paper" if nv else "live")
            edited = True
    with tm2:
        pb = config.get("trading", "paper_initial_balance")
        nv = st.number_input("Paper Initial Balance $", 100.0, 1_000_000.0, float(pb), 100.0)
        if nv != pb:
            config.set("trading", "paper_initial_balance", nv)
            edited = True

    st.markdown("---")
    st.subheader("🔬 Strategy Pre-validation")
    spv = config.get("trading", "strategy_pre_validation")
    nv = st.checkbox("Enable Pre-validation", spv, help="Auto-disable poor strategies before trading")
    if nv != spv:
        config.set("trading", "strategy_pre_validation", nv)
        edited = True
    if nv:
        spv1, spv2, spv3 = st.columns(3)
        with spv1:
            v = config.get("trading", "min_backtest_trades")
            nv = st.number_input("Min Trades", 1, 100, int(v))
            if nv != v:
                config.set("trading", "min_backtest_trades", nv)
                edited = True
        with spv2:
            v = config.get("trading", "min_win_rate")
            nv = st.number_input("Min Win Rate %", 0.0, 100.0, float(v), 1.0)
            if nv != v:
                config.set("trading", "min_win_rate", nv)
                edited = True
        with spv3:
            v = config.get("trading", "max_backtest_drawdown")
            nv = st.number_input("Max Drawdown %", 5.0, 100.0, float(v), 1.0)
            if nv != v:
                config.set("trading", "max_backtest_drawdown", nv)
                edited = True

    v = config.get("trading", "max_consecutive_losses")
    nv = st.number_input("Max Consecutive Losses", 1, 50, int(v))
    if nv != v:
        config.set("trading", "max_consecutive_losses", nv)
        edited = True

    return edited
