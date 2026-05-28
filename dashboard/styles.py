"""Dashboard CSS and style constants."""

import streamlit as st

_PREMIUM_CSS = """
<style>
    /* ── Google Font Import ── */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');

    /* ── Global Typography & Layout Reset ── */
    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        color: #e2e8f0;
    }

    /* ── Custom Scrollbar ── */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: rgba(15, 15, 26, 0.5); }
    ::-webkit-scrollbar-thumb { background: rgba(99, 102, 241, 0.15); border-radius: 4px; border: 2px solid #0f0f1a; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(99, 102, 241, 0.3); }

    /* ── Ambient Background Mesh ── */
    .stApp {
        background-color: #080810 !important;
        background-image:
            radial-gradient(at 10% 15%, rgba(99, 102, 241, 0.08) 0px, transparent 45%),
            radial-gradient(at 90% 10%, rgba(139, 92, 246, 0.06) 0px, transparent 40%),
            radial-gradient(at 50% 85%, rgba(236, 72, 153, 0.04) 0px, transparent 50%),
            radial-gradient(at 80% 80%, rgba(34, 197, 94, 0.02) 0px, transparent 40%) !important;
        background-attachment: fixed !important;
    }

    /* ── Typography & Headers ── */
    .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.03em !important;
        color: #ffffff !important;
        margin-top: 0px !important;
    }
    
    h1 {
        font-size: 1.8rem !important;
        background: linear-gradient(135deg, #ffffff 40%, #a5b4fc 90%, #818cf8 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        margin-bottom: 0.8rem !important;
        filter: drop-shadow(0 2px 8px rgba(99, 102, 241, 0.1));
    }
    
    h2 {
        font-size: 1.3rem !important;
        background: linear-gradient(135deg, #ffffff 60%, #c7d2fe 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
        padding-bottom: 0.3rem !important;
        margin-top: 1.2rem !important;
        margin-bottom: 0.8rem !important;
    }
    
    h3 {
        font-size: 1.0rem !important;
        font-weight: 650 !important;
        color: #e0e7ff !important;
        margin-bottom: 0.4rem !important;
    }

    /* ── Premium Glassmorphic Cards (st.container(border=True)) ── */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(18, 18, 32, 0.35) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 16px !important;
        padding: 1.4rem !important;
        backdrop-filter: blur(20px) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        margin-bottom: 1.2rem !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(99, 102, 241, 0.25) !important;
        box-shadow: 
            0 12px 40px 0 rgba(0, 0, 0, 0.4),
            0 0 25px 0 rgba(99, 102, 241, 0.08) !important;
        transform: translateY(-1px);
    }

    /* ── Metric Cards ── */
    div[data-testid="metric-container"] {
        background: rgba(26, 26, 46, 0.4) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 12px !important;
        padding: 0.8rem 1.1rem !important;
        backdrop-filter: blur(12px) !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative;
        overflow: hidden;
    }
    div[data-testid="metric-container"]::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 3px;
        height: 100%;
        background: linear-gradient(180deg, #6366f1, #a855f7);
        opacity: 0.7;
    }
    div[data-testid="metric-container"]:hover {
        border-color: rgba(99, 102, 241, 0.3) !important;
        background: rgba(30, 30, 54, 0.55) !important;
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.12) !important;
        transform: translateY(-2px);
    }
    div[data-testid="metric-container"] label {
        font-size: 0.65rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        color: rgba(255, 255, 255, 0.45) !important;
    }
    div[data-testid="metric-container"] div[data-testid="metric-value"] {
        font-weight: 800 !important;
        font-size: 1.25rem !important;
        color: #ffffff !important;
        letter-spacing: -0.02em !important;
        margin-top: 0.15rem !important;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricDelta"] {
        font-weight: 600 !important;
        font-size: 0.8rem !important;
    }

    /* ── Interactive Tabs (st.tabs) ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px !important;
        background-color: rgba(10, 10, 18, 0.45) !important;
        padding: 5px !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        padding: 0.5rem 1.1rem !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        color: rgba(255, 255, 255, 0.5) !important;
        background-color: transparent !important;
        border: none !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #ffffff !important;
        background-color: rgba(255, 255, 255, 0.03) !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        color: #ffffff !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.25) !important;
    }
    .stTabs [data-baseweb="tab-highlight-id"] {
        background-color: transparent !important;
    }

    /* ── Buttons (st.button) ── */
    div.stButton > button {
        width: 100% !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        padding: 0.55rem 1.2rem !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        background: rgba(255, 255, 255, 0.02) !important;
        color: rgba(255, 255, 255, 0.85) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        border-color: rgba(99, 102, 241, 0.4) !important;
        background: rgba(99, 102, 241, 0.08) !important;
        color: #ffffff !important;
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.12) !important;
    }
    div.stButton > button:active {
        transform: translateY(0px) !important;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.25) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.35) !important;
        transform: translateY(-2px) !important;
    }

    /* ── Form Inputs & Widgets ── */
    div[data-testid="stTextInput"] input, 
    div[data-testid="stNumberInput"] input,
    div[data-baseweb="select"] {
        background-color: rgba(10, 10, 18, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
        color: #ffffff !important;
        padding: 0.4rem 0.8rem !important;
        transition: all 0.25s ease !important;
    }
    div[data-testid="stTextInput"] input:focus, 
    div[data-testid="stNumberInput"] input:focus,
    div[data-baseweb="select"]:focus-within {
        border-color: rgba(99, 102, 241, 0.6) !important;
        box-shadow: 0 0 10px rgba(99, 102, 241, 0.15) !important;
        background-color: rgba(15, 15, 26, 0.8) !important;
    }
    
    /* Toggle & Checkbox styling */
    div[data-testid="stCheckbox"] label, 
    div[data-testid="stCheckbox"] span {
        font-weight: 550 !important;
        font-size: 0.85rem !important;
        color: rgba(255, 255, 255, 0.8) !important;
    }
    
    /* Slider styling */
    div[data-testid="stSlider"] {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }

    /* ── DataFrames & Tables ── */
    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 14px !important;
        background: rgba(10, 10, 18, 0.3) !important;
        padding: 6px !important;
        overflow: hidden !important;
        box-shadow: inset 0 0 12px rgba(0, 0, 0, 0.2) !important;
    }
    div[data-testid="stDataFrame"] table { font-size: 0.75rem; }

    /* ── Dividers ── */
    hr { border-color: rgba(255, 255, 255, 0.05) !important; margin: 1.4rem 0 !important; }

    /* ── Premium Sidebar ── */
    .stSidebar {
        background: rgba(8, 8, 14, 0.96) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(20px) !important;
    }
    .stSidebar .stRadio label {
        font-weight: 600 !important;
        font-size: 0.86rem !important;
        padding: 0.5rem 0.8rem !important;
        border-radius: 10px !important;
        transition: all 0.2s ease !important;
        color: rgba(255, 255, 255, 0.7) !important;
        border: 1px solid transparent !important;
        margin-bottom: 5px !important;
    }
    .stSidebar .stRadio label:hover {
        background: rgba(255, 255, 255, 0.03) !important;
        color: #ffffff !important;
    }
    .stSidebar .stRadio div[data-testid="stMarkdownContainer"] {
        font-size: 0.86rem;
    }
    .stSidebar .stRadio div[role="radiogroup"] {
        padding-top: 0.5rem;
    }

    /* ── Info / Warning / Error Alert Boxes ── */
    .stAlert {
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15) !important;
        background-color: rgba(18, 18, 32, 0.6) !important;
    }
    div[data-testid="stInfoBox"] {
        background: rgba(99, 102, 241, 0.05) !important;
        border-color: rgba(99, 102, 241, 0.15) !important;
        color: #c7d2fe !important;
    }
    div[data-testid="stWarningBox"] {
        background: rgba(245, 158, 11, 0.05) !important;
        border-color: rgba(245, 158, 11, 0.15) !important;
        color: #fde68a !important;
    }
    div[data-testid="stSuccessBox"] {
        background: rgba(16, 185, 129, 0.05) !important;
        border-color: rgba(16, 185, 129, 0.15) !important;
        color: #a7f3d0 !important;
    }

    /* ── Expanders ── */
    .streamlit-expanderHeader {
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        border-radius: 10px !important;
        background-color: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        transition: all 0.2s ease !important;
        color: #e2e8f0 !important;
    }
    .streamlit-expanderHeader:hover {
        background-color: rgba(255, 255, 255, 0.04) !important;
        border-color: rgba(99, 102, 241, 0.2) !important;
    }
    .streamlit-expanderContent {
        background-color: rgba(10, 10, 18, 0.2) !important;
        border-radius: 0 0 10px 10px !important;
        border-left: 1px solid rgba(255, 255, 255, 0.04) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.04) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.04) !important;
    }

    /* ── Custom Cards / Classes ── */
    .premium-metric {
        background: linear-gradient(135deg, rgba(26, 26, 46, 0.8), rgba(15, 15, 26, 0.85)) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        border-radius: 16px !important;
        padding: 1.1rem !important;
        backdrop-filter: blur(16px) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative;
        overflow: hidden;
    }
    .premium-metric::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
    }
    .premium-metric:hover {
        transform: translateY(-3px) !important;
        border-color: rgba(99, 102, 241, 0.4) !important;
        box-shadow: 0 12px 40px rgba(99, 102, 241, 0.16) !important;
    }
    .premium-metric .label {
        font-size: 0.62rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        color: rgba(255, 255, 255, 0.45) !important;
        font-weight: 700 !important;
        margin-bottom: 0.3rem !important;
    }
    .premium-metric .value {
        font-size: 1.35rem !important;
        font-weight: 800 !important;
        color: #ffffff !important;
        letter-spacing: -0.03em !important;
        background: linear-gradient(135deg, #ffffff 60%, rgba(255,255,255,0.75));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .glass-card {
        background: rgba(20, 20, 35, 0.3) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 16px !important;
        padding: 1.3rem !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25) !important;
        transition: all 0.3s ease !important;
    }
    .glass-card:hover {
        border-color: rgba(99, 102, 241, 0.25) !important;
        box-shadow: 0 15px 45px rgba(0,0,0,0.35) !important;
    }

    /* Live pulse dot */
    .live-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        animation: pulse-dot 1.8s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    .live-dot.red { background: #ef4444; box-shadow: 0 0 10px rgba(239, 68, 68, 0.6); }
    .live-dot.green { background: #10b981; box-shadow: 0 0 10px rgba(16, 185, 129, 0.6); }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.3; transform: scale(0.8); }
    }

    /* Info banner */
    .info-banner {
        background: linear-gradient(135deg, rgba(99,102,241,0.06), rgba(139,92,246,0.02));
        border: 1px solid rgba(99,102,241,0.12);
        border-radius: 12px;
        padding: 0.9rem 1.2rem;
        margin-bottom: 1.2rem;
    }
    .info-banner .title {
        font-size: 0.85rem;
        font-weight: 700;
        color: #a5b4fc;
        letter-spacing: -0.01em;
    }
    .info-banner .desc {
        font-size: 0.72rem;
        opacity: 0.55;
        margin-top: 3px;
    }

    .preview-card {
        background: rgba(255,255,255,0.01);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 0.8rem;
        margin-bottom: 0.6rem;
        transition: all 0.25s ease;
    }
    .preview-card:hover {
        border-color: rgba(99, 102, 241, 0.2);
        background: rgba(255,255,255,0.03);
    }

    @media (max-width: 768px) {
        .premium-metric .value { font-size: 1.3rem; }
        h1 { font-size: 1.8rem !important; }
    }
</style>
"""


def inject_css():
    """Inject premium CSS into the Streamlit app."""
    st.markdown(_PREMIUM_CSS, unsafe_allow_html=True)
