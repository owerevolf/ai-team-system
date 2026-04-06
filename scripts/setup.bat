@echo off
REM Setup для Windows

echo 🚀 Установка AI Team System

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден. Установите Python 3.10+
    pause
    exit /b 1
)

REM Создание виртуального окружения
if not exist "venv" (
    echo 📦 Создание виртуального окружения...
    python -m venv venv
    call venv\Scripts\activate.bat
)

REM Установка зависимостей
echo 📥 Установка зависимостей...
pip install -r requirements.txt

REM Создание .env
if not exist ".env" (
    echo 📝 Создание .env...
    copy .env.example .env
)

REM Создание папок
echo 📁 Создание папок...
if not exist "%USERPROFILE%\.logs\ai_team" mkdir "%USERPROFILE%\.logs\ai_team"
if not exist "%USERPROFILE%\projects" mkdir "%USERPROFILE%\projects"

echo.
echo ✅ Установка завершена!
echo.
echo Запуск:
echo   CLI:  python core\main.py --project-name myapp --requirements "описание"
echo   Web:  python web_ui\app.py
echo.
echo Документация: docs\QUICKSTART.md

pause
