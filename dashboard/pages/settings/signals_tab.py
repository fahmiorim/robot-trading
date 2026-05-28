import streamlit as st


def render(config) -> bool:
    edited = False

    st.subheader("📡 Signal Sources")
    sig_cols = st.columns(4)
    for i, k in enumerate(["use_ml", "use_agent", "use_swarm"]):
        v = config.get("signals", k)
        with sig_cols[i]:
            nv = st.checkbox(k.replace("_", " ").title(), v, key=f"sig_{k}")
            if nv != v:
                config.set("signals", k, nv)
                edited = True

    st.markdown("---")
    st.subheader("⚖️ Consensus Thresholds")
    c1, c2 = st.columns(2)
    with c1:
        v = config.get("signals", "consensus_buy_threshold")
        nv = st.number_input("Buy Threshold", -1.0, 1.0, float(v), 0.05,
                             help="Minimum consensus score to trigger BUY")
        if nv != v:
            config.set("signals", "consensus_buy_threshold", nv)
            edited = True
    with c2:
        v = config.get("signals", "consensus_sell_threshold")
        nv = st.number_input("Sell Threshold", -1.0, 0.0, float(v), 0.05,
                             help="Maximum consensus score to trigger SELL")
        if nv != v:
            config.set("signals", "consensus_sell_threshold", nv)
            edited = True

    return edited
