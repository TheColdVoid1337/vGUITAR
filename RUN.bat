@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0vguitar_notes.py"
) else (
    python "%~dp0vguitar_notes.py"
)
if errorlevel 1 (
    echo.
    echo Could not start vGUITAR. Check Python and Tkinter installation.
    pause
)
