"""
Health & Notifications — semua setting sudah dipindahkan ke tab 🌍 Universal.
Tab ini dipertahankan sebagai placeholder kosong.
"""
import streamlit as st


def render(config) -> bool:
    st.info(
        "🏥 **Health Check, Notifikasi & Telegram** sudah dipindahkan ke tab **🌍 Universal** — "
        "berlaku untuk semua simbol dan timeframe.",
        icon="🌍",
    )
    return False
