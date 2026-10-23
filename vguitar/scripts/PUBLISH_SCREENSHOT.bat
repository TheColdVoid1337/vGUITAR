@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0publish_screenshot.ps1" %*
exit /b %ERRORLEVEL%
