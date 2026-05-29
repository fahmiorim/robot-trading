"""
Agent Pipeline & Signal Sources Settings Tab — premium glass cards.
Merged from former Signals tab: signal sources + thresholds + agent pipeline parameters.
"""

import streamlit as st

SIGNAL_INFO = {
    "use_ml": {
        "icon": "🤖",
        "label": "Sinyal Machine Learning",
        "help": "Gunakan model ML (Random Forest / Gradient Boosting) untuk memberi sinyal trading.",
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
        "help": "Skor konsensus minimum untuk trigger BUY. Lebih tinggi = lebih selektif. Dengan 2 sumber sinyal: 0.6 = kedua sumber harus setuju.",
    },
    "consensus_sell_threshold": {
        "icon": "📉",
        "label": "Batas Konsensus Sell",
        "min": -1.0, "max": 0.0, "step": 0.05,
        "help": "Skor konsensus maksimum untuk trigger SELL. Dengan 2 sumber sinyal: -0.6 = kedua sumber harus setuju untuk SELL.",
    },
}

AGENT_INFO = {
    "sma_fast_period": {
        "icon": "⚡",
        "label": "SMA Fast Period",
        "min": 2, "max": 100, "step": 1,
        "help": "Periode SMA cepat untuk momentum jangka pendek. Default 10. Scalping M1: 5-15.",
    },
    "sma_medium_period": {
        "icon": "🌊",
        "label": "SMA Medium Period",
        "min": 5, "max": 200, "step": 1,
        "help": "Periode SMA menengah untuk konfirmasi trend. Default 21. Scalping M1: 20-40 — lebih responsif dari 30.",
    },
    "sma_slow_period": {
        "icon": "🐢",
        "label": "SMA Slow Period",
        "min": 10, "max": 500, "step": 1,
        "help": "Periode SMA lambat untuk trend jangka panjang. Default 50. Scalping M1: 40-100.",
    },
    "volatility_window": {
        "icon": "📊",
        "label": "Volatility Window",
        "min": 5, "max": 100, "step": 1,
        "help": "Jendela rolling untuk menghitung volatilitas harga. Default 20. Lebih besar = lebih smooth.",
    },
    "volatility_high": {
        "icon": "🔴",
        "label": "Volatility High",
        "min": 0.001, "max": 0.1, "step": 0.001, "format": "%.4f",
        "help": "Ambang volatilitas tinggi (fraction). Jika volatilitas > nilai ini, posisi ditolak. Default 0.00039 — P95 XAUUSD M1 berdasarkan data aktual (hanya 5% candle paling volatil ditolak).",
    },
    "volatility_medium": {
        "icon": "🟡",
        "label": "Volatility Medium",
        "min": 0.001, "max": 0.05, "step": 0.001, "format": "%.4f",
        "help": "Ambang volatilitas medium (fraction). Default 0.000307 — P75 XAUUSD M1 (25% candle medium risk).",
    },
    "position_size": {
        "icon": "📐",
        "label": "Max Position Size",
        "min": 0.001, "max": 0.5, "step": 0.001, "format": "%.3f",
        "help": "Ukuran posisi maksimal untuk agent (lot). Default 0.01. Scalping XAUUSD: 0.01-0.1.",
    },
    "momentum_threshold": {
        "icon": "🚀",
        "label": "Momentum Threshold",
        "min": 0.0001, "max": 0.05, "step": 0.0001, "format": "%.4f",
        "help": "Ambang momentum minimal untuk entry. Default 0.001 (0.1%). Lebih kecil = lebih sensitif.",
    },
    "regime_weight_trending": {
        "icon": "📈",
        "label": "Weight Trending",
        "min": 0.1, "max": 3.0, "step": 0.1,
        "help": "Bobot sinyal saat market trending. Default 1.0. >1 = agresif saat trend, <1 = konservatif.",
    },
    "regime_weight_ranging": {
        "icon": "↔️",
        "label": "Weight Ranging",
        "min": 0.1, "max": 3.0, "step": 0.1,
        "help": "Bobot sinyal saat market ranging (sideways). Default 0.7. Lebih rendah = lebih hati-hati.",
    },
    "regime_weight_choppy": {
        "icon": "🌊",
        "label": "Weight Choppy",
        "min": 0.1, "max": 3.0, "step": 0.1,
        "help": "Bobot sinyal saat market choppy (tidak menentu). Default 0.5. Rendah = hindari false signal.",
    },
}


def _render_card(config, section: str, key: str, info: dict) -> bool:
    """Compact parameter card: description on left, input on right.

    Supports boolean toggles (when info has no "min" key)
    and numeric inputs (int or float) otherwise.
    """
    edited = False
    v = config.get(section, key)
    is_bool = "min" not in info
    is_int = not is_bool and isinstance(info.get("min"), int)
    fmt = info.get("format", None)

    with st.container(border=True):
        c1, c2 = st.columns([1.8, 1.2], vertical_alignment="center")
        with c1:
            st.markdown(f"**{info['icon']} {info['label']}**")
            st.caption(info.get("help", ""))
        with c2:
            if is_bool:
                nv = st.toggle(info["label"], value=bool(v),
                               key=f"agent_{key}", label_visibility="collapsed")
            elif is_int:
                nv = st.number_input(info["label"], info["min"], info["max"], int(v), int(info.get("step", 1)),
                                     key=f"agent_{key}", label_visibility="collapsed")
            else:
                step = info.get("step", 0.001)
                nv = st.number_input(info["label"], info["min"], info["max"], float(v), step,
                                     format=fmt, key=f"agent_{key}", label_visibility="collapsed")
        if nv != v:
            config.set(section, key, nv)
            edited = True
    return edited


def render(config) -> bool:
    edited = False

    # ── Signal Sources ──
    st.markdown(
        """
        <div class="info-banner">
            <div class="title">📡 Signal Sources & Agents</div>
            <div class="desc">Aktifkan sumber sinyal trading, atur threshold konsensus, dan konfigurasi Agent pipeline.
            Kombinasikan ML, Agent AI, dan Swarm untuk akurasi maksimal.</div>
        </div>
        """,
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

    st.markdown("---")

    # ── Agent Pipeline ──
    st.markdown("### 🤖 Agent Pipeline")
    st.caption("Konfigurasi pipeline agent untuk analisis multi-lapis: scout, risk audit, dan decision core.")

    # ── SMA Periods ──
    st.markdown("### 📊 SMA Periods")
    st.caption("Periode SMA untuk deteksi trend di Scout Agent — fast, medium, dan slow.")

    cols = st.columns(3)
    sma_keys = ["sma_fast_period", "sma_medium_period", "sma_slow_period"]
    for i, k in enumerate(sma_keys):
        with cols[i]:
            edited |= _render_card(config, "agent", k, AGENT_INFO[k])

    # ── Volatility ──
    st.markdown("---")
    st.markdown("### 🌊 Volatility Detection")
    st.caption("Parameter volatilitas untuk Risk Audit Agent — window, threshold high dan medium.")

    cols = st.columns(3)
    vol_keys = ["volatility_window", "volatility_high", "volatility_medium"]
    for i, k in enumerate(vol_keys):
        with cols[i]:
            edited |= _render_card(config, "agent", k, AGENT_INFO[k])

    # ── Position & Signal ──
    st.markdown("---")
    st.markdown("### 🎯 Position & Signal")
    st.caption("Ukuran posisi maksimal dan ambang momentum untuk entry signal.")

    cols = st.columns(2)
    with cols[0]:
        edited |= _render_card(config, "agent", "position_size", AGENT_INFO["position_size"])
    with cols[1]:
        edited |= _render_card(config, "agent", "momentum_threshold", AGENT_INFO["momentum_threshold"])

    # ── Regime Weights ──
    st.markdown("---")
    st.markdown("### ⚖️ Regime Weights")
    st.caption("Bobot keputusan berdasarkan regime pasar. Decision Core mengalikan momentum dengan weight sesuai regime.")

    cols = st.columns(3)
    weight_keys = ["regime_weight_trending", "regime_weight_ranging", "regime_weight_choppy"]
    for i, k in enumerate(weight_keys):
        with cols[i]:
            edited |= _render_card(config, "agent", k, AGENT_INFO[k])

    # ── Pipeline flowchart ──
    st.markdown("---")
    st.markdown(
        """
        <div style="font-family: 'Outfit', sans-serif; background: rgba(99,102,241,0.03);
             border: 1px solid rgba(99,102,241,0.12); border-radius: 12px; padding: 1rem 1.2rem;">
            <div style="font-size:0.9rem; font-weight:700; color:#a5b4fc; margin-bottom:8px;">
            🔄 Pipeline Flow</div>
            <div style="font-size:0.78rem; opacity:0.7; line-height:1.7;">
            <b>Scout Agent</b> → SMA cross + momentum + volatilitas<br>
            &nbsp;&nbsp;&nbsp;↓<br>
            <b>Risk Audit</b> → Validasi volatilitas vs threshold, tentukan ukuran posisi<br>
            &nbsp;&nbsp;&nbsp;↓<br>
            <b>Decision Core</b> → Kalibrasi sinyal dengan regime weight + momentum threshold → <b>BUY / SELL / HOLD</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return edited
