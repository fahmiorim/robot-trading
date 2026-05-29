"""
Signals Settings Tab — premium glass cards with Indonesian descriptions.
"""
import streamlit as st
import textwrap

SIGNAL_INFO = {
    "use_ml": {
        "icon": "🤖",
        "label": "Sinyal Machine Learning",
        "help": "Gunakan model ML (Random Forest / Gradient Boosting / LSTM) untuk memberi sinyal trading.",
    },
    "use_agent": {
        "icon": "🧠",
        "label": "Sinyal Agent AI",
        "help": "Gunakan agent pipeline dengan analisis regime, momentum, dan volatilitas.",
    },
    "use_swarm": {
        "icon": "🐝",
        "label": "Sinyal Swarm Intelligence",
        "help": "Ensemble dari berbagai strategi dengan voting berbobot untuk keputusan bersama.",
    },
}

THRESHOLD_INFO = {
    "consensus_buy_threshold": {
        "icon": "📈",
        "label": "Batas Konsensus Buy",
        "min": -1.0, "max": 1.0, "step": 0.05,
        "help": "Skor konsensus minimum untuk trigger BUY. Lebih tinggi = lebih selektif. Scalping: 0.2–0.3.",
    },
    "consensus_sell_threshold": {
        "icon": "📉",
        "label": "Batas Konsensus Sell",
        "min": -1.0, "max": 0.0, "step": 0.05,
        "help": "Skor konsensus maksimum untuk trigger SELL. Lebih rendah = lebih selektif.",
    },
}


def _render_card(config, section: str, key: str, info: dict) -> bool:
    edited = False
    v = config.get(section, key)
    is_bool = isinstance(v, bool)

    with st.container(border=True):
        col1, col2 = st.columns([0.65, 0.35], vertical_alignment="center")
        with col1:
            st.markdown(f"**{info['icon']} {info['label']}**")
            st.caption(info.get('help', ''))
        with col2:
            if is_bool:
                nv = st.checkbox(info["label"], v, key=f"{section}_{key}", label_visibility="collapsed")
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
            <div class="title">📡 Sumber Sinyal</div>
            <div class="desc">Aktifkan sumber sinyal trading dan atur threshold konsensus. Kombinasikan ML, Agent AI, dan Swarm untuk akurasi maksimal.</div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    st.markdown("### 🔌 Sumber Sinyal")
    st.caption("Pilih engine yang akan digunakan untuk menghasilkan sinyal trading.")

    cols = st.columns(3)
    for i, k in enumerate(["use_ml", "use_agent", "use_swarm"]):
        with cols[i]:
            edited |= _render_card(config, "signals", k, SIGNAL_INFO[k])

    st.markdown("---")
    st.markdown("### ⚖️ Threshold Konsensus")
    st.caption("Skor konsensus minimum dari semua strategi sebelum sinyal dieksekusi.")

    cols = st.columns(2)
    with cols[0]:
        edited |= _render_card(config, "signals", "consensus_buy_threshold", THRESHOLD_INFO["consensus_buy_threshold"])
    with cols[1]:
        edited |= _render_card(config, "signals", "consensus_sell_threshold", THRESHOLD_INFO["consensus_sell_threshold"])

    return edited
