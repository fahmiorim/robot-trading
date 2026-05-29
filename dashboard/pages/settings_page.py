import streamlit as st
import textwrap

from dashboard.helpers import refresh_robot

from dashboard.pages.settings.general_tab import render as render_general
from dashboard.pages.settings.strategies_tab import render as render_strategies
from dashboard.pages.settings.risk_tab import render as render_risk
from dashboard.pages.settings.ml_tab import render as render_ml
from dashboard.pages.settings.agent_tab import render as render_agent
from dashboard.pages.settings.universal_tab import render as render_universal
from dashboard.pages.settings.timeframe_tab import render as render_timeframe


def render():
    st.title("\u2699\ufe0f Settings Editor")
    config = st.session_state.config
    edited = False

    # ── Sync context from current symbol/timeframe ────────────
    current_symbol = config.get("general", "symbol", default="XAUUSD")
    current_tf = config.get("general", "timeframe", default="TIMEFRAME_M15")
    config.set_context(current_symbol, current_tf)

    config_warnings = config.validate()

    # ── Context indicator badge ───────────────────────────────
    ctx_sym = config.context_symbol or "GLOBAL"
    ctx_tf = config.context_timeframe or "GLOBAL"
    ctx_label = f"{ctx_sym} / {ctx_tf}"
    is_global = config.context_symbol is None and config.context_timeframe is None

    st.markdown(
        textwrap.dedent(f"""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 1rem;
             background: linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.08));
             border: 1px solid rgba(99,102,241,0.2); border-radius: 12px; padding: 0.6rem 1.2rem;">
            <span style="font-size: 1.1rem;">{"🌐" if is_global else "🎯"}</span>
            <div style="flex: 1;">
                <span style="font-weight: 700; font-size: 0.95rem;">
                    {"Konfigurasi Global" if is_global else f"Konfigurasi: <span style='color: #818cf8;'>{ctx_label}</span>"}
                </span>
                <span style="opacity: 0.5; font-size: 0.75rem; margin-left: 10px;">
                    {"Berlaku untuk semua simbol/timeframe" if is_global else "Pengaturan khusus simbol/timeframe ini — override global"}
                </span>
            </div>
            <div style="font-size: 0.7rem; opacity: 0.4; text-align: right;">
                {config.get("trading", "mode", default="live")}
            </div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    tab_labels = [
        "\U0001f4cb General",
        "\u23f1\ufe0f Per-Timeframe",
        "\U0001f4c8 Strategies",
        "\U0001f6e1\ufe0f Risk & Protection",
        "\U0001f9e0 ML",
        "\U0001f916 Agent Pipeline",
        "\U0001f30d Universal",
    ]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        edited |= render_general(config)
    with tabs[1]:
        edited |= render_timeframe(config)
    with tabs[2]:
        edited |= render_strategies(config)
    with tabs[3]:
        edited |= render_risk(config)
    with tabs[4]:
        edited |= render_ml(config)
    with tabs[5]:
        edited |= render_agent(config)
    with tabs[6]:
        edited |= render_universal(config)

    # ── CONFIG WARNINGS ──────────────────────────────────────
    if config_warnings:
        with st.expander("\u26a0\ufe0f Config Warnings", expanded=True):
            for w in config_warnings:
                st.warning(w)

    # ── SAVE / RESET ─────────────────────────────────────────
    st.markdown("---")
    cs1, cs2, cs3 = st.columns([1, 1, 3])
    with cs1:
        if st.button("\U0001f4be Save Config", width='stretch', type="primary"):
            if config.save():
                refresh_robot(config)
                st.success("Saved & robot reloaded!")
            else:
                st.error("Save failed!")
    with cs2:
        if st.button("\U0001f504 Reset Defaults", width='stretch'):
            config.reset_to_defaults()
            config.save()
            refresh_robot(config)
            st.rerun()
    with cs3:
        if edited:
            st.info("\u26a1 Changes detected \u2014 click Save Config")
