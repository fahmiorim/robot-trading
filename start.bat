@echo off
title AI Trading Robot Dashboard
color 0A
echo ========================================
echo    AI TRADING ROBOT - Dashboard
echo ========================================
echo.
echo Memulai Streamlit dashboard...
echo.
cd /d "D:\laragon\www\robot"

rem Streamlit akan otomatis buka browser
python -m streamlit run dashboard.py

pause
