@echo off
title Feedback360 Launcher - FRI-142
cd /d "%~dp0"

echo ============================================================
echo    Feedback360Degree  -  360 Core Values Assessment System
echo    Group FRI-142
echo ============================================================
echo.

REM --- 1. Find Python (prefer the "py" launcher, fall back to "python") ---
set "PYTHON="
where py >nul 2>nul && set "PYTHON=py"
if not defined PYTHON (
    where python >nul 2>nul && set "PYTHON=python"
)
if not defined PYTHON (
    echo [ERROR] Python was not found on this computer.
    echo.
    echo Install Python 3 from:  https://www.python.org/downloads/
    echo During setup, TICK the box "Add python.exe to PATH".
    echo Then run this file again.
    echo.
    pause
    exit /b 1
)
echo Using Python: %PYTHON%
echo.

REM --- 2. Install required packages only if they are missing ---
%PYTHON% -c "import flask, reportlab" >nul 2>nul
if errorlevel 1 (
    echo Installing required packages ^(first run only, please wait^)...
    %PYTHON% -m pip install -r requirements.txt --quiet --disable-pip-version-check
    if errorlevel 1 (
        echo.
        echo [ERROR] Could not install packages. Check your internet connection
        echo and try running this file again.
        echo.
        pause
        exit /b 1
    )
) else (
    echo Required packages already installed.
)
echo.

REM --- 3. Build the database the first time only (keeps your data afterwards) ---
if not exist "feedback360.db" (
    echo Setting up the database for the first time...
    %PYTHON% database.py
    echo.
)

REM --- 4. Start the server in its own window, then open the browser ---
echo Starting the server...
start "Feedback360 Server" %PYTHON% app.py

echo Waiting a few seconds for the server to be ready...
ping -n 5 127.0.0.1 >nul
start "" http://127.0.0.1:5000

echo.
echo ============================================================
echo    The app is now running at:   http://127.0.0.1:5000
echo.
echo    A window titled "Feedback360 Server" just opened.
echo    KEEP THAT WINDOW OPEN while you present.
echo    To STOP the server, close that window.
echo.
echo    You can close THIS window now.
echo ============================================================
echo.
pause