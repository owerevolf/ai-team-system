@echo off
rem Запуск AI Team System двойным кликом: поднимает сервер и открывает браузер.
rem Ничего вводить не нужно — просто закрой это окно, когда закончишь.
cd /d "%~dp0"
pwsh -NoProfile -ExecutionPolicy Bypass -File "scripts\launcher.ps1"
if errorlevel 1 (
    echo.
    echo Не удалось запустить. Скопируй текст выше и покажи помощнику.
    pause
)
