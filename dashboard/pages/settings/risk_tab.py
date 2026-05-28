import streamlit as st


def _render_circuit_breaker(config) -> bool:
    edited = False
    st.subheader("🛡️ Circuit Breaker")
    cb_enabled = st.checkbox("Circuit Breaker Enabled",
                             config.get("risk_management", "circuit_breaker_enabled"))
    if cb_enabled != config.get("risk_management", "circuit_breaker_enabled"):
        config.set("risk_management", "circuit_breaker_enabled", cb_enabled)
        edited = True
    if cb_enabled:
        cb1, cb2, cb3 = st.columns(3)
        with cb1:
            v = config.get("risk_management", "circuit_breaker_loss_pct")
            nv = st.number_input("Rapid Loss %", 1.0, 50.0, float(v), 1.0, help="Trigger CB if loss exceeds this % within window")
            if nv != v:
                config.set("risk_management", "circuit_breaker_loss_pct", nv)
                edited = True
        with cb2:
            v = config.get("risk_management", "circuit_breaker_window_minutes")
            nv = st.number_input("Window (min)", 5, 1440, int(v), 5, help="Time window to measure loss")
            if nv != v:
                config.set("risk_management", "circuit_breaker_window_minutes", nv)
                edited = True
        with cb3:
            v = config.get("risk_management", "circuit_breaker_cooldown_minutes")
            nv = st.number_input("Cooldown (min)", 10, 1440, int(v), 10, help="Time before auto-reset")
            if nv != v:
                config.set("risk_management", "circuit_breaker_cooldown_minutes", nv)
                edited = True
    return edited


def _render_risk_params(config) -> bool:
    edited = False
    st.subheader("📊 Risk Parameters")
    risk_keys = [
        ("position_size_pct", "Position Size %", 0.1, 50.0, 2.0),
        ("max_daily_loss_pct", "Max Daily Loss %", 0.1, 50.0, 5.0),
        ("max_drawdown_pct", "Max Drawdown %", 0.1, 100.0, 15.0),
        ("max_open_positions", "Max Positions", 1, 50, 3),
        ("cooldown_minutes", "Cooldown (min)", 0, 60, 1),
        ("stop_loss_pct", "Stop Loss %", 0.1, 20.0, 1.5),
        ("take_profit_pct", "Take Profit %", 0.1, 50.0, 3.0),
    ]
    risk_cols = st.columns(3)
    for i, (k, label, mn, mx, default) in enumerate(risk_keys):
        v = config.get("risk_management", k)
        with risk_cols[i % 3]:
            nv = st.number_input(label, mn, mx, float(v) if isinstance(default, float) else int(v),
                                 step=0.1 if isinstance(default, float) else 1, key=f"risk_{k}")
            if nv != v:
                config.set("risk_management", k, nv)
                edited = True
    return edited


def _render_trailing_stop(config) -> bool:
    edited = False
    st.subheader("🎯 Trailing Stop")
    ts = config.get("risk_management", "use_trailing_stop")
    ts_new = st.checkbox("Use Trailing Stop", ts)
    if ts_new != ts:
        config.set("risk_management", "use_trailing_stop", ts_new)
        edited = True
    if ts_new:
        c1, c2 = st.columns(2)
        with c1:
            v = config.get("risk_management", "trailing_stop_activation_pct")
            nv = st.number_input("Activation %", 0.1, 20.0, float(v), 0.1)
            if nv != v:
                config.set("risk_management", "trailing_stop_activation_pct", nv)
                edited = True
        with c2:
            v = config.get("risk_management", "trailing_stop_distance_pct")
            nv = st.number_input("Distance %", 0.1, 10.0, float(v), 0.1)
            if nv != v:
                config.set("risk_management", "trailing_stop_distance_pct", nv)
                edited = True
    return edited


def render(config) -> bool:
    edited = False
    edited |= _render_circuit_breaker(config)
    st.markdown("---")
    edited |= _render_risk_params(config)
    st.markdown("---")
    edited |= _render_trailing_stop(config)
    return edited
