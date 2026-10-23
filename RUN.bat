@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creating vGUITAR virtual environment...
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 -m venv ".venv"
  ) else (
    python -m venv ".venv"
  )
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -c "import sounddevice" >nul 2>&1
if errorlevel 1 (
  echo Installing WASAPI audio dependency...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" "vguitar\vguitar_notes.py"
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo vGUITAR could not start. Check Python, Tkinter and internet access for first install.
pause
exit /b 1
