@echo off
title Bayanullisan Bot 24/7 Restart Script

:loop
echo Bot ishga tushirilmoqda...
python main.py

echo Bot to'xtab qoldi. Yoki xato yuz berdi.
echo 5 soniyadan keyin qayta ishga tushiriladi...
timeout /t 5 /nobreak >nul
goto loop
