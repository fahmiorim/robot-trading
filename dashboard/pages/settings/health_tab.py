import streamlit as st


def _render_notifications(config) -> bool:
    edited = False
    st.subheader("\U0001f514 Notifications")
    nc1, nc2 = st.columns(2)
    with nc1:
        v = config.get("notifications", "telegram_enabled")
        nv = st.checkbox("Telegram Enabled", v)
        if nv != v:
            config.set("notifications", "telegram_enabled", nv)
            edited = True
    with nc2:
        v = config.get("notifications", "notify_on_trade")
        nv = st.checkbox("Notify on Trade", v)
        if nv != v:
            config.set("notifications", "notify_on_trade", nv)
            edited = True

    v = config.get("notifications", "notify_daily_report")
    nv = st.checkbox("Notify Daily Report", v)
    if nv != v:
        config.set("notifications", "notify_daily_report", nv)
        edited = True

    v = config.get("notifications", "telegram_bot_token")
    nv = st.text_input("Bot Token", v, type="password")
    if nv != v:
        config.set("notifications", "telegram_bot_token", nv)
        edited = True

    v = config.get("notifications", "telegram_chat_id")
    nv = st.text_input("Chat ID", v)
    if nv != v:
        config.set("notifications", "telegram_chat_id", nv)
        edited = True
    return edited


def render(config) -> bool:
    edited = False

    st.subheader("\U0001f3e5 Health Check")
    hc1, hc2 = st.columns(2)
    with hc1:
        hc_enabled = config.get("health_check", "enabled")
        nv = st.checkbox("Health Check Enabled", hc_enabled)
        if nv != hc_enabled:
            config.set("health_check", "enabled", nv)
            edited = True
    with hc2:
        v = config.get("health_check", "auto_restart")
        nv = st.checkbox("Auto Restart on Failure", v)
        if nv != v:
            config.set("health_check", "auto_restart", nv)
            edited = True
    if hc_enabled:
        hc3, hc4, hc5 = st.columns(3)
        with hc3:
            v2 = config.get("health_check", "check_interval_seconds")
            nv = st.number_input("Check Interval (s)", 10, 600, int(v2), 10)
            if nv != v2:
                config.set("health_check", "check_interval_seconds", nv)
                edited = True
        with hc4:
            v2 = config.get("health_check", "max_consecutive_errors")
            nv = st.number_input("Max Errors", 3, 100, int(v2))
            if nv != v2:
                config.set("health_check", "max_consecutive_errors", nv)
                edited = True
        with hc5:
            v2 = config.get("health_check", "max_idle_minutes")
            nv = st.number_input("Max Idle (min)", 5, 240, int(v2), 5)
            if nv != v2:
                config.set("health_check", "max_idle_minutes", nv)
                edited = True

    st.markdown("---")
    edited |= _render_notifications(config)

    return edited
