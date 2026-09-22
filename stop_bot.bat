@echo off
title Stop MeetBot
echo Stopping MeetBot background processes...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host 'Stopped process' $_.ProcessId }"
echo.
echo MeetBot has been stopped.
timeout /t 3
