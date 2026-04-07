@echo off
REM ═══════════════════════════════════════════════════════════════
REM AI Team System — One-Click Installer (Windows)
REM Версия: 2.0
REM ═══════════════════════════════════════════════════════════════

setlocal enabledelayedexpansion

set "INSTALL_DIR=%~dp0.."
set "LOG_FILE=%INSTALL_DIR%\scripts\install.log"
set "CACHE_FILE=%INSTALL_DIR%\.hardware_cache"

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║        AI Team System — Installer v2.0 (Windows)        ║
echo ║        Мультиагентная система разработки ПО             ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

call :log "[INFO] Лог: %LOG_FILE%"

cd /d "%INSTALL_DIR%"

REM Проверка Python
set "PYTHON_CMD="
for %%v in (3.12 3.11 3.10) do (
    for /f "tokens=*" %%p in ('where python%%v 2^>nul') do (
        set "PYTHON_CMD=%%p"
        goto :python_found
    )
)
where python3 >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_CMD=python3"
    goto :python_found
)
where python >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_CMD=python"
    goto :python_found
)

call :warn "Python 3.10+ не найден."
call :warn "Скачай с https://www.python.org/downloads/"
call :warn "Убедись что галочка 'Add to PATH' установлена."
pause
exit /b 1

:python_found
if "!PYTHON_CMD!"=="python" (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PY_VERSION=%%v"
) else (
    for /f "tokens=2" %%v in ('"!PYTHON_CMD!" --version 2^>^&1') do set "PY_VERSION=%%v"
)
call :ok "Python найден: !PY_VERSION!"

REM Проверка Git
where git >nul 2>&1
if !errorlevel! neq 0 (
    call :warn "Git не найден. Скачай с https://git-scm.com/download/win"
    pause
    exit /b 1
)
call :ok "Git найден"

REM Виртуальное окружение
call :log "Создаю виртуальное окружение..."
"!PYTHON_CMD!" -m venv venv
call venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
call :ok "Виртуальное окружение создано"

REM Зависимости
call :log "Устанавливаю зависимости..."
pip install -r requirements.txt -q 2>> "%LOG_FILE%"
call :ok "Зависимости установлены"

REM Детект железа
call :log "Сканирую железо..."
set "VRAM_GB=0"
set "RAM_GB=0"

REM RAM через wmic
for /f "tokens=2 delims==" %%a in ('wmic ComputerSystem get TotalPhysicalMemory /value 2^>nul') do (
    set /a "RAM_GB=%%a / 1073741824"
)
if "!RAM_GB!"=="" set "RAM_GB=8"

REM VRAM через wmic
for /f "tokens=2 delims==" %%a in ('wmic path Win32_VideoController get AdapterRAM /value 2^>nul ^| findstr "^[0-9]"') do (
    set /a "VRAM_GB=%%a / 1073741824"
)
if "!VRAM_GB!"=="" set "VRAM_GB=0"

REM Выбор модели
if !VRAM_GB! gtr 12 (
    set "PROFILE=heavy"
    set "MODEL=qwen3:14b"
) else if !VRAM_GB! geq 6 (
    set "PROFILE=medium"
    set "MODEL=qwen3:8b"
) else (
    set "PROFILE=light"
    set "MODEL=qwen3:4b"
)

echo profile=!PROFILE!> "%CACHE_FILE%"
echo model=!MODEL!>> "%CACHE_FILE%"
echo vram=!VRAM_GB!>> "%CACHE_FILE%"
echo ram=!RAM_GB!>> "%CACHE_FILE%"
echo os=Windows>> "%CACHE_FILE%"

call :log "Железо: !VRAM_GB!ГБ VRAM, !RAM_GB!ГБ RAM → профиль '!PROFILE!', модель '!MODEL!'"
call :ok "Кэш сохранён в .hardware_cache"

REM Ollama
where ollama >nul 2>&1
if !errorlevel! neq 0 (
    call :warn "Ollama не найдена."
    call :warn "Скачай с https://ollama.ai/download/windows"
    call :warn "После установки запусти ollama pull !MODEL!"
) else (
    call :ok "Ollama найдена"
    ollama list 2>nul | findstr "!MODEL!" >nul
    if !errorlevel! neq 0 (
        call :log "Загружаю модель !MODEL!..."
        ollama pull !MODEL!
        call :ok "Модель !MODEL! загружена"
    ) else (
        call :ok "Модель !MODEL! уже загружена"
    )
)

REM .env
if not exist "%INSTALL_DIR%\.env" (
    copy "%INSTALL_DIR%\.env.example" "%INSTALL_DIR%\.env" >nul
    call :log ".env создан"
)

REM Папки
mkdir "%USERPROFILE%\.logs\ai_team" 2>nul
mkdir "%USERPROFILE%\ai-team-lessons" 2>nul
mkdir "%USERPROFILE%\projects" 2>nul
call :ok "Рабочие папки созданы"

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║                    ГОТОВО!                              ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
call :log "Запускаю веб-интерфейс..."

cd /d "%INSTALL_DIR%"
call venv\Scripts\activate.bat
start /b python -m uvicorn web_ui.app:app --host 0.0.0.0 --port 8000

timeout /t 3 /nobreak >nul
start http://localhost:8000

echo.
echo Веб-интерфейс: http://localhost:8000
echo Лог: %LOG_FILE%
echo.
pause
exit /b 0

:log
echo [INFO] %~1
echo [INFO] %~1 >> "%LOG_FILE%"
exit /b 0

:ok
echo [OK] %~1
echo [OK] %~1 >> "%LOG_FILE%"
exit /b 0

:warn
echo [WARN] %~1
echo [WARN] %~1 >> "%LOG_FILE%"
exit /b 0
