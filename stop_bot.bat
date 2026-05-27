@echo off
title Stopping Phone Monitor Bot
echo Stopping Phone Monitor Bot...
taskkill /f /im python.exe
echo Bot stopped successfully
timeout /t 3
