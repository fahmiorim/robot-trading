"""
Health & Notifications Tab — premium glass cards with Indonesian descriptions.
"""
import streamlit as st
import textwrap

HC_INFO = {
    "enabled": {
        "icon": "🩺",
        "label": "Aktifkan Health Check",
        "help": "Monitor bot secara berkala untuk mendeteksi error, idle, atau kegagalan.",
    },
    "check_interval_seconds": {
        "icon": "⏱️",
        "label": "Interval Cek (detik)",
        "min": 10, "max": 600, "step": 10,
        "help": "Frekuensi pengecekan status bot. M1 cukup 30–60 detik.",
    },
    "max_consecutive_errors": {
        "icon": "❌",
        "label": "Max Error Beruntun",
        "min": 3, "max": 100, "step": 1,
        "help": "Jumlah error beruntun sebelum bot dianggap gagal. Scalping M1: 5 cukup — restart lebih cepat saat error beruntun.",
    },
    "max_idle_minutes": {
        "icon": "💤",
        "label": "Max Idle (menit)",
        "min": 5, "max": 240, "step": 5,
        "help": "Waktu tanpa aktivitas sebelum bot dianggap stalled. Scalping M1: 5–10 menit — cycle tiap 1 menit, jika 5 cycle tanpa trade bot dicurigai stalled.",
    },
    "auto_restart": {
        "icon": "🔄",
        "label": "Restart Otomatis",
        "help": "Restart bot otomatis jika terdeteksi gagal atau stalled.",
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
        "help": "ID chat atau grup Telegram untuk notifikasi.",
    },
    "notify_daily_report": {
        "icon": "📊",
        "label": "Laporan Harian",
        "help": "Kirim ringkasan performa trading setiap hari.",
    },
}


TLCMD_INFO = {
    "enabled": {
        "icon": "📱",
        "label": "Aktifkan Telegram CMD",
        "help": "Izinkan perintah Telegram untuk kontrol bot — /status, /positions, /trade, dll.",
    },
    "allowed_chat_ids": {
        "icon": "👤",
        "label": "Chat ID Diizinkan",
        "help": "Daftar chat ID yang diizinkan mengirim perintah Telegram. Pisahkan dengan koma. Contoh: 123456789, 987654321",
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
                nv = st.text_input(info["label"], str(v), key=f"{section}_{key}", label_visibility="collapsed",
                                   type="password" if "token" in key else None)
        if nv != v:
            config.set(section, key, nv)
            edited = True

    return edited


def _render_health(config) -> bool:
    st.markdown("### 🩺 Health Check")
    st.caption("Monitor kesehatan bot secara berkala — deteksi error, idle, dan kegagalan.")
    edited = False
    edited |= _render_card(config, "health_check", "enabled", HC_INFO["enabled"])
    if config.get("health_check", "enabled"):
        cols = st.columns(2)
        with cols[0]:
            edited |= _render_card(config, "health_check", "check_interval_seconds", HC_INFO["check_interval_seconds"])
            edited |= _render_card(config, "health_check", "max_consecutive_errors", HC_INFO["max_consecutive_errors"])
        with cols[1]:
            edited |= _render_card(config, "health_check", "max_idle_minutes", HC_INFO["max_idle_minutes"])
            edited |= _render_card(config, "health_check", "auto_restart", HC_INFO["auto_restart"])
    return edited


def _render_telegram_cmd(config) -> bool:
    edited = False
    st.markdown("### 📱 Telegram Commands")
    st.caption("Izinkan perintah Telegram untuk kontrol bot jarak jauh — /status, /positions, /trade, /balance.")
    edited |= _render_card(config, "telegram_cmd", "enabled", TLCMD_INFO["enabled"])
    if config.get("telegram_cmd", "enabled"):
        v = config.get("telegram_cmd", "allowed_chat_ids")
        original_val = v  # preserve original (list) for restore
        if isinstance(v, list):
            display_val = ", ".join(str(c) for c in v)
        else:
            display_val = str(v) if v else ""
        with st.container(border=True):
            c1, c2 = st.columns([1.8, 1.2], vertical_alignment="center")
            with c1:
                st.markdown(f"**{TLCMD_INFO['allowed_chat_ids']['icon']} {TLCMD_INFO['allowed_chat_ids']['label']}**")
                st.caption(TLCMD_INFO['allowed_chat_ids']['help'])
            with c2:
                nv = st.text_input(TLCMD_INFO['allowed_chat_ids']['label'], display_val,
                                   key="telegram_cmd_allowed_chat_ids", label_visibility="collapsed")
        if nv != display_val:
            try:
                chat_ids = [int(c.strip()) for c in nv.split(",") if c.strip()]
                config.set("telegram_cmd", "allowed_chat_ids", chat_ids)
                edited = True
            except ValueError:
                st.warning("⚠️ Chat ID harus berupa angka. Pisahkan dengan koma. Contoh: 123456789, 987654321")
                config.set("telegram_cmd", "allowed_chat_ids", original_val)
    return edited


def _render_notifications(config) -> bool:
    st.markdown("### 🔔 Notifikasi")
    st.caption("Kirim notifikasi trading ke Telegram — pantau posisi dan performa real-time.")
    edited = False
    edited |= _render_card(config, "notifications", "telegram_enabled", NOTIF_INFO["telegram_enabled"])
    if config.get("notifications", "telegram_enabled"):
        cols = st.columns(2)
        with cols[0]:
            edited |= _render_card(config, "notifications", "telegram_bot_token", NOTIF_INFO["telegram_bot_token"])
        with cols[1]:
            edited |= _render_card(config, "notifications", "telegram_chat_id", NOTIF_INFO["telegram_chat_id"])
        edited |= _render_card(config, "notifications", "notify_daily_report", NOTIF_INFO["notify_daily_report"])
    return edited


def render(config) -> bool:
    edited = False

    st.markdown(
        textwrap.dedent("""
        <div class="info-banner">
            <div class="title">🏥 Kesehatan & Notifikasi</div>
            <div class="desc">Pantau kondisi bot dan atur notifikasi Telegram. Pastikan bot berjalan sehat 24/7.</div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    edited |= _render_health(config)
    st.markdown("---")
    edited |= _render_notifications(config)
    st.markdown("---")
    edited |= _render_telegram_cmd(config)

    return edited
