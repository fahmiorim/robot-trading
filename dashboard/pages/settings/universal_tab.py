"""
Universal Settings Tab — settings that are NOT tied to any symbol/timeframe.
All edits use ``config.set_global()`` so they always save to global context,
regardless of the active symbol/timeframe in the dashboard.

These settings behave identically across all pairs and timeframes.
"""

import streamlit as st


# ── Info dictionaries (icon, label, help, min/max/step/format) ──

EXCHANGE_INFO = {
    "type": {
        "icon": "🏦",
        "label": "Exchange Type",
        "help": "Jenis exchange. mt5 = MetaTrader 5, bybit = Bybit.",
    },
}

TRADING_INFO = {
    "mode": {
        "icon": "🔀",
        "label": "Mode Trading",
        "help": "live = real money, paper = simulasi.",
    },
    "paper_trading": {
        "icon": "📝",
        "label": "Paper Trading",
        "help": "Simulasi trading tanpa uang asli.",
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
        "help": "Ukuran lot untuk paper trading.",
    },
    "paper_order_delay_ms": {
        "icon": "⏱️",
        "label": "Paper Delay (ms)",
        "min": 0, "max": 10000, "step": 100,
        "help": "Simulasi delay eksekusi order dalam ms.",
    },
}

SIGNAL_INFO = {
    "use_ml": {
        "icon": "🤖",
        "label": "Sinyal ML",
        "help": "Gunakan model ML untuk sinyal trading.",
    },
    "use_agent": {
        "icon": "🧠",
        "label": "Sinyal Agent AI",
        "help": "Gunakan agent pipeline untuk sinyal.",
    },
    "use_swarm": {
        "icon": "🐝",
        "label": "Sinyal Swarm",
        "help": "Ensemble strategi dengan voting berbobot.",
    },
    "consensus_buy_threshold": {
        "icon": "📈",
        "label": "Batas Buy",
        "min": -1.0, "max": 1.0, "step": 0.05,
        "help": "Skor minimum untuk trigger BUY.",
    },
    "consensus_sell_threshold": {
        "icon": "📉",
        "label": "Batas Sell",
        "min": -1.0, "max": 0.0, "step": 0.05,
        "help": "Skor maksimum untuk trigger SELL.",
    },
}

BACKTEST_INFO = {
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
        "help": "Biaya komisi per trade.",
    },
    "slippage_pct": {
        "icon": "📉",
        "label": "Slippage (%)",
        "min": 0.0, "max": 5.0, "step": 0.01,
        "help": "Selisih harga eksekusi.",
    },
}


ORDER_INFO = {
    "contract_size": {
        "icon": "📦",
        "label": "Contract Size",
        "min": 0.1, "max": 1000.0, "step": 0.1,
        "help": "Ukuran kontrak per lot. XAUUSD = 100.",
    },
}

HEALTH_INFO = {
    "enabled": {
        "icon": "🩺",
        "label": "Health Check Aktif",
        "help": "Monitor bot secara berkala.",
    },
    "auto_restart": {
        "icon": "🔄",
        "label": "Restart Otomatis",
        "help": "Restart bot jika terdeteksi gagal.",
    },
}

CB_INFO = {
    "circuit_breaker_enabled": {
        "icon": "🛡️",
        "label": "Circuit Breaker Aktif",
        "help": "Matikan trading otomatis jika rugi cepat.",
    },
    "circuit_breaker_loss_pct": {
        "icon": "📉",
        "label": "Batas Rugi Cepat (%)",
        "min": 1.0, "max": 50.0, "step": 1.0,
        "help": "Kerugian dalam window yang memicu CB.",
    },
}

NOTIF_INFO = {
    "telegram_enabled": {
        "icon": "📱",
        "label": "Telegram Aktif",
        "help": "Kirim notifikasi trading ke Telegram.",
    },
    "telegram_bot_token": {
        "icon": "🔑",
        "label": "Token Bot",
        "help": "Token bot Telegram dari @BotFather.",
    },
    "telegram_chat_id": {
        "icon": "👤",
        "label": "Chat ID",
        "help": "ID chat/grup Telegram untuk notifikasi.",
    },
    "notify_daily_report": {
        "icon": "📊",
        "label": "Laporan Harian",
        "help": "Kirim ringkasan performa harian.",
    },
}

TLCMD_INFO = {
    "enabled": {
        "icon": "📱",
        "label": "Telegram CMD Aktif",
        "help": "Perintah Telegram untuk kontrol bot.",
    },
    "allowed_chat_ids": {
        "icon": "👤",
        "label": "Chat ID Diizinkan",
        "help": "Daftar chat ID (pisahkan koma).",
    },
}

RPC_INFO = {
    "enabled": {
        "icon": "🔌",
        "label": "REST API Aktif",
        "help": "Aktifkan server REST API.",
    },
    "host": {
        "icon": "🌐",
        "label": "REST Host",
        "help": "IP binding server REST API.",
    },
    "port": {
        "icon": "🔌",
        "label": "REST Port",
        "min": 1024, "max": 65535, "step": 1,
        "help": "Port REST API server.",
    },
    "api_key": {
        "icon": "🔑",
        "label": "API Key",
        "help": "API key untuk autentikasi.",
    },
}

WS_INFO = {
    "host": {
        "icon": "🌐",
        "label": "WS Host",
        "help": "IP binding WebSocket server.",
    },
    "port": {
        "icon": "🔌",
        "label": "WS Port",
        "min": 1024, "max": 65535, "step": 1,
        "help": "Port WebSocket server.",
    },
}


# ── _card: renders a single parameter card using set_global() ──


def _card(config, section: str, key: str, info: dict) -> bool:
    """Render a single parameter card.
    Uses ``config.set_global()`` so changes always save as global defaults.
    """
    edited = False
    v = config.get(section, key)
    is_bool = isinstance(v, bool)
    is_int = not is_bool and info.get("min") is not None and isinstance(info["min"], int)
    fmt = info.get("format", None)

    has_range = "min" in info

    with st.container(border=True):
        c1, c2 = st.columns([1.8, 1.2], vertical_alignment="center")
        with c1:
            st.markdown(f"**{info['icon']} {info['label']}**")
            st.caption(info.get("help", ""))
        with c2:
            if is_bool:
                nv = st.checkbox(info["label"], v, key=f"univ_{section}_{key}",
                                 label_visibility="collapsed")
            elif key in ("host",):
                opts = ["0.0.0.0", "127.0.0.1", "localhost"]
                idx = opts.index(v) if v in opts else 0
                nv = st.selectbox(info["label"], opts, idx,
                                  key=f"univ_{section}_{key}", label_visibility="collapsed")
            elif key == "mode":
                opts = ["live", "paper"]
                idx = opts.index(v) if v in opts else 0
                nv = st.selectbox(info["label"], opts, idx,
                                  key=f"univ_{section}_{key}", label_visibility="collapsed")
            elif key in ("telegram_bot_token", "api_key"):
                nv = st.text_input(info["label"], str(v) if v else "",
                                   type="password", key=f"univ_{section}_{key}",
                                   label_visibility="collapsed")
            elif key == "type" and section == "exchange":
                opts = ["mt5", "bybit", "ccxt"]
                idx = opts.index(v) if v in opts else 0
                nv = st.selectbox(info["label"], opts, idx,
                                  key=f"univ_{section}_{key}", label_visibility="collapsed")
            elif has_range and is_int:
                nv = st.number_input(info["label"], info["min"], info["max"], int(v),
                                     int(info.get("step", 1)),
                                     key=f"univ_{section}_{key}", label_visibility="collapsed")
            elif has_range:
                step = info.get("step", 0.1)
                nv = st.number_input(info["label"], info["min"], info["max"], float(v),
                                     step, format=fmt,
                                     key=f"univ_{section}_{key}", label_visibility="collapsed")
            else:
                # Fallback: string text input for anything else
                nv = st.text_input(info["label"], str(v) if v is not None else "",
                                   key=f"univ_{section}_{key}", label_visibility="collapsed")
        if nv != v:
            ok = config.set_global(section, key, nv)
            if ok:
                edited = True
            else:
                st.error(f"❌ Gagal menyimpan {section}.{key} — cek koneksi database.")
    return edited


def _section(config, section: str, info_map: dict, keys: list) -> bool:
    """Render a 2-column grid of cards for a list of keys."""
    edited = False
    cols = st.columns(2)
    for i, key in enumerate(keys):
        if key in info_map:
            with cols[i % 2]:
                edited |= _card(config, section, key, info_map[key])
    return edited


def _render_exchange(config) -> bool:
    st.markdown("### 🏦 Exchange")
    st.caption("Jenis exchange backend — berlaku untuk semua simbol.")
    return _section(config, "exchange", EXCHANGE_INFO,
                    ["type"])


def _render_trading_mode(config) -> bool:
    edited = False

    st.markdown("### 💹 Trading Mode & Validasi")
    st.caption("Mode live/paper, validasi strategi — sama di semua context.")

    edited |= _card(config, "trading", "mode", TRADING_INFO["mode"])
    edited |= _card(config, "trading", "paper_trading", TRADING_INFO["paper_trading"])

    if config.get("trading", "paper_trading") or config.get("trading", "mode") == "paper":
        cols = st.columns(3)
        with cols[0]:
            edited |= _card(config, "trading", "paper_initial_balance", TRADING_INFO["paper_initial_balance"])
        with cols[1]:
            edited |= _card(config, "trading", "paper_lot_size", TRADING_INFO["paper_lot_size"])
        with cols[2]:
            edited |= _card(config, "trading", "paper_order_delay_ms", TRADING_INFO["paper_order_delay_ms"])

    return edited


def _render_order(config) -> bool:
    st.markdown("### ⚙️ Order & Eksekusi")
    st.caption("Ukuran kontrak per lot — global untuk semua trading.")
    edited = _card(config, "order", "contract_size", ORDER_INFO["contract_size"])
    return edited


def _render_signal_sources(config) -> bool:
    st.markdown("### 📡 Sumber Sinyal")
    st.caption("Engine sinyal dan threshold konsensus — berlaku global.")
    edited = _section(config, "signals", SIGNAL_INFO,
                      ["use_ml", "use_agent", "use_swarm",
                       "consensus_buy_threshold", "consensus_sell_threshold"])
    return edited


def _render_backtest(config) -> bool:
    st.markdown("### 📊 Backtest & Performa")
    st.caption("Parameter backtest dan metrik performa — global.")
    edited = _section(config, "backtest", BACKTEST_INFO,
                      ["initial_balance", "commission_pct", "slippage_pct"])
    # risk_free_rate hidden from UI — uses standard 0.02
    return edited


def _render_health(config) -> bool:
    st.markdown("### 🩺 Health Check")
    st.caption("Monitoring bot — sama di semua kondisi market.")
    edited = _card(config, "health_check", "enabled", HEALTH_INFO["enabled"])
    if config.get("health_check", "enabled"):
        edited |= _card(config, "health_check", "auto_restart", HEALTH_INFO["auto_restart"])
    return edited


def _render_protection(config) -> bool:
    edited = False
    st.markdown("### 🛡️ Circuit Breaker")
    st.caption("Matikan trading otomatis jika rugi cepat — melindungi saldo di semua context.")

    edited |= _card(config, "risk_management", "circuit_breaker_enabled", CB_INFO["circuit_breaker_enabled"])
    if config.get("risk_management", "circuit_breaker_enabled"):
        edited |= _card(config, "risk_management", "circuit_breaker_loss_pct", CB_INFO["circuit_breaker_loss_pct"])

    return edited


def _render_notifications(config) -> bool:
    edited = False
    st.markdown("### 🔔 Notifikasi & Telegram")
    st.caption("Notifikasi trading dan perintah Telegram — global.")
    edited |= _card(config, "notifications", "telegram_enabled", NOTIF_INFO["telegram_enabled"])
    if config.get("notifications", "telegram_enabled"):
        cols = st.columns(2)
        with cols[0]:
            edited |= _card(config, "notifications", "telegram_bot_token", NOTIF_INFO["telegram_bot_token"])
        with cols[1]:
            edited |= _card(config, "notifications", "telegram_chat_id", NOTIF_INFO["telegram_chat_id"])
        edited |= _card(config, "notifications", "notify_daily_report", NOTIF_INFO["notify_daily_report"])

    st.markdown("---")
    edited |= _card(config, "telegram_cmd", "enabled", TLCMD_INFO["enabled"])
    if config.get("telegram_cmd", "enabled"):
        v = config.get("telegram_cmd", "allowed_chat_ids")
        display_val = ", ".join(str(c) for c in v) if isinstance(v, list) else (str(v) if v else "")
        with st.container(border=True):
            c1, c2 = st.columns([1.8, 1.2], vertical_alignment="center")
            with c1:
                st.markdown(f"**{TLCMD_INFO['allowed_chat_ids']['icon']} {TLCMD_INFO['allowed_chat_ids']['label']}**")
                st.caption(TLCMD_INFO['allowed_chat_ids']['help'])
            with c2:
                nv = st.text_input(TLCMD_INFO['allowed_chat_ids']['label'], display_val,
                                   key="univ_telegram_cmd_chat_ids", label_visibility="collapsed")
        if nv != display_val:
            try:
                chat_ids = [int(c.strip()) for c in nv.split(",") if c.strip()]
                config.set_global("telegram_cmd", "allowed_chat_ids", chat_ids)
                edited = True
            except ValueError:
                st.warning("⚠️ Chat ID harus berupa angka. Pisahkan dengan koma.")
    return edited


def _render_rpc(config) -> bool:
    edited = False
    st.markdown("### 📡 RPC & API")
    st.caption("REST API dan WebSocket server — konfigurasi global.")

    edited |= _card(config, "rest_api", "enabled", RPC_INFO["enabled"])
    if config.get("rest_api", "enabled"):
        cols = st.columns(3)
        with cols[0]:
            edited |= _card(config, "rest_api", "host", RPC_INFO["host"])
        with cols[1]:
            edited |= _card(config, "rest_api", "port", RPC_INFO["port"])
        with cols[2]:
            edited |= _card(config, "rest_api", "api_key", RPC_INFO["api_key"])

    st.markdown("---")
    cols = st.columns(2)
    with cols[0]:
        edited |= _card(config, "websocket", "host", WS_INFO["host"])
    with cols[1]:
        edited |= _card(config, "websocket", "port", WS_INFO["port"])

    return edited


# ── Main render ───────────────────────────────────────────────


def render(config) -> bool:
    edited = False

    st.markdown(
        """
        <div class="info-banner">
            <div class="title">🌍 Pengaturan Universal</div>
            <div class="desc">
                Setting di tab ini <b>TIDAK TERIKAT</b> dengan simbol atau timefram —
                nilainya sama di semua context. Perubahan langsung disimpan sebagai
                <b>global default</b> tanpa perlu tombol Save.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        "💡 **Semua perubahan di tab ini langsung disimpan ke global** — "
        "tidak perlu klik tombol Save di bagian bawah halaman. "
        "Setting ini berlaku untuk SEMUA simbol dan timeframe.",
        icon="🌍",
    )

    edited |= _render_exchange(config)
    st.markdown("---")
    edited |= _render_trading_mode(config)
    st.markdown("---")
    edited |= _render_order(config)
    st.markdown("---")
    edited |= _render_signal_sources(config)
    st.markdown("---")
    edited |= _render_backtest(config)
    st.markdown("---")
    edited |= _render_health(config)
    st.markdown("---")
    edited |= _render_protection(config)
    st.markdown("---")
    edited |= _render_notifications(config)
    st.markdown("---")
    edited |= _render_rpc(config)

    # ── Reset Global Defaults ───────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔄 Reset Global Defaults")
    st.caption("Kembalikan semua parameter Universal ke nilai factory default dari schema.sql. Context-specific override (TF/symbol) tidak terpengaruh.")

    if st.button("⚠️ Reset Global Defaults", type="primary",
                 help="Hapus semua global default dan re-seed dari schema.sql → factory defaults"):
        if "confirm_reset_global" not in st.session_state:
            st.session_state.confirm_reset_global = True
            st.rerun()

    if st.session_state.get("confirm_reset_global"):
        st.warning(
            "⚠️ **Yakin ingin mereset semua global default ke factory?** "
            "Tindakan ini tidak bisa dibatalkan. "
            "Override timeframe/symbol tidak terpengaruh."
        )
        c1, c2, _ = st.columns([1, 1, 6])
        with c1:
            if st.button("✅ Ya, Reset", type="primary", use_container_width=True, key="yes_reset_global"):
                config.reset_global_defaults()
                st.session_state.confirm_reset_global = False
                st.toast("✅ Global defaults kembali ke factory default", icon="🔄")
                st.rerun()
        with c2:
            if st.button("❌ Batal", use_container_width=True, key="no_reset_global"):
                st.session_state.confirm_reset_global = False
                st.rerun()

    return edited
