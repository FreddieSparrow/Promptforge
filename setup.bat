@echo off
setlocal
title PromptForge Setup

echo.
echo   PROMPTFORGE - Setup
echo   ==================
echo.

set "SCRIPT_DIR=%~dp0"

:: Python check
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [INFO] %%v

:: Ollama check
where ollama >nul 2>&1
if errorlevel 1 (
    echo [INFO] Ollama not found - installing via winget...
    winget install Ollama.Ollama --silent
    if errorlevel 1 (
        echo [WARN] winget install failed. Download manually: https://ollama.com/download/windows
    )
    echo [INFO] After install completes, close and re-run this script.
    pause
)

:: Pull default starter model
where ollama >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Pulling gemma3:4b as the default starter model (may take several minutes)...
    echo [INFO] You can install any other Ollama model from Settings inside the app.
    start /min "" ollama serve
    timeout /t 3 /nobreak >nul
    ollama pull gemma3:4b
    if errorlevel 1 echo [WARN] Could not pull model. Open the app, go to Settings, and install a model from there.
)

:: Python deps
echo [INFO] Installing Python dependencies...
cd /d "%SCRIPT_DIR%"
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed
    pause & exit /b 1
)

:: Launch
echo.
echo [INFO] Starting PromptForge at http://localhost:7474
start "" "http://localhost:7474"
python main.py

pause
