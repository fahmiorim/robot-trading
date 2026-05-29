import streamlit as st
import textwrap

from dashboard.helpers import get_available_symbols
from src.configuration import TIMEFRAME_MAP
from src.constants.mt5 import TRADE_MODE_LABELS
from src.exchange.helpers import get_symbol_trade_info



def render(config) -> bool:
    edited = False

    col1, col2 = st.columns(2)
    with col1:
        avail_symbols = get_available_symbols()
        if not avail_symbols:
            st.warning("\u26a0\ufe0f MT5 not connected \u2014 symbol list unavailable")
        current_sym = config.get("general", "symbol")
        if avail_symbols:
            sym_idx = avail_symbols.index(current_sym) if current_sym in avail_symbols else 0
            sym = st.selectbox("Symbol", avail_symbols, index=sym_idx)
        else:
            sym = st.text_input("Symbol", value=current_sym)
        if sym != current_sym:
            config.set("general", "symbol", sym)
            edited = True

        # Trade Mode indicator (live from MT5)
        _cfg_trade_mode = None
        _cfg_trade_info = None
        if st.session_state.mt5_initialized:
            try:
                _cfg_trade_info = get_symbol_trade_info(sym)
                _cfg_trade_mode = _cfg_trade_info.get('trade_mode') if _cfg_trade_info else None
            except Exception:
                pass
        _cfg_tm_label = TRADE_MODE_LABELS.get(_cfg_trade_mode, "UNKNOWN") if _cfg_trade_mode is not None else "\u2014"
        _cfg_tm_color = {0: '#ef5350', 1: '#42a5f5', 2: '#ffa726', 3: '#ef5350', 4: '#26a69a'}.get(_cfg_trade_mode, '#666')
        _cfg_tm_icon = {0: '\U0001f534', 1: '\U0001f535', 2: '\U0001f7e0', 3: '\U0001f534', 4: '\U0001f7e2'}.get(_cfg_trade_mode, '\u26aa')
        _cfg_tm_desc = {
            0: 'Trading disabled for this symbol',
            1: 'Only BUY orders allowed',
            2: 'Only SELL orders allowed',
            3: 'Only closing positions allowed',
            4: 'Both BUY and SELL allowed',
        }.get(_cfg_trade_mode, 'Unknown trade mode')
        _cfg_tm_vol = f"min={_cfg_trade_info['volume_min']}, step={_cfg_trade_info['volume_step']}" if _cfg_trade_info else "\u2014"

        st.markdown(textwrap.dedent(f"""
        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 0.5rem 0.8rem; margin-top: 0.5rem; font-size: 0.8rem;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                <span style="font-size: 1rem;">{_cfg_tm_icon}</span>
                <span style="font-weight: 700; color: {_cfg_tm_color};">{_cfg_tm_label}</span>
                <span style="opacity: 0.5; font-size: 0.7rem;">\u2014 {_cfg_tm_desc}</span>
            </div>
            <div style="display: flex; gap: 16px; font-size: 0.7rem; opacity: 0.45;">
                <span>\U0001f4e6 Volume: {_cfg_tm_vol}</span>
                <span>\U0001f522 Digits: {_cfg_trade_info.get('digits', '\u2014') if _cfg_trade_info else '\u2014'}</span>
            </div>
        </div>
        """), unsafe_allow_html=True)

    with col2:
        tf_options = list(TIMEFRAME_MAP.keys())
        current_tf = config.get("general", "timeframe")
        tf_idx = tf_options.index(current_tf) if current_tf in tf_options else 0
        tf = st.selectbox("Timeframe", tf_options, index=tf_idx, help="Cycle interval auto-syncs to timeframe (M1=1min, M5=5min, etc.)")
        if tf != current_tf:
            config.set("general", "timeframe", tf)
            tf_minutes = TIMEFRAME_MAP.get(tf, 15)
            config.set("general", "cycle_interval_minutes", tf_minutes)
            edited = True

        ci = TIMEFRAME_MAP.get(tf, 15)
        st.caption(f"\u23f1\ufe0f Cycle interval: **{ci} min** (auto)")

    col1, col2 = st.columns(2)
    with col1:
        dc = st.number_input("Data Count", 100, 100000, config.get("general", "data_count"), 1000)
        if dc != config.get("general", "data_count"):
            config.set("general", "data_count", dc)
            edited = True
    with col2:
        mn = st.number_input("Magic Number", 1, 999999, config.get("general", "magic_number"))
        if mn != config.get("general", "magic_number"):
            config.set("general", "magic_number", mn)
            edited = True

    return edited
