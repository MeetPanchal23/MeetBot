@echo off
title Install MeetBot Auto-Start
echo Setting up MeetBot to run automatically on Windows startup...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$startup = [System.Environment]::GetFolderPath('Startup'); $scriptDir = (Get-Item '%~dp0').FullName.TrimEnd('\'); $vbsPath = Join-Path $scriptDir 'start_bot_background.vbs'; $shortcutPath = Join-Path $startup 'MeetBot.lnk'; $wsh = New-Object -ComObject WScript.Shell; $sc = $wsh.CreateShortcut($shortcutPath); $sc.TargetPath = 'wscript.exe'; $sc.Arguments = '\"' + $vbsPath + '\"'; $sc.WorkingDirectory = $scriptDir; $sc.Description = 'MeetBot IPO Agent Auto-Start'; $sc.Save(); Write-Host 'SUCCESS: Shortcut created in Windows Startup folder!' -ForegroundColor Green; Write-Host 'Location: ' $shortcutPath"
echo.
echo MeetBot will now automatically start in the background whenever you log into Windows!
echo You will never have to type "python main.py" again.
echo.
pause
