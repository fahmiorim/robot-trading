@echo off
title AI Trading Robot Dashboard
color 0A
echo ========================================
echo    AI TRADING ROBOT - Dashboard
echo ========================================
echo.
echo Memulai Streamlit dashboard...
echo.
cd /d "D:\laragon\www\robot-trading"

rem Jalankan Streamlit langsung — lebih stabil dari python -m dashboard
python -m streamlit run dashboard.py --server.port=8501

pause
