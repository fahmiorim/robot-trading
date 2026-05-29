"""
Trading Settings Tab — premium glass cards with Indonesian descriptions.
Merged from Order tab: order_types, contract_size, stoploss_limit_slip.
"""
import streamlit as st

MODE_INFO = {
    "mode": {
        "icon": "🔀",
        "label": "Mode Trading",
        "help": "Pilih mode trading: live (real money) atau paper (simulasi).",
    },
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
    "paper_lot_size": {
        "icon": "📦",
        "label": "Paper Lot Size",
        "min": 0.01, "max": 10.0, "step": 0.01,
        "help": "Ukuran lot untuk paper trading. 0.01 = micro lot. 0.1 = mini lot. 1.0 = standard lot.",
    },
    "paper_order_delay_ms": {
        "icon": "⏱️",
        "label": "Paper Order Delay (ms)",
        "min": 0, "max": 10000, "step": 100,
        "help": "Simulasi delay eksekusi order dalam milidetik. 500 ms realistis untuk broker rata-rata.",
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

ORDER_INFO = {
    "custom": {
        "icon": "\u2699\ufe0f",
        "label": "Custom Order Types",
        "help": "Aktifkan tipe order kustom. Jika nonaktif, gunakan market order standar.",
    },
    "use_stop_loss_limit": {
        "icon": "\U0001f6d1",
        "label": "Stop-Loss Limit",
        "help": "Gunakan stop-loss limit order untuk proteksi. Order entry + limit order di dekat SL.",
    },
    "use_oco": {
        "icon": "\U0001f517",
        "label": "OCO Orders",
        "help": "Gunakan One-Cancels-Other order: SL dan TP dipasang bersamaan. Jika satu terisi, yang lain otomatis dibatalkan.",
    },
    "contract_size": {
        "icon": "\U0001f4e6",
        "label": "Contract Size",
        "min": 0.1, "max": 1000.0, "step": 0.1,
        "help": "Ukuran kontrak per lot untuk perhitungan P&L paper trading. Default 100 (XAUUSD standard). XAUUSD mini: 10.",
    },
    "stoploss_limit_slip": {
        "icon": "\U0001f4cf",
        "label": "SL Limit Slip",
        "min": 0.0, "max": 0.1, "step": 0.001, "format": "%.3f",
        "help": "Jarak slip untuk stop-loss limit order (fraction). 0.001 = 0.1% dari harga SL. Untuk menghindari gagal eksekusi.",
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
        "help": "Maksimal jumlah DCA per posisi. Scalping M1: 2–3 cukup. Makin banyak makin berisiko.",
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
        if is_bool:
            c1, c2 = st.columns([3, 1], vertical_alignment="center")
            with c1:
                st.markdown(f"**{info['icon']} {info['label']}**")
                st.caption(info.get('help', ''))
            with c2:
                nv = st.checkbox(info["label"], v, key=f"{section}_{key}", label_visibility="collapsed")
        else:
            col1, col2 = st.columns([0.65, 0.35], vertical_alignment="center")
            with col1:
                st.markdown(f"**{info['icon']} {info['label']}**")
                st.caption(info.get('help', ''))
            with col2:
                if is_int:
                    nv = st.number_input(info["label"], info["min"], info["max"], int(v), int(info.get("step", 1)),
                                         key=f"{section}_{key}", label_visibility="collapsed")
                else:
                    nv = st.number_input(info["label"], info["min"], info["max"], float(v), info.get("step", 1.0),
                                         format=fmt, key=f"{section}_{key}", label_visibility="collapsed")
        if nv != v:
            config.set(section, key, nv)
            edited = True

    return edited


# ── Order Execution sub-render ────────────────────────────────


def _render_order_execution(config) -> bool:
    edited = False

    st.markdown("---")
    st.markdown("### \u2699\ufe0f Order Execution")
    st.caption("Tipe order kustom, ukuran kontrak, dan parameter eksekusi.")

    st.info(
        "**Alur OCO:** Entry market order \u2192 pasang SL & TP bersamaan (OCO). "
        "Jika SL terisi, TP otomatis dibatalkan (dan sebaliknya).\\n\\n"
        "**Alur Stop-Loss-Limit:** Entry market order \u2192 pasang limit order di dekat harga SL. "
        "Mencegah slippage saat SL tereksekusi di pasar cepat."
    )

    edited |= _render_card(config, "order_types", "custom", ORDER_INFO["custom"])
    edited |= _render_card(config, "order_types", "use_stop_loss_limit", ORDER_INFO["use_stop_loss_limit"])
    edited |= _render_card(config, "order_types", "use_oco", ORDER_INFO["use_oco"])

    cols = st.columns(2)
    with cols[0]:
        edited |= _render_card(config, "order", "contract_size", ORDER_INFO["contract_size"])
    with cols[1]:
        edited |= _render_card(config, "order", "stoploss_limit_slip", ORDER_INFO["stoploss_limit_slip"])

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

    # Mode: live / paper
    mode_val = config.get("trading", "mode")
    mode_opts = ["live", "paper"]
    mode_idx = mode_opts.index(mode_val) if mode_val in mode_opts else 0
    with st.container(border=True):
        c1, c2 = st.columns([1.8, 1.2], vertical_alignment="center")
        with c1:
            st.markdown(f"**{MODE_INFO['mode']['icon']} {MODE_INFO['mode']['label']}**")
            st.caption(MODE_INFO['mode']['help'])
        with c2:
            nv = st.selectbox(MODE_INFO['mode']['label'], mode_opts, mode_idx, key="trading_mode", label_visibility="collapsed")
    if nv != mode_val:
        config.set("trading", "mode", nv)
        edited = True
        st.rerun()

    edited |= _render_card(config, "trading", "paper_trading", MODE_INFO["paper_trading"])
    if config.get("trading", "paper_trading") or config.get("trading", "mode") == "paper":
        cols = st.columns(3)
        with cols[0]:
            edited |= _render_card(config, "trading", "paper_initial_balance", MODE_INFO["paper_initial_balance"])
        with cols[1]:
            edited |= _render_card(config, "trading", "paper_lot_size", MODE_INFO["paper_lot_size"])
        with cols[2]:
            edited |= _render_card(config, "trading", "paper_order_delay_ms", MODE_INFO["paper_order_delay_ms"])

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

    # ── Order Execution (merged from Order tab) ──
    edited |= _render_order_execution(config)

    # ── DCA (merged from former DCA tab) ──
    with st.expander("🔄 Dollar-Cost Averaging", expanded=False):
        st.caption(
            "Strategi menambah posisi saat harga bergerak berlawanan untuk menurunkan harga rata-rata entry. "
            "Cocok untuk market ranging, tapi berisiko tinggi di trend kuat."
        )

        edited |= _render_card(config, "dca", "enabled", DCA_INFO["enabled"])

        if config.get("dca", "enabled"):
            st.markdown("### ⚙️ Parameter DCA")
            st.caption("Atur trigger, ukuran, dan batasan DCA sesuai toleransi risiko.")
            dca_keys = [
                "max_dca_orders", "dca_trigger_pct", "dca_cooldown_minutes",
                "dca_increment_factor", "dca_position_limit_pct",
            ]
            cols = st.columns(2)
            for i, k in enumerate(dca_keys):
                with cols[i % 2]:
                    edited |= _render_card(config, "dca", k, DCA_INFO[k])

            st.markdown(
                """
                <div style="background: rgba(99,102,241,0.05); border: 1px solid rgba(99,102,241,0.15);
                     border-radius: 12px; padding: 1rem; margin-top: 0.5rem; font-size: 0.85rem; line-height: 1.8;">
                    <div style="opacity: 0.8;">📌 <b>Entry</b> — 0.10 lot @ $2000</div>
                    <div style="opacity: 0.8;">📉 <b>DCA #1</b> — +0.15 lot @ $1980 (harga turun 1%)</div>
                    <div style="opacity: 0.7;">📉 <b>DCA #2</b> — +0.23 lot @ $1960</div>
                    <div style="opacity: 0.6;">📉 <b>DCA #3</b> — +0.34 lot @ $1940</div>
                    <div style="margin-top: 8px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px; opacity: 0.9;">
                        🎯 <b>Total:</b> 0.82 lot | <b>Rata-rata:</b> ~$1965 | <b>Profit di:</b> $1975 (+0.5%)
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    return edited
