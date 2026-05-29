"""
Trading Settings Tab — premium glass cards with Indonesian descriptions.
"""
import streamlit as st

MODE_INFO = {
    "paper_trading": {
        "icon": "📝",
        "label": "Mode Paper Trading",
        "help": "Simulasi trading tanpa uang asli — cocok untuk uji strategi di live market.",
    },
    "paper_initial_balance": {
        "icon": "💰",
        "label": "Saldo Awal Paper",
        "min": 100.0, "max": 1_000_000.0, "step": 100.0,
        "help": "Saldo awal untuk simulasi paper trading.",
    },
}

VALIDATION_INFO = {
    "strategy_pre_validation": {
        "icon": "🔬",
        "label": "Validasi Strategi",
        "help": "Nonaktifkan otomatis strategi yang gagal backtest sebelum dipakai trading.",
    },
    "min_backtest_trades": {
        "icon": "📊",
        "label": "Min Trade Backtest",
        "min": 1, "max": 100, "step": 1,
        "help": "Jumlah minimal trade dalam backtest. M1: minimal 20 agar signifikan.",
    },
    "min_win_rate": {
        "icon": "📈",
        "label": "Min Win Rate (%)",
        "min": 0.0, "max": 100.0, "step": 1.0,
        "help": "Win rate minimal. Scalping: 35% cukup dengan R:R 1:2.",
    },
    "max_backtest_drawdown": {
        "icon": "⚠️",
        "label": "Max Drawdown Backtest (%)",
        "min": 5.0, "max": 100.0, "step": 1.0,
        "help": "Drawdown maksimal yang ditoleransi dalam backtest.",
    },
    "max_consecutive_losses": {
        "icon": "🔴",
        "label": "Max Rugi Beruntun",
        "min": 1, "max": 50, "step": 1,
        "help": "Hentikan trading setelah rugi beruntun sebanyak ini.",
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
            elif is_int:
                nv = st.number_input(info["label"], info["min"], info["max"], int(v), int(info.get("step", 1)),
                                     key=f"{section}_{key}", label_visibility="collapsed")
            else:
                nv = st.number_input(info["label"], info["min"], info["max"], float(v), info.get("step", 1.0),
                                     key=f"{section}_{key}", label_visibility="collapsed")
        if nv != v:
            config.set(section, key, nv)
            edited = True

    return edited


def render(config) -> bool:
    edited = False

    st.markdown(
        """
        <div class="info-banner">
            <div class="title">💹 Pengaturan Trading</div>
            <div class="desc">Atur mode trading, saldo paper, dan validasi strategi otomatis sebelum dieksekusi.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 💹 Mode Trading")
    st.caption("Pilih live atau paper trading — paper trading aman untuk uji strategi.")

    edited |= _render_card(config, "trading", "paper_trading", MODE_INFO["paper_trading"])
    if config.get("trading", "paper_trading"):
        edited |= _render_card(config, "trading", "paper_initial_balance", MODE_INFO["paper_initial_balance"])

    st.markdown("---")
    st.markdown("### 🔬 Validasi Strategi")
    st.caption("Nonaktifkan strategi buruk otomatis sebelum merugikan saldo.")

    edited |= _render_card(config, "trading", "strategy_pre_validation", VALIDATION_INFO["strategy_pre_validation"])
    if config.get("trading", "strategy_pre_validation"):
        cols = st.columns(2)
        with cols[0]:
            edited |= _render_card(config, "trading", "min_backtest_trades", VALIDATION_INFO["min_backtest_trades"])
            edited |= _render_card(config, "trading", "min_win_rate", VALIDATION_INFO["min_win_rate"])
        with cols[1]:
            edited |= _render_card(config, "trading", "max_backtest_drawdown", VALIDATION_INFO["max_backtest_drawdown"])
            edited |= _render_card(config, "trading", "max_consecutive_losses", VALIDATION_INFO["max_consecutive_losses"])

    return edited
