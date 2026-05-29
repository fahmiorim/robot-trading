"""
Risk Settings Tab — premium glass cards with Indonesian descriptions.
Merged from Protection tab and DCA tab.
"""
import streamlit as st
import textwrap

RISK_INFO = {
    "position_size_pct": {
        "icon": "📊",
        "label": "Ukuran Posisi",
        "min": 0.1, "max": 50.0, "step": 0.5,
        "help": "Persentase saldo yang digunakan per posisi. Scalping M1-M15: 1–2%. 1.5% default — kompromi antara growth dan safety untuk frekuensi tinggi.",
    },
    "max_daily_loss_pct": {
        "icon": "📉",
        "label": "Max Rugi Harian",
        "min": 0.1, "max": 50.0, "step": 1.0,
        "help": "Batas rugi total per hari. Trading otomatis berhenti jika terlampaui.",
    },
    "max_drawdown_pct": {
        "icon": "⚠️",
        "label": "Max Drawdown",
        "min": 0.1, "max": 100.0, "step": 1.0,
        "help": "Penarikan maksimum dari saldo puncak. Jika terlampaui, semua posisi ditutup.",
    },
    "max_open_positions": {
        "icon": "📂",
        "label": "Max Posisi Terbuka",
        "min": 1, "max": 50, "step": 1,
        "help": "Jumlah maksimum posisi yang bisa dibuka bersamaan. Scalping M1-M15: 2–3 cukup — lebih dari itu sulit dikelola dan meningkatkan drawdown kumulatif.",
    },
    "cooldown_minutes": {
        "icon": "⏳",
        "label": "Cooldown (menit)",
        "min": 0, "max": 60, "step": 1,
        "help": "Waktu tunggu setelah posisi ditutup sebelum bisa entry lagi. M1: 1 menit cukup — mencegah overtrading tanpa menghambat scalping frekuensi tinggi.",
    },
    "stop_loss_pct": {
        "icon": "🛑",
        "label": "Stop Loss (%)",
        "min": 0.1, "max": 20.0, "step": 0.1,
        "help": "Persentase kerugian per posisi untuk menutup otomatis. Scalping: 0.3–0.8%.",
    },
    "take_profit_pct": {
        "icon": "✅",
        "label": "Take Profit (%)",
        "min": 0.1, "max": 50.0, "step": 0.1,
        "help": "Persentase keuntungan untuk menutup otomatis. Scalping M1: 0.5–0.8% (target cepat), M5-M15: 0.8–1.5%. Idealnya 1.5–2x SL.",
    },
}

TS_INFO = {
    "use_trailing_stop": {
        "icon": "🎯",
        "label": "Aktifkan Trailing Stop",
        "help": "Stop loss otomatis mengikuti harga saat posisi bergerak profit.",
    },
    "trailing_stop_activation_pct": {
        "icon": "🚀",
        "label": "Aktivasi Trailing (%)",
        "min": 0.1, "max": 20.0, "step": 0.1,
        "help": "Keuntungan minimum sebelum trailing stop aktif. Scalping M1-M15: 0.3–0.5%. Default 0.5% — pastikan ini LEBIH KECIL dari TP (0.8%) agar trailing benar-benar aktif.",
    },
    "trailing_stop_distance_pct": {
        "icon": "📏",
        "label": "Jarak Trailing (%)",
        "min": 0.1, "max": 10.0, "step": 0.1,
        "help": "Jarak stop loss dari harga tertinggi setelah trailing aktif.",
    },
}

REGIME_INFO = {
    "adx_period": {
        "icon": "📈",
        "label": "ADX Period",
        "min": 5, "max": 50, "step": 1,
        "help": "Periode ADX untuk deteksi kekuatan tren. 14 standar. M1: 14 = 14 menit lookback.",
    },
    "adx_threshold": {
        "icon": "📊",
        "label": "ADX Threshold",
        "min": 5.0, "max": 50.0, "step": 1.0,
        "help": "Batas ADX untuk klasifikasi regime. 25 = di atas 25 trending, di bawah 25 ranging/choppy.",
    },
    "window_size": {
        "icon": "🪟",
        "label": "Window Size",
        "min": 5, "max": 100, "step": 5,
        "help": "Jumlah candle untuk regresi linear slope. M1: 20 = 20 menit. Lebih besar = lebih smooth.",
    },
    "slope_threshold": {
        "icon": "📐",
        "label": "Slope Threshold",
        "min": 0.001, "max": 0.1, "step": 0.001, "format": "%.3f",
        "help": "Batas minimum slope regresi untuk deteksi tren. 0.01 = slope 1% per window. Makin kecil makin sensitif.",
    },
    "volatility_threshold": {
        "icon": "🌊",
        "label": "Volatility Threshold",
        "min": 0.001, "max": 0.05, "step": 0.001, "format": "%.3f",
        "help": "Batas volatilitas utk membedakan ranging vs choppy. M1-M15 noise tinggi — 0.005 (0.5%) mengurangi false choppy. Di atas threshold = choppy, di bawah = ranging.",
    },
}

DCA_INFO = {
    "enabled": {
        "icon": "🔄",
        "label": "Aktifkan DCA",
        "help": "Dollar-Cost Averaging — menambah posisi saat harga bergerak berlawanan untuk meratakan harga entry.",
    },
    "max_dca_orders": {
        "icon": "📊",
        "label": "Max DCA Orders",
        "min": 1, "max": 10, "step": 1,
        "help": "Maksimal jumlah DCA per posisi. Scalping M1: 2-3 cukup. Makin banyak makin berisiko.",
    },
    "dca_trigger_pct": {
        "icon": "📉",
        "label": "Trigger DCA (%)",
        "min": -10.0, "max": -0.1, "step": 0.1,
        "help": "Kerugian % yang memicu DCA. -1.0 artinya harga turun 1% dari entry baru DCA aktif.",
    },
    "dca_cooldown_minutes": {
        "icon": "⏳",
        "label": "Cooldown DCA (menit)",
        "min": 1, "max": 120, "step": 1,
        "help": "Jeda antar DCA untuk posisi yang sama. M1: 3-5 menit agar tidak keburu entry lagi.",
    },
    "dca_increment_factor": {
        "icon": "📈",
        "label": "Faktor Increment",
        "min": 1.0, "max": 5.0, "step": 0.1,
        "help": "Kelipatan volume tiap level DCA. 1.5x: lot ke-2 = 1.5x lot awal. Makin besar makin agresif.",
    },
    "dca_position_limit_pct": {
        "icon": "⚠️",
        "label": "Limit Posisi (%)",
        "min": 1.0, "max": 50.0, "step": 1.0,
        "help": "Batas maksimal total exposure posisi dari balance. 20% artinya total posisi tidak boleh > 20% saldo.",
    },
}


def _render_card(config, section: str, key: str, info: dict) -> bool:
    edited = False
    v = config.get(section, key)
    is_bool = isinstance(v, bool)
    is_int = not is_bool and info.get("min") is not None and isinstance(info["min"], int)
    fmt = info.get("format", None)

    with st.container(border=True):
        col1, col2 = st.columns([0.65, 0.35], vertical_alignment="center")
        with col1:
            st.markdown(f"**{info['icon']} {info['label']}**")
            st.caption(info.get('help', ''))
        with col2:
            if is_bool:
                nv = st.checkbox(info["label"], v, key=f"{section}_{key}", label_visibility="collapsed")
            else:
                step = info.get("step", 0.1)
                if is_int:
                    nv = st.number_input(info["label"], info["min"], info["max"], int(v), int(step),
                                         key=f"{section}_{key}", label_visibility="collapsed")
                else:
                    nv = st.number_input(info["label"], info["min"], info["max"], float(v), step,
                                         format=fmt, key=f"{section}_{key}", label_visibility="collapsed")
        if nv != v:
            config.set(section, key, nv)
            edited = True

    return edited


def _render_section(config, section: str, info_map: dict, keys: list) -> bool:
    edited = False
    cols = st.columns(2)
    for i, key in enumerate(keys):
        if key in info_map:
            with cols[i % 2]:
                edited |= _render_card(config, section, key, info_map[key])
    return edited


def _render_risk_params(config) -> bool:
    st.markdown("### 📊 Parameter Risiko")
    st.caption("Atur toleransi risiko, ukuran posisi, dan batasan trading harian.")
    keys = ["position_size_pct", "max_daily_loss_pct", "max_drawdown_pct",
            "max_open_positions", "cooldown_minutes", "stop_loss_pct",
            "take_profit_pct"]
    edited = _render_section(config, "risk_management", RISK_INFO, keys)
    return edited


def _render_trailing_stop(config) -> bool:
    edited = False
    st.markdown("### 🎯 Trailing Stop")
    st.caption("Stop loss otomatis yang mengikuti harga saat posisi bergerak profit.")
    edited |= _render_card(config, "risk_management", "use_trailing_stop", TS_INFO["use_trailing_stop"])
    if config.get("risk_management", "use_trailing_stop"):
        for key in ["trailing_stop_activation_pct", "trailing_stop_distance_pct"]:
            edited |= _render_card(config, "risk_management", key, TS_INFO[key])
    return edited


def _render_roi(config) -> bool:
    edited = False
    st.markdown("### 💰 ROI Take-Profit")
    st.caption("Target profit bertingkat berdasarkan lama posisi terbuka — makin lama makin ketat.")

    roi_enabled = config.get("roi", "enabled")
    with st.container(border=True):
        col1, col2 = st.columns([0.65, 0.35], vertical_alignment="center")
        with col1:
            st.markdown(f"**{'✅' if roi_enabled else '⛔'} ROI Take-Profit**")
            st.caption("Matikan jika hanya ingin pakai TP tetap.")
        with col2:
            nv = st.checkbox("Enable ROI", roi_enabled, key="roi_enabled", label_visibility="collapsed")
    if nv != roi_enabled:
        config.set("roi", "enabled", nv)
        edited = True
        st.rerun()

    if nv:
        table = config.get("roi", "table")
        st.markdown(
            textwrap.dedent("""
            <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 0.6rem 1rem;">
                <div style="display: flex; gap: 6px; margin-bottom: 0.3rem; padding-bottom: 0.3rem; border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <div style="flex: 1; text-align: left; font-size: 0.7rem; font-weight: 600; opacity: 0.6;">Menit</div>
                    <div style="flex: 1; text-align: left; font-size: 0.7rem; font-weight: 600; opacity: 0.6;">ROI %</div>
                    <div style="flex: 0 0 30px;"></div>
                </div>
            """),
            unsafe_allow_html=True,
        )
        new_table = list(table)
        for i, row in enumerate(table):
            mc1, mc2 = st.columns([1, 1])
            with mc1:
                mins = st.number_input("Menit", value=row["minutes"], min_value=0,
                                       key=f"roi_min_{i}", label_visibility="collapsed")
            with mc2:
                pct = st.number_input("ROI %", value=float(row["roi_pct"]), min_value=0.0,
                                      format="%.1f", key=f"roi_pct_{i}", label_visibility="collapsed")
            new_table[i] = {"minutes": mins, "roi_pct": pct}
        if new_table != table:
            config.set("roi", "table", new_table)
            edited = True
        st.markdown("</div>", unsafe_allow_html=True)

    return edited


def _render_dca(config) -> bool:
    edited = False
    st.markdown("### 🔄 Dollar-Cost Averaging")
    st.caption("Strategi menambah posisi saat harga bergerak berlawanan untuk menurunkan harga rata-rata entry. Cocok untuk market ranging, tapi berisiko tinggi di trend kuat.")

    edited |= _render_card(config, "dca", "enabled", DCA_INFO["enabled"])

    if config.get("dca", "enabled"):
        dca_keys = [
            "max_dca_orders", "dca_trigger_pct", "dca_cooldown_minutes",
            "dca_increment_factor", "dca_position_limit_pct",
        ]
        cols = st.columns(2)
        for i, k in enumerate(dca_keys):
            with cols[i % 2]:
                edited |= _render_card(config, "dca", k, DCA_INFO[k])

        st.markdown(
            '<div style="background: rgba(99,102,241,0.05); border: 1px solid rgba(99,102,241,0.15);'
            '     border-radius: 12px; padding: 1rem; margin-top: 0.5rem; font-size: 0.85rem; line-height: 1.8;">'
            '<div style="opacity: 0.8;">📌 <b>Entry</b> — 0.10 lot @ $2000</div>'
            '<div style="opacity: 0.8;">📉 <b>DCA #1</b> — +0.15 lot @ $1980 (harga turun 1%)</div>'
            '<div style="opacity: 0.7;">📉 <b>DCA #2</b> — +0.23 lot @ $1960</div>'
            '<div style="opacity: 0.6;">📉 <b>DCA #3</b> — +0.34 lot @ $1940</div>'
            '<div style="margin-top: 8px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px; opacity: 0.9;">'
            "🎯 <b>Total:</b> 0.82 lot | <b>Rata-rata:</b> ~$1965 | <b>Profit di:</b> $1975 (+0.5%)"
            "</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    return edited


def _render_regime_detection(config) -> bool:
    edited = False
    st.markdown("### 📊 Regime Detection")
    st.caption(
        "Parameter ADX, regresi slope, dan threshold volatilitas untuk deteksi regime market. "
        "Mengklasifikasikan market menjadi trending, ranging, atau choppy secara otomatis."
    )

    cols = st.columns(3)
    with cols[0]:
        edited |= _render_card(config, "risk_management", "adx_period", REGIME_INFO["adx_period"])
    with cols[1]:
        edited |= _render_card(config, "risk_management", "adx_threshold", REGIME_INFO["adx_threshold"])
    with cols[2]:
        edited |= _render_card(config, "risk_management", "window_size", REGIME_INFO["window_size"])

    cols = st.columns(2)
    with cols[0]:
        edited |= _render_card(config, "risk_management", "slope_threshold", REGIME_INFO["slope_threshold"])
    with cols[1]:
        edited |= _render_card(config, "risk_management", "volatility_threshold", REGIME_INFO["volatility_threshold"])

    return edited


def render(config) -> bool:
    edited = False

    st.markdown(
        textwrap.dedent("""
        <div class="info-banner">
            <div class="title">🛡️ Manajemen Risiko & Proteksi</div>
            <div class="desc">Atur parameter risiko, circuit breaker, trailing stop, ROI take-profit, DCA, dan stoploss guard. Semua nilai disesuaikan untuk scalping timeframe M1–M15.</div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    edited |= _render_risk_params(config)
    st.markdown("---")
    edited |= _render_trailing_stop(config)
    st.markdown("---")
    edited |= _render_roi(config)
    st.markdown("---")
    edited |= _render_dca(config)
    st.markdown("---")
    edited |= _render_regime_detection(config)

    return edited
