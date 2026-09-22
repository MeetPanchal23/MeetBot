@echo off
title MeetBot Status
echo Checking MeetBot background status...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*main.py*' }; if ($procs) { Write-Host '>>> MeetBot is RUNNING in the background (PID: ' ($procs.ProcessId -join ', ') ')' -ForegroundColor Green } else { Write-Host '>>> MeetBot is NOT running.' -ForegroundColor Red }"
echo.
pause
