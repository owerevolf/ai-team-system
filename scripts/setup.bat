@echo off
REM ═══════════════════════════════════════════════════════════════
REM AI Team System — One-Click Installer
REM Windows
REM ═══════════════════════════════════════════════════════════════

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║        AI Team System - Installer                       ║
echo ║        Мультиагентная система разработки ПО             ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM ─── 1. Проверка Python ───
echo [INFO] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [WARN] Python не найден!
    echo.
    echo Скачайте Python с https://www.python.org/downloads/
    echo При установке отметьте "Add Python to PATH"
    echo.
    echo Открываю страницу загрузки...
    start https://www.python.org/downloads/
    echo.
    echo После установки Python запустите этот скрипт снова.
    pause
    exit /b 1
)
echo [OK] Python найден

REM ─── 2. Создание директории ───
set INSTALL_DIR=%USERPROFILE%\ai-team-system
if exist "%INSTALL_DIR%" (
    echo [WARN] Папка уже существует: %INSTALL_DIR%
    echo.
    set /p USE_EXIST="Использовать существующую? (y/n): "
    if /i "%USE_EXIST%"=="y" (
        cd /d "%INSTALL_DIR%"
        call venv\Scripts\activate.bat 2>nul
        echo.
        echo Запуск Web UI...
        python web_ui\app.py
        exit /b 0
    ) else (
        echo [INFO] Удаляю старую установку...
        rmdir /s /q "%INSTALL_DIR%"
    )
)

echo [INFO] Создаю папку: %INSTALL_DIR%
mkdir "%INSTALL_DIR%"
cd /d "%INSTALL_DIR%"

REM ─── 3. Клонирование репозитория ───
echo [INFO] Скачиваю проект...
where git >nul 2>&1
if errorlevel 1 (
    echo [WARN] Git не найден!
    echo.
    echo Скачайте Git с https://git-scm.com/download/win
    start https://git-scm.com/download/win
    echo.
    echo После установки Git запустите этот скрипт снова.
    pause
    exit /b 1
)

git clone https://github.com/owerevolf/ai-team-system.git .
echo [OK] Проект скачан

REM ─── 4. Виртуальное окружение ───
echo [INFO] Создаю виртуальное окружение...
python -m venv venv
call venv\Scripts\activate.bat
echo [OK] Виртуальное окружение создано

REM ─── 5. Установка зависимостей ───
echo [INFO] Устанавливаю зависимости...
pip install -r requirements.txt -q
echo [OK] Зависимости установлены

REM ─── 6. Проверка Ollama ───
where ollama >nul 2>&1
if errorlevel 1 (
    echo.
    echo ╔══════════════════════════════════════════════════════════╗
    echo ║  Ollama - локальный сервер для AI моделей               ║
    echo ║  Без неё система не сможет работать офлайн              ║
    echo ╚══════════════════════════════════════════════════════════╝
    echo.
    set /p INSTALL_OLLAMA="Установить Ollama? (y/n): "
    if /i "%INSTALL_OLLAMA%"=="y" (
        echo [INFO] Открываю страницу загрузки Ollama...
        start https://ollama.ai/download
        echo.
        echo После установки Ollama откройте командную строку и выполните:
        echo   ollama pull qwen2.5-coder:7b
        echo.
    ) else (
        echo [WARN] Ollama не установлена. Можно использовать облачные API.
    )
) else (
    echo [OK] Ollama найдена
    ollama list | findstr "qwen2.5-coder" >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Модель qwen2.5-coder не найдена
        echo.
        set /p PULL_MODEL="Скачать модель qwen2.5-coder:7b? (y/n): "
        if /i "%PULL_MODEL%"=="y" (
            echo [INFO] Скачиваю модель...
            ollama pull qwen2.5-coder:7b
            echo [OK] Модель скачана
        )
    ) else (
        echo [OK] Модель qwen2.5-coder найдена
    )
)

REM ─── 7. Конфигурация ───
if not exist ".env" (
    copy .env.example .env >nul
    echo [OK] Конфиг .env создан
)

REM ─── 8. Создание папок ───
if not exist "%USERPROFILE%\.logs\ai_team" mkdir "%USERPROFILE%\.logs\ai_team"
if not exist "%USERPROFILE%\projects" mkdir "%USERPROFILE%\projects"
echo [OK] Папки созданы

REM ─── 9. Финал ───
echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║                    ГОТОВО!                               ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo Запуск:
echo.
echo   cd %INSTALL_DIR%
echo   venv\Scripts\activate
echo.
echo   REM Web UI (рекомендуется):
echo   python web_ui\app.py
echo.
echo   REM CLI:
echo   python -m core.main --project-name myapp --requirements "описание"
echo.
echo Открой в браузере: http://localhost:5000
echo.
echo Документация: https://github.com/owerevolf/ai-team-system
echo.
set /p LAUNCH="Запустить Web UI сейчас? (y/n): "
if /i "%LAUNCH%"=="y" (
    echo Запуск...
    python web_ui\app.py
)

pause
