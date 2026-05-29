"""
RPC & API Settings Tab — premium glass cards with Indonesian descriptions.
Merged from REST API tab + WebSocket tab. Configure REST API server for
external access and WebSocket server for real-time dashboard streaming.
"""
import streamlit as st


API_INFO = {
    "enabled": {
        "icon": "\U0001f50c",
        "label": "Enable REST API",
        "help": "Aktifkan server REST API untuk akses eksternal. Nonaktifkan jika tidak digunakan untuk keamanan.",
    },
    "host": {
        "icon": "\U0001f310",
        "label": "REST API Host",
        "help": "IP address untuk binding server REST API. 0.0.0.0 = semua interface. 127.0.0.1 = localhost saja.",
    },
    "port": {
        "icon": "\U0001f50c",
        "label": "REST API Port",
        "min": 1024, "max": 65535, "step": 1,
        "help": "Port untuk REST API server. Default 8000. Pastikan port tidak dipakai aplikasi lain.",
    },
    "api_key": {
        "icon": "\U0001f511",
        "label": "API Key",
        "help": "API key untuk autentikasi request REST. Wajib diisi jika akses dari luar jaringan.",
    },
}

WS_INFO = {
    "host": {
        "icon": "\U0001f310",
        "label": "WebSocket Host",
        "help": "IP address untuk binding WebSocket server. 0.0.0.0 = semua interface. 127.0.0.1 = localhost saja.",
    },
    "port": {
        "icon": "\U0001f50c",
        "label": "WebSocket Port",
        "min": 1024, "max": 65535, "step": 1,
        "help": "Port untuk WebSocket server. Default 8765. Dashboard connect ke port ini untuk real-time data.",
    },
}


def _render_card(config, section: str, key: str, info: dict) -> bool:
    edited = False
    v = config.get(section, key)
    is_bool = isinstance(v, bool)

    with st.container(border=True):
        if is_bool:
            c1, c2 = st.columns([3, 1], vertical_alignment="center")
            with c1:
                st.markdown(f"**{info['icon']} {info['label']}**")
                st.caption(info.get("help", ""))
            with c2:
                nv = st.checkbox(info["label"], v, key=f"rpc_{section}_{key}", label_visibility="collapsed")
        elif key in ("api_key",):
            c1, c2 = st.columns([1.8, 1.2], vertical_alignment="center")
            with c1:
                st.markdown(f"**{info['icon']} {info['label']}**")
                st.caption(info.get("help", ""))
            with c2:
                nv = st.text_input(info["label"], str(v) if v else "",
                                   type="password", key=f"rpc_{section}_{key}", label_visibility="collapsed")
        else:
            c1, c2 = st.columns([1.8, 1.2], vertical_alignment="center")
            with c1:
                st.markdown(f"**{info['icon']} {info['label']}**")
                st.caption(info.get("help", ""))
            with c2:
                is_int = info.get("min") is not None and isinstance(info["min"], int)
                if is_int:
                    nv = st.number_input(info["label"], info["min"], info["max"], int(v), int(info.get("step", 1)),
                                         key=f"rpc_{section}_{key}", label_visibility="collapsed")
                else:
                    nv = st.text_input(info["label"], str(v) if v else "",
                                       key=f"rpc_{section}_{key}", label_visibility="collapsed")
        if nv != v:
            config.set(section, key, nv)
            edited = True
    return edited


def render(config) -> bool:
    edited = False
    rest_api_enabled = config.get("rest_api", "enabled")

    st.markdown(
        """
        <div class="info-banner">
            <div class="title">\U0001f4e1 RPC & API</div>
            <div class="desc">Konfigurasi server REST API dan WebSocket untuk akses eksternal dan streaming real-time.
            REST API menyediakan endpoint HTTP untuk kontrol trading. WebSocket digunakan dashboard untuk update otomatis.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── REST API ──
    st.markdown("### \U0001f50c REST API Server")
    st.caption("Akses eksternal ke data bot via HTTP. Nonaktifkan jika tidak digunakan.")

    edited |= _render_card(config, "rest_api", "enabled", API_INFO["enabled"])

    if rest_api_enabled:
        cols = st.columns(3)
        with cols[0]:
            edited |= _render_card(config, "rest_api", "host", API_INFO["host"])
        with cols[1]:
            edited |= _render_card(config, "rest_api", "port", API_INFO["port"])
        with cols[2]:
            edited |= _render_card(config, "rest_api", "api_key", API_INFO["api_key"])

        # ── Endpoint Info ──
        host_val = config.get("rest_api", "host")
        port_val = config.get("rest_api", "port")
        display_host = "localhost" if host_val in ("0.0.0.0", "127.0.0.1") else host_val
        st.markdown(
            f"""
            <div style="font-family: 'Outfit', sans-serif; background: rgba(99,102,241,0.03);
                 border: 1px solid rgba(99,102,241,0.12); border-radius: 12px; padding: 1rem 1.2rem; margin-top: 0.5rem;">
                <div style="font-size:0.9rem; font-weight:700; color:#a5b4fc; margin-bottom:8px;">
                \U0001f4e1 Available Endpoints</div>
                <div style="font-size:0.78rem; opacity:0.7; line-height:2;">
                <code>GET  http://{display_host}:{port_val}/status</code> — Status bot & koneksi<br>
                <code>GET  http://{display_host}:{port_val}/positions</code> — Daftar posisi terbuka<br>
                <code>GET  http://{display_host}:{port_val}/balance</code> — Informasi balance<br>
                <code>POST http://{display_host}:{port_val}/trade</code> — Eksekusi trade manual
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.warning(
            "⚠️ **Keamanan:** Jika host = 0.0.0.0, server dapat diakses dari perangkat lain "
            "di jaringan yang sama. Selalu gunakan API key untuk autentikasi."
        )
    else:
        st.info("\U0001f534 REST API dalam keadaan **nonaktif**. Aktifkan toggle di atas untuk mengakses pengaturan server.")

    # ── WebSocket ──
    st.markdown("---")
    st.markdown("### \U0001f4e1 WebSocket Server")
    st.caption("Streaming data real-time ke dashboard — update otomatis tanpa refresh manual.")

    cols = st.columns(2)
    with cols[0]:
        edited |= _render_card(config, "websocket", "host", WS_INFO["host"])
    with cols[1]:
        edited |= _render_card(config, "websocket", "port", WS_INFO["port"])

    host_val = config.get("websocket", "host")
    port_val = config.get("websocket", "port")
    display_host = "localhost" if host_val in ("0.0.0.0", "127.0.0.1") else host_val
    st.markdown(
        f"""
        <div style="font-family: 'Outfit', sans-serif; background: rgba(99,102,241,0.03);
             border: 1px solid rgba(99,102,241,0.12); border-radius: 12px; padding: 1rem 1.2rem; margin-top: 0.5rem;">
            <div style="font-size:0.9rem; font-weight:700; color:#a5b4fc; margin-bottom:8px;">
            \U0001f517 Connection Info</div>
            <div style="font-size:0.78rem; opacity:0.7; line-height:2;">
            <b>WebSocket URL:</b> <code>ws://{display_host}:{port_val}</code><br>
            <b>Data Pusher:</b> Mengirim data market, posisi, balance, dan sinyal real-time ke dashboard<br>
            <b>Auto-start:</b> WebSocket server otomatis menyala saat bot dijalankan
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        "💡 **Tip:** Dashboard Streamlit menggunakan WebSocket untuk fitur real-time. "
        "Pastikan port tidak terhalang firewall jika dashboard diakses dari perangkat lain."
    )

    return edited
