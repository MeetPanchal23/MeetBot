@echo off
title Remove MeetBot Auto-Start
echo Removing MeetBot from Windows startup...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$startup = [System.Environment]::GetFolderPath('Startup'); $shortcutPath = Join-Path $startup 'MeetBot.lnk'; if (Test-Path $shortcutPath) { Remove-Item $shortcutPath -Force; Write-Host 'SUCCESS: Auto-start shortcut removed.' -ForegroundColor Yellow } else { Write-Host 'Auto-start shortcut was not found.' }"
echo.
pause
