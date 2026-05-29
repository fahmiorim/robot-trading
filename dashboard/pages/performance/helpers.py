"""Shared helper functions for Performance Analytics tabs."""
import streamlit as st

def _clean_html(html: str) -> str:
    """Remove leading/trailing whitespace from each line of HTML to prevent markdown parsing issues."""
    return "\n".join(line.strip() for line in html.splitlines())

def _glass_card(content: str, style: str = ""):
    return f'<div class="glass-card" style="{style}">{content}</div>'

def _info_banner(title: str, desc: str):
    st.markdown(
        f'<div class="info-banner">'
        f'<div class="title">{title}</div>'
        f'<div class="desc">{desc}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def _metrics_bar(*items):
    """Render compact metrics row from (label, value, color) tuples."""
    sep = '<div style="width:1px; height:22px; background:rgba(255,255,255,0.08);">'
    cells = ""
    for idx, (lbl, val, col) in enumerate(items):
        if idx > 0:
            cells += sep
        cells += (
            f'<div style="flex:1; text-align:center;">'
            f'<div style="font-size:0.62rem; opacity:0.5; font-weight:700; text-transform:uppercase; '
            f'letter-spacing:0.05em; margin-bottom:2px;">{lbl}</div>'
            f'<div style="font-size:0.9rem; font-weight:800; color:{col};">{val}</div>'
            f'</div>'
        )
    st.markdown(
        _glass_card(
            f'<div style="display:flex; align-items:center;">{cells}</div>',
            'padding: 0.6rem 1rem;',
        ),
        unsafe_allow_html=True,
    )
