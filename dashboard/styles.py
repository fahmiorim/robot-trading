"""Dashboard CSS and style constants."""

import streamlit as st

_PREMIUM_CSS = """
<style>
    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.15); }

    /* ── Global ── */
    html { scroll-behavior: smooth; }
    .stApp {
        background: #0f0f1a;
        background-image:
            radial-gradient(ellipse at 20% 50%, rgba(88, 80, 236, 0.04) 0%, transparent 70%),
            radial-gradient(ellipse at 80% 20%, rgba(168, 85, 247, 0.03) 0%, transparent 60%),
            radial-gradient(ellipse at 50% 80%, rgba(236, 72, 153, 0.02) 0%, transparent 60%);
    }

    /* ── Typography ── */
    h1, h2, h3, h4, h5, h6 { font-weight: 700 !important; letter-spacing: -0.02em; }
    .block-container { padding-top: 3rem !important; }
    h1 { font-size: 2.2rem !important; background: linear-gradient(135deg, #fff 40%, rgba(255,255,255,0.6)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.75rem !important; }
    h2 { font-size: 1.5rem !important; margin-top: 1.5rem !important; }
    h3 { font-size: 1.15rem !important; }

    /* ── Metrics ── */
    div[data-testid="metric-container"] {
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 0.6rem 0.8rem;
        backdrop-filter: blur(8px);
        transition: all 0.2s ease;
    }
    div[data-testid="metric-container"]:hover { border-color: rgba(255,255,255,0.12); background: rgba(255,255,255,0.04); }
    div[data-testid="metric-container"] label {
        font-size: 0.7rem !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        opacity: 0.5;
    }
    div[data-testid="metric-container"] div[data-testid="metric-value"] {
        font-weight: 700;
        font-size: 1.5rem !important;
    }

    /* ── Cards / Containers ── */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.4rem 1rem;
        font-size: 0.8rem;
        font-weight: 600;
        transition: all 0.15s ease;
    }
    .stTabs [aria-selected="true"] { background: rgba(255,255,255,0.06) !important; }

    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.8rem;
        transition: all 0.2s ease;
        border: 1px solid rgba(255,255,255,0.06);
        background: rgba(255,255,255,0.03);
    }
    div.stButton > button:hover {
        transform: translateY(-1px);
        border-color: rgba(255,255,255,0.15);
        background: rgba(255,255,255,0.06);
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        color: white;
    }
    div.stButton > button[kind="primary"]:hover {
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);
        transform: translateY(-1px);
    }

    /* ── DataFrames ── */
    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 10px;
        overflow: hidden;
    }
    div[data-testid="stDataFrame"] table { font-size: 0.75rem; }

    /* ── Dividers ── */
    hr { border-color: rgba(255,255,255,0.04) !important; margin: 1.2rem 0 !important; }

    /* ── Sidebar ── */
    .stSidebar {
        background: rgba(15, 15, 30, 0.95) !important;
        border-right: 1px solid rgba(255,255,255,0.04);
    }
    .stSidebar .stRadio label {
        font-weight: 500;
        font-size: 0.85rem;
        padding: 0.35rem 0.5rem;
        border-radius: 6px;
        transition: all 0.15s ease;
    }
    .stSidebar .stRadio label:hover { background: rgba(255,255,255,0.04); }
    .stSidebar .stRadio div[data-testid="stMarkdownContainer"] {
        font-size: 0.85rem;
    }

    /* ── Info / Warning / Error boxes ── */
    .stAlert { border-radius: 10px; border: 1px solid rgba(255,255,255,0.06); }
    div[data-testid="stInfoBox"] { background: rgba(96,165,250,0.06); border-color: rgba(96,165,250,0.15); }
    div[data-testid="stWarningBox"] { background: rgba(251,191,36,0.06); border-color: rgba(251,191,36,0.15); }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        font-weight: 600;
        font-size: 0.85rem;
        border-radius: 8px;
        transition: all 0.15s ease;
    }
    .streamlit-expanderHeader:hover { background: rgba(255,255,255,0.03); }

    /* ── Premium Metric Cards (custom) ── */
    .premium-metric {
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 0.8rem;
        backdrop-filter: blur(8px);
        transition: all 0.25s ease;
    }
    .premium-metric:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
        border-color: rgba(255,255,255,0.12);
    }
    .premium-metric .label {
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 600;
        margin-bottom: 0.2rem;
    }
    .premium-metric .value {
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }

    /* ── Glass card ── */
    .glass-card {
        background: rgba(255,255,255,0.02);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 14px;
        padding: 1rem;
        transition: all 0.2s ease;
    }
    .glass-card:hover {
        border-color: rgba(255,255,255,0.1);
        box-shadow: 0 8px 32px rgba(0,0,0,0.12);
    }

    /* ── Live dot ── */
    .live-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        animation: pulse-dot 1.5s ease-in-out infinite;
        box-shadow: 0 0 8px rgba(239,68,68,0.5);
    }
    .live-dot.red { background: #ef4444; }
    .live-dot.green { background: #22c55e; }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.85); }
    }

    /* ── Info banner ── */
    .info-banner {
        background: linear-gradient(135deg, rgba(139,92,246,0.06), rgba(139,92,246,0.02));
        border: 1px solid rgba(139,92,246,0.1);
        border-radius: 12px;
        padding: 0.8rem 1rem;
        margin-bottom: 1rem;
    }
    .info-banner .title {
        font-size: 0.8rem;
        font-weight: 600;
        color: #a78bfa;
    }
    .info-banner .desc {
        font-size: 0.7rem;
        opacity: 0.45;
        margin-top: 2px;
    }

    @media (max-width: 768px) {
        .premium-metric .value { font-size: 1.1rem; }
        h1 { font-size: 1.6rem !important; }
    }

    /* Preview card */
    .preview-card {
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 0.8rem;
        margin-bottom: 0.5rem;
        transition: all 0.2s ease;
    }
    .preview-card:hover {
        border-color: rgba(255,255,255,0.15);
        background: rgba(255,255,255,0.04);
    }

    /* Toggle switch for settings */
    div[data-testid="stCheckbox"] label {
        font-weight: 500;
        font-size: 0.85rem;
    }
</style>
"""


def inject_css():
    """Inject premium CSS into the Streamlit app."""
    st.markdown(_PREMIUM_CSS, unsafe_allow_html=True)
