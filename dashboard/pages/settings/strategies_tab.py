"""
Premium Strategies Tab — styled glass cards with param bounds & heat-map weight matrix.
"""
import streamlit as st
import textwrap

# ── Strategy metadata ─────────────────────────────────────────
STRATEGY_INFO = {
    "MA_Crossover": {
        "icon": "\U0001f4c8",
        "desc": "Buy saat MA cepat crossing di atas MA lambat, Sell saat sebaliknya.",
        "params": {
            "fast_period": {"label": "Fast MA Period", "min": 3, "max": 40, "step": 1, "help": "Periode MA cepat untuk deteksi tren"},
            "slow_period": {"label": "Slow MA Period", "min": 10, "max": 80, "step": 1, "help": "Periode MA lambat — harus > fast period"},
        },
    },
    "RSI": {
        "icon": "\U0001f4ca",
        "desc": "Buy saat RSI oversold, Sell saat RSI overbought.",
        "params": {
            "period": {"label": "RSI Period", "min": 7, "max": 21, "step": 1, "help": "Jumlah candle untuk kalkulasi RSI"},
            "overbought": {"label": "Overbought Level", "min": 60, "max": 85, "step": 1, "help": "RSI di atas ini = overbought, trigger Sell"},
            "oversold": {"label": "Oversold Level", "min": 15, "max": 40, "step": 1, "help": "RSI di bawah ini = oversold, trigger Buy"},
        },
    },
    "MACD": {
        "icon": "\U0001f3af",
        "desc": "Buy saat MACD crossing di atas signal line, Sell saat sebaliknya.",
        "params": {
            "fast": {"label": "Fast EMA", "min": 8, "max": 20, "step": 1, "help": "Periode EMA cepat untuk MACD"},
            "slow": {"label": "Slow EMA", "min": 20, "max": 50, "step": 1, "help": "Periode EMA lambat — harus > fast"},
            "signal": {"label": "Signal Line", "min": 5, "max": 15, "step": 1, "help": "Periode EMA untuk signal line"},
        },
    },
    "Bollinger": {
        "icon": "\U0001f7e2",
        "desc": "Buy saat harga menyentuh lower band, Sell saat upper band.",
        "params": {
            "period": {"label": "Bollinger Period", "min": 10, "max": 30, "step": 1, "help": "Periode lookback SMA & std dev"},
            "std_dev": {"label": "Std Deviation", "min": 1.5, "max": 3.0, "step": 0.1, "help": "Jumlah standar deviasi untuk bands"},
        },
    },
    "Breakout": {
        "icon": "\u26a1",
        "desc": "Buy saat harga break di atas high terbaru, Sell saat break di bawah low.",
        "params": {
            "lookback": {"label": "Lookback Period", "min": 5, "max": 50, "step": 1, "help": "Jumlah candle untuk menentukan range"},
        },
    },
}

STRATEGY_ORDER = ["MA_Crossover", "RSI", "MACD", "Bollinger", "Breakout"]

REGIME_INFO = {
    "trending": {"icon": "\U0001f4c8", "color": "#22c55e"},
    "ranging": {"icon": "\U0001f504", "color": "#f59e0b"},
    "choppy": {"icon": "\U0001f300", "color": "#ef4444"},
}

# ── Render ────────────────────────────────────────────────────


def _render_strategy_card(config, sname: str) -> bool:
    info = STRATEGY_INFO[sname]
    params = config.get("strategies", sname)
    enabled = params.get("enabled", True)
    edited = False

    # ── Card wrapper ──
    with st.container(border=True):
        card_col1, card_col2 = st.columns([0.65, 0.35], vertical_alignment="center")
        with card_col1:
            st.markdown(f"**{info['icon']} {sname.replace('_', ' ')}**")
            st.caption(info['desc'])
        with card_col2:
            en = st.checkbox(f"Enable {sname}", enabled, key=f"strat_{sname}", label_visibility="collapsed")
        if en != enabled:
            config.set("strategies", sname, "enabled", en)
            edited = True
            st.rerun()

        if en:
            # Parameters grid
            param_keys = list(info["params"].keys())
            cols = st.columns(3)
            for i, pk in enumerate(param_keys):
                meta = info["params"][pk]
                v = params.get(pk)
                with cols[i]:
                    if isinstance(v, float):
                        nv = st.number_input(
                            meta["label"],
                            min_value=meta["min"],
                            max_value=meta["max"],
                            value=float(v),
                            step=meta["step"],
                            key=f"{sname}_{pk}",
                            help=meta.get("help"),
                        )
                    else:  # int
                        nv = st.number_input(
                            meta["label"],
                            min_value=meta["min"],
                            max_value=meta["max"],
                            value=int(v),
                            step=int(meta["step"]),
                            key=f"{sname}_{pk}",
                            help=meta.get("help"),
                        )
                    if nv != v:
                        config.set("strategies", sname, pk, nv)
                        edited = True

    return edited


def _render_weights(config) -> bool:
    edited = False
    regimes = ["trending", "ranging", "choppy"]
    strats = ["Breakout", "MA_Crossover", "MACD", "RSI", "Bollinger"]

    st.markdown("---")
    st.subheader("\U0001f3af Strategy Weights (by Regime)")
    st.caption("Adjust how heavily each strategy influences decisions under different market conditions.")

    st.markdown(
        textwrap.dedent(f"""
        <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 0.6rem 1rem; margin-top: 0.25rem;">
            <div style="display: flex; gap: 6px; margin-bottom: 0.5rem; padding-bottom: 0.4rem; border-bottom: 1px solid rgba(255,255,255,0.05);">
                <div style="width: 80px; font-size: 0.6rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.4; align-self: center;">Regime</div>
                {''.join(f'<div style="flex: 1; text-align: center; font-size: 0.7rem; font-weight: 600; opacity: 0.6;">{STRATEGY_INFO.get(s, {}).get("icon", "")} {s.replace("_", " ")}</div>' for s in strats)}
            </div>
        """),
        unsafe_allow_html=True,
    )

    for regime in regimes:
        ri = REGIME_INFO.get(regime, {"icon": "", "color": "#666"})
        cols = st.columns([0.6] + [1] * len(strats))

        with cols[0]:
            st.markdown(
                f"<div style='font-weight: 700; font-size: 0.75rem; color: {ri['color']}; line-height: 2.2;'>{ri['icon']} {regime.upper()}</div>",
                unsafe_allow_html=True,
            )

        for i, s in enumerate(strats):
            v = config.get("strategy_weights", regime, s)
            with cols[i + 1]:
                nv = st.number_input(
                    s,
                    0.0, 2.0, float(v), 0.1,
                    key=f"sw_{regime}_{s}",
                    label_visibility="collapsed",
                    help=f"{regime.title()} weight for {s}",
                )
                if abs(nv - v) > 0.001:
                    config.set("strategy_weights", regime, s, nv)
                    edited = True

    st.markdown("</div>", unsafe_allow_html=True)

    return edited


def render(config) -> bool:
    edited = False

    # Intro banner
    st.markdown(
        textwrap.dedent("""
        <div class="info-banner">
            <div class="title">\U0001f9e0 Konfigurasi Strategi</div>
            <div class="desc">Aktifkan/nonaktifkan strategi dan atur parameter masing-masing. Sesuaikan bobot per regime di bawah untuk mengontrol pengaruh tiap strategi.</div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    # Strategy cards — split into 2 columns (3 left, 2 right)
    col_left, col_right = st.columns(2)
    with col_left:
        for sname in STRATEGY_ORDER[:3]:
            edited |= _render_strategy_card(config, sname)
    with col_right:
        for sname in STRATEGY_ORDER[3:]:
            edited |= _render_strategy_card(config, sname)

    # Weights matrix
    edited |= _render_weights(config)

    return edited
