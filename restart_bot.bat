@echo off
title Restarting Phone Monitor Bot
echo Stopping bot...
taskkill /f /im python.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo Starting bot...
cd /d "%~dp0"
start "Phone Monitor Bot" cmd /k "python -m bot.main"
echo Bot restarted successfully
timeout /t 3
