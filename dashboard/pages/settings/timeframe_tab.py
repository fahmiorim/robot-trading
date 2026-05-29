"""
Per-Timeframe Settings Tab — comparison & quick-edit across all 9 timeframes.
Shows all TF-specific overrides in one place for power users.
"""
import streamlit as st
import pandas as pd
from typing import Any, Dict, List, Tuple

# ── Constants ──────────────────────────────────────────────────

ALL_TFS: List[str] = [
    "TIMEFRAME_M1", "TIMEFRAME_M5", "TIMEFRAME_M15", "TIMEFRAME_M30",
    "TIMEFRAME_H1", "TIMEFRAME_H4", "TIMEFRAME_D1", "TIMEFRAME_W1", "TIMEFRAME_MN",
]

TF_SHORT: Dict[str, str] = {
    "TIMEFRAME_M1": "M1", "TIMEFRAME_M5": "M5", "TIMEFRAME_M15": "M15",
    "TIMEFRAME_M30": "M30", "TIMEFRAME_H1": "H1", "TIMEFRAME_H4": "H4",
    "TIMEFRAME_D1": "D1", "TIMEFRAME_W1": "W1", "TIMEFRAME_MN": "MN",
}

TF_HEADERS: List[str] = [TF_SHORT[tf] for tf in ALL_TFS]


# ── Batch read/write helpers ──────────────────────────────────


def _read_tf_values(config, section: str, keys: List[str]) -> Dict[str, List[Any]]:
    """Batch-read all param values for all TFs with minimal context switches.

    Reads TF-wide overrides (None, tf) for cross-TF comparison.
    Per-symbol+TF overrides are NOT reflected here — they are edited
    through the individual Settings tabs (Risk, ML, Agent, etc.)
    where context is already symbol-specific.
    """
    current_sym = config.context_symbol
    current_tf = config.context_timeframe

    data: Dict[str, List[Any]] = {}
    for tf in ALL_TFS:
        config.set_context(None, tf)
        row = [config.get(section, key) for key in keys]
        data[TF_SHORT[tf]] = row

    config.set_context(current_sym, current_tf)
    return data


def _save_tf_value(config, section: str, key: str, tf: str, value: Any) -> None:
    """Save a single value as TF-wide override (applies to all symbols).

    Uses (None, tf) context so the override is timeframe-wide, not symbol-specific.
    For per-symbol+TF overrides, edit through the individual Settings tabs.
    """
    current_sym = config.context_symbol
    current_tf = config.context_timeframe
    config.set_context(None, tf)
    config.set(section, key, value)
    config.set_context(current_sym, current_tf)


# ── Categories ─────────────────────────────────────────────────
# (section, icon, label, [(key, display_name, value_type)])

# Essential params — selalu tampil, sering di-tuning per TF
CATEGORIES_BASIC: List[Tuple[str, str, str, List[Tuple[str, str, str]]]] = [
    ("general", "⚙️", "General", [
        ("data_count", "Data Count", "int"),
        ("cycle_interval_minutes", "Cycle (menit)", "int"),
    ]),
    ("risk_management", "📊", "Risk Parameter", [
        ("position_size_pct", "Position Size (%)", "float"),
        ("stop_loss_pct", "Stop Loss (%)", "float"),
        ("take_profit_pct", "Take Profit (%)", "float"),
        ("cooldown_minutes", "Cooldown (menit)", "int"),
        ("max_open_positions", "Max Open", "int"),
    ]),
    ("agent", "🤖", "Agent SMA", [
        ("sma_fast_period", "SMA Fast", "int"),
        ("sma_medium_period", "SMA Medium", "int"),
        ("sma_slow_period", "SMA Slow", "int"),
    ]),
]

# Advanced params — disembunyikan di balik toggle, jarang diubah
CATEGORIES_ADVANCED: List[Tuple[str, str, str, List[Tuple[str, str, str]]]] = [
    ("risk_management", "📊", "Risk — Trailing & CB", [
        ("trailing_stop_activation_pct", "Trailing Activation (%)", "float"),
        ("trailing_stop_distance_pct", "Trailing Distance (%)", "float"),
        ("circuit_breaker_loss_pct", "CB Loss (%)", "float"),
        ("circuit_breaker_cooldown_minutes", "CB Cooldown (menit)", "int"),
    ]),
    ("risk_management", "📊", "Risk — Volatility", [
        ("volatility_threshold", "Volatility Threshold", "float"),
    ]),
    ("protection", "🛡️", "Protection", [
        ("max_stoploss", "Max Stoploss", "int"),
        ("stoploss_window_hours", "SL Window (jam)", "int"),
    ]),
    ("ml", "🧠", "ML Tuning", [
        ("max_depth", "Max Depth", "int"),
        ("atr_multiplier", "ATR Multiplier", "float"),
        ("retrain_interval_hours", "Retrain (jam)", "int"),
    ]),
    ("agent", "🤖", "Agent — Volatility & Momentum", [
        ("volatility_high", "Volatility High", "float"),
        ("volatility_medium", "Volatility Medium", "float"),
        ("momentum_threshold", "Momentum Threshold", "float"),
    ]),
    ("features", "📐", "Features", [
        ("rsi_period", "RSI Period", "int"),
        ("bb_period", "BB Period", "int"),
        ("bb_std_dev", "BB Std Dev", "float"),
    ]),
    ("dca", "🔄", "DCA", [
        ("dca_cooldown_minutes", "DCA Cooldown (menit)", "int"),
        ("dca_trigger_pct", "DCA Trigger (%)", "float"),
    ]),
    ("health_check", "🩺", "Health Check", [
        ("check_interval_seconds", "Check Interval (detik)", "int"),
        ("max_consecutive_errors", "Max Errors", "int"),
        ("max_idle_minutes", "Max Idle (menit)", "int"),
    ]),
    ("performance", "📈", "Performa", [
        ("periods_per_year", "Periods/Year", "int"),
    ]),
]


def _render_category(config, section: str, icon: str, label: str,
                     params: List[Tuple[str, str, str]]) -> bool:
    """Render a category section as an editable ``st.data_editor`` table."""
    edited = False

    keys = [k for k, _, _ in params]
    param_names = [pn for _, pn, _ in params]

    data = _read_tf_values(config, section, keys)
    df = pd.DataFrame(data, index=param_names)

    # Build column config — NumberColumn with compact width
    col_config = {}
    for tf_s in TF_HEADERS:
        col_config[tf_s] = st.column_config.NumberColumn(
            tf_s, width="small", disabled=False,
        )

    h = min(35 * len(params) + 40, 300)

    st.markdown(f"### {icon} {label}")

    edited_df = st.data_editor(
        df,
        column_config=col_config,
        use_container_width=True,
        height=h,
        key=f"tf_editor_{section}_{label.lower().replace(' ', '_')}",
        num_rows="fixed",
    )

    # Detect changes and save
    for param_name in edited_df.index:
        orig_row = df.loc[param_name]
        new_row = edited_df.loc[param_name]
        for tf_s in TF_HEADERS:
            old_val = orig_row[tf_s]
            new_val = new_row[tf_s]

            # Skip NaN → NaN
            if pd.isna(old_val) and pd.isna(new_val):
                continue
            if not pd.isna(old_val) and not pd.isna(new_val) and old_val == new_val:
                continue

            # Locate original key and TF
            idx = list(df.index).index(param_name)
            param_key = keys[idx]
            _, _, vtype = params[idx]

            tf_key = next(tf for tf in ALL_TFS if TF_SHORT[tf] == tf_s)

            if pd.isna(new_val):
                continue
            typed_val = int(new_val) if vtype == "int" else float(new_val)

            _save_tf_value(config, section, param_key, tf_key, typed_val)
            edited = True

    if edited:
        st.caption("✏️ Perubahan langsung disimpan — klik **Save Config** untuk persist ke database.")

    return edited


# ── Reset helpers ─────────────────────────────────────────────


def _reset_single_tf(config, tf: str) -> None:
    """Reset all overrides for a single timeframe."""
    config.reset_timeframe_overrides(tf)
    st.toast(f"✅ Override **{TF_SHORT[tf]}** dihapus → global default", icon="🔄")
    st.rerun()


def _reset_all_tfs(config) -> None:
    """Reset all timeframe overrides globally."""
    config.reset_to_defaults()
    st.session_state.confirm_reset_all = False
    st.toast("✅ Semua override timeframe dihapus → global default", icon="🔄")
    st.rerun()


# ── Main render ───────────────────────────────────────────────


def render(config) -> bool:
    edited = False

    st.markdown("""
    <div class="info-banner">
        <div class="title">⏱️ Per-Timeframe Comparison</div>
        <div class="desc">
            Lihat dan edit parameter <b>semua 9 timeframe</b> secara berdampingan.
            Parameter yang belum memiliki override timeframe akan menampilkan nilai global default.
            Perubahan langsung disimpan, perlu klik <b>Save Config</b> untuk persist ke database.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.info(
        "💡 **Tip:** Gunakan tab ini untuk menyelaraskan parameter "
        "antar timeframe secara sekilas.",
        icon="⏱️",
    )

    # ── Reset buttons ───────────────────────────────────────────
    st.markdown("### 🔄 Reset Timeframe Overrides")

    col_all, *tf_cols = st.columns([1.5] + [1] * 9)

    with col_all:
        st.caption("Reset All")
        if st.button("⚠️ Reset All", type="primary", use_container_width=True,
                     help="Hapus SEMUA override di semua timeframe → kembali ke global default"):
            if "confirm_reset_all" not in st.session_state:
                st.session_state.confirm_reset_all = True
                st.rerun()

    for i, tf_key in enumerate(ALL_TFS):
        with tf_cols[i]:
            st.caption(f"Reset {TF_SHORT[tf_key]}")
            if st.button(f"↺ {TF_SHORT[tf_key]}", use_container_width=True,
                         key=f"reset_{tf_key}",
                         help=f"Hapus semua override **{TF_SHORT[tf_key]}** → kembali ke global default"):
                _reset_single_tf(config, tf_key)

    if st.session_state.get("confirm_reset_all"):
        st.warning("⚠️ Yakin ingin **menghapus semua override timeframe**? Tindakan ini tidak bisa dibatalkan.")
        c1, c2, _ = st.columns([1, 1, 6])
        with c1:
            if st.button("✅ Ya, Reset All", type="primary", use_container_width=True):
                _reset_all_tfs(config)
        with c2:
            if st.button("❌ Batal", use_container_width=True):
                st.session_state.confirm_reset_all = False
                st.rerun()

    st.markdown("---")

    # ── Basic parameters (always visible) ───────────────────────
    st.markdown("### 📋 Parameter Utama")
    st.caption("Parameter yang sering di-tuning per timeframe.")

    for section, icon, label, params in CATEGORIES_BASIC:
        edited |= _render_category(config, section, icon, label, params)
        st.markdown("---")

    # ── Advanced parameters (toggle) ────────────────────────────
    show_advanced = st.toggle(
        "🔬 Tampilkan Advanced Parameters",
        value=st.session_state.get("show_advanced_tf", False),
        key="show_advanced_tf",
        help="Menampilkan parameter yang jarang diubah: trailing, CB, ML tuning, protection, health, dll.",
    )

    if show_advanced:
        st.markdown("### ⚙️ Parameter Lanjutan")
        st.caption(
            "Parameter ini umumnya **set & forget** — "
            "default sudah terkalibrasi per timeframe. Hanya ubah jika Anda paham dampaknya."
        )

        for section, icon, label, params in CATEGORIES_ADVANCED:
            edited |= _render_category(config, section, icon, label, params)
            st.markdown("---")

    return edited
