@echo off
title MeetBot - IPO Intelligence Agent
cd /d "%~dp0"
echo ========================================================
echo   Starting MeetBot (Godfather IPO Intelligence Agent)
echo ========================================================
echo.
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bot stopped with an error code %ERRORLEVEL%.
    pause
)
