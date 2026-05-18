@echo off
setlocal
title PromptForge Setup

echo.
echo   PROMPTFORGE - Setup
echo   ==================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause & exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [INFO] %%v

if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause & exit /b 1
    )
)

call .venv\Scripts\activate
python -m pip install --upgrade pip --quiet

where ollama >nul 2>&1
if errorlevel 1 (
    echo [WARN] Ollama not found.
    echo [INFO] Install from: https://ollama.com/download/windows
)

where ollama >nul 2>&1
if not errorlevel 1 (
    start /min "" ollama serve
    timeout /t 3 /nobreak >nul

    ollama list | findstr /i "gemma3" >nul
    if errorlevel 1 (
        echo [INFO] Pulling gemma3:4b as the default starter model...
        ollama pull gemma3:4b
        if errorlevel 1 echo [WARN] Could not pull model. You can install one later in Settings.
    )
)

echo [INFO] Installing Python dependencies into .venv...
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed
    pause & exit /b 1
)

echo.
echo [INFO] Starting PromptForge at http://localhost:7474
start "" "http://localhost:7474"
python main.py

pause
