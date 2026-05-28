import streamlit as st


def render(config) -> bool:
    edited = False

    st.subheader("📊 Backtest Settings")
    bt_cols = st.columns(3)
    bt_keys = [
        ("initial_balance", "Initial Balance", 100, 1_000_000, 10000),
        ("commission_pct", "Commission %", 0.0, 10.0, 0.1),
        ("slippage_pct", "Slippage %", 0.0, 5.0, 0.05),
    ]
    for i, (k, label, mn, mx, default) in enumerate(bt_keys):
        v = config.get("backtest", k)
        with bt_cols[i]:
            nv = st.number_input(label, float(mn), float(mx), float(v), 0.01, key=f"bt_{k}")
            if nv != v:
                config.set("backtest", k, nv)
                edited = True

    st.markdown("---")
    st.subheader("📐 Position Sizing")
    sizing = config.get("backtest", "position_sizing")
    nv = st.selectbox("Sizing Method", ["fixed_pct", "kelly"], 0 if sizing == "fixed_pct" else 1)
    if nv != sizing:
        config.set("backtest", "position_sizing", nv)
        edited = True

    return edited
