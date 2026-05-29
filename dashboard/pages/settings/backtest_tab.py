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
    "risk_free_rate": {
        "icon": "🏦",
        "label": "Risk-Free Rate",
        "min": 0.0, "max": 1.0, "step": 0.001, "format": "%.3f",
        "help": "Tingkat return bebas risiko tahunan (fraction). 0.02 = 2%. Digunakan untuk Sharpe & Sortino ratio.",
    },
    "periods_per_year": {
        "icon": "📅",
        "label": "Periode per Tahun",
        "min": 1, "max": 525600, "step": 1,
        "help": "Jumlah periode trading per tahun. Daily: 252, H1: ~5840, M15: ~35040, M5: ~105120, M1: ~525600.",
    },
}


def _render_card(config, section: str, key: str, info: dict) -> bool:
    edited = False
    v = config.get(section, key)
    is_int = info.get("min") is not None and isinstance(info["min"], int)
    fmt = info.get("format", None)

    with st.container(border=True):
        col1, col2 = st.columns([0.65, 0.35], vertical_alignment="center")
        with col1:
            st.markdown(f"**{info['icon']} {info['label']}**")
            st.caption(info.get('help', ''))
        with col2:
            if is_int:
                nv = st.number_input(info["label"], info["min"], info["max"], int(v), int(info.get("step", 1)),
                                     key=f"{section}_{key}", label_visibility="collapsed")
            else:
                nv = st.number_input(info["label"], info["min"], info["max"], float(v), info.get("step", 0.1),
                                     format=fmt, key=f"{section}_{key}", label_visibility="collapsed")
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

    # ── Performance Metrics ──
    st.markdown("---")
    st.markdown("### 📈 Metrik Performa")
    st.caption(
        "Risk-free rate dan periode per tahun untuk kalkulasi Sharpe & Sortino ratio. "
        "Digunakan oleh backtesting engine untuk annualized ratio."
    )

    cols = st.columns(2)
    with cols[0]:
        edited |= _render_card(config, "performance", "risk_free_rate", BT_INFO["risk_free_rate"])
    with cols[1]:
        edited |= _render_card(config, "performance", "periods_per_year", BT_INFO["periods_per_year"])

    return edited
