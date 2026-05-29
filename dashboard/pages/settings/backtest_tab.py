"""
Backtest Settings Tab — premium glass cards with Indonesian descriptions.
"""
import streamlit as st
import textwrap

BT_INFO = {
    "initial_balance": {
        "icon": "💰",
        "label": "Saldo Awal",
        "min": 100.0, "max": 1_000_000.0, "step": 100.0,
        "help": "Saldo awal simulasi backtest.",
    },
    "commission_pct": {
        "icon": "💸",
        "label": "Komisi (%)",
        "min": 0.0, "max": 10.0, "step": 0.01,
        "help": "Biaya komisi per trade. XAUUSD: 0.1% realistis.",
    },
    "slippage_pct": {
        "icon": "📉",
        "label": "Slippage (%)",
        "min": 0.0, "max": 5.0, "step": 0.01,
        "help": "Selisih harga eksekusi. Scalping M1: 0.1% untuk simulasi realistis.",
    },
    "position_sizing": {
        "icon": "📐",
        "label": "Metode Sizing",
        "help": "fixed_pct = persentase tetap, kelly = fractional Kelly optimal.",
    },
}


def _render_card(config, section: str, key: str, info: dict) -> bool:
    edited = False
    v = config.get(section, key)

    with st.container(border=True):
        col1, col2 = st.columns([0.65, 0.35], vertical_alignment="center")
        with col1:
            st.markdown(f"**{info['icon']} {info['label']}**")
            st.caption(info.get('help', ''))
        with col2:
            if key == "position_sizing":
                opts = ["fixed_pct", "kelly"]
                idx = opts.index(v) if v in opts else 0
                nv = st.selectbox(info["label"], opts, idx, key=f"{section}_{key}", label_visibility="collapsed")
            else:
                nv = st.number_input(info["label"], info["min"], info["max"], float(v), info.get("step", 0.1),
                                     key=f"{section}_{key}", label_visibility="collapsed")
        if nv != v:
            config.set(section, key, nv)
            edited = True

    return edited


def render(config) -> bool:
    edited = False

    st.markdown(
        textwrap.dedent("""
        <div class="info-banner">
            <div class="title">📊 Backtest</div>
            <div class="desc">Atur parameter simulasi backtest — saldo, biaya, dan metode position sizing.</div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    st.markdown("### ⚙️ Parameter Backtest")
    st.caption("Saldo awal, komisi, dan slippage untuk simulasi yang realistis.")

    cols = st.columns(3)
    for i, k in enumerate(["initial_balance", "commission_pct", "slippage_pct"]):
        with cols[i]:
            edited |= _render_card(config, "backtest", k, BT_INFO[k])

    st.markdown("---")
    st.markdown("### 📐 Position Sizing")
    st.caption("Metode alokasi posisi: fixed_pct untuk konsistensi, kelly untuk optimal.")
    edited |= _render_card(config, "backtest", "position_sizing", BT_INFO["position_sizing"])

    return edited
