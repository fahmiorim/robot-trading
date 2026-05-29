"""
Risk Settings Tab — premium glass cards with Indonesian descriptions.
"""
import streamlit as st
import textwrap

RISK_INFO = {
    "position_size_pct": {
        "icon": "📊",
        "label": "Ukuran Posisi",
        "min": 0.1, "max": 50.0, "step": 0.5,
        "help": "Persentase saldo yang digunakan per posisi. Untuk scalping M1–M15 disarankan 1–3%.",
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
        "help": "Jumlah maksimum posisi yang bisa dibuka secara bersamaan.",
    },
    "cooldown_minutes": {
        "icon": "⏳",
        "label": "Cooldown (menit)",
        "min": 0, "max": 60, "step": 1,
        "help": "Waktu tunggu setelah posisi ditutup sebelum bisa entry lagi. M1 cukup 0–1 menit.",
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
        "help": "Persentase keuntungan untuk menutup otomatis. Idealnya 2–3x stop loss.",
    },
}

CB_INFO = {
    "circuit_breaker_enabled": {
        "icon": "🛡️",
        "label": "Aktifkan Circuit Breaker",
        "help": "Matikan trading otomatis jika terjadi kerugian cepat dalam waktu singkat.",
    },
    "circuit_breaker_loss_pct": {
        "icon": "📉",
        "label": "Batas Rugi Cepat (%)",
        "min": 1.0, "max": 50.0, "step": 1.0,
        "help": "Persentase kerugian dalam window tertentu yang memicu circuit breaker.",
    },
    "circuit_breaker_window_minutes": {
        "icon": "⏱️",
        "label": "Jendela Waktu (menit)",
        "min": 5, "max": 1440, "step": 5,
        "help": "Durasi jendela untuk mengukur kerugian cepat. Scalping: 15–30 menit.",
    },
    "circuit_breaker_cooldown_minutes": {
        "icon": "🔄",
        "label": "Cooldown CB (menit)",
        "min": 10, "max": 1440, "step": 10,
        "help": "Waktu tunggu sebelum circuit breaker di-reset otomatis.",
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
        "help": "Keuntungan minimum sebelum trailing stop aktif. Scalping: 0.3–0.5%.",
    },
    "trailing_stop_distance_pct": {
        "icon": "📏",
        "label": "Jarak Trailing (%)",
        "min": 0.1, "max": 10.0, "step": 0.1,
        "help": "Jarak stop loss dari harga tertinggi setelah trailing aktif.",
    },
}


def _render_card(config, section: str, key: str, info: dict) -> bool:
    edited = False
    v = config.get(section, key)
    is_bool = isinstance(v, bool)
    is_int = not is_bool and info.get("min") is not None and isinstance(info["min"], int)

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
                                         key=f"{section}_{key}", label_visibility="collapsed")
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


def _render_circuit_breaker(config) -> bool:
    st.markdown("### 🛡️ Circuit Breaker")
    st.caption("Melindungi saldo dari kerugian cepat dengan menghentikan trading otomatis.")
    keys = ["circuit_breaker_enabled", "circuit_breaker_loss_pct",
            "circuit_breaker_window_minutes", "circuit_breaker_cooldown_minutes"]
    edited = _render_section(config, "risk_management", CB_INFO, keys)
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


def render(config) -> bool:
    edited = False

    st.markdown(
        textwrap.dedent("""
        <div class="info-banner">
            <div class="title">🛡️ Manajemen Risiko</div>
            <div class="desc">Atur parameter risiko, trailing stop, circuit breaker, dan ROI take-profit. Semua nilai disesuaikan untuk scalping timeframe M1–M15.</div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    edited |= _render_risk_params(config)
    st.markdown("---")
    edited |= _render_circuit_breaker(config)
    st.markdown("---")
    edited |= _render_trailing_stop(config)
    st.markdown("---")
    edited |= _render_roi(config)

    return edited
